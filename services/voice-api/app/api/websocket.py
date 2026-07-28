import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ValidationError

from app.audio.buffer import AudioBuffer
from app.audio.validation import validate_frame
from app.clients.factory import get_llm, get_stt, get_tts
from app.config import Settings, get_settings
from app.core.errors import DeviceError, ErrorCode
from app.core.security import parse_device_tokens, verify_device
from app.pipeline import VoicePipeline
from app.schemas.websocket import (
    AudioEndMessage,
    AudioStartMessage,
    AuthMessage,
    auth_ok,
    error_message,
)
from app.sessions.manager import SessionManager
from app.sessions.models import Session

logger = logging.getLogger(__name__)
router = APIRouter()

session_manager = SessionManager()


def build_pipeline() -> VoicePipeline:
    settings = get_settings()
    return VoicePipeline(get_stt(), get_llm(), get_tts(), frame_bytes=settings.frame_bytes)


@router.websocket("/ws/audio")
async def ws_audio(websocket: WebSocket) -> None:
    settings = get_settings()
    await websocket.accept()

    session = await _authenticate(websocket, settings)
    if session is None:
        return

    logger.info("device connected: %s session=%s", session.device_id, session.session_id)
    try:
        await _serve(websocket, session, settings)
    except WebSocketDisconnect:
        logger.info("device disconnected: %s", session.device_id)
    finally:
        session_manager.remove(session.device_id)


async def _authenticate(websocket: WebSocket, settings: Settings) -> Session | None:
    """첫 메시지 JSON 인증 (기획서 7.2). 실패 시 오류 전송 후 연결을 닫는다."""
    try:
        raw = await asyncio.wait_for(
            websocket.receive_text(), timeout=settings.auth_timeout_seconds
        )
        message = AuthMessage.model_validate_json(raw)
    except TimeoutError:
        await _reject(websocket, ErrorCode.AUTH_TIMEOUT, "Authentication timed out")
        return None
    except WebSocketDisconnect:
        return None
    except (ValidationError, KeyError):
        await _reject(websocket, ErrorCode.INVALID_MESSAGE, "First message must be auth JSON")
        return None

    registry = parse_device_tokens(settings.device_tokens)
    if not verify_device(message.device_id, message.token, registry):
        logger.warning("auth failed device_id=%s", message.device_id)
        await _reject(websocket, ErrorCode.AUTH_FAILED, "Invalid device credentials")
        return None

    session = session_manager.create(message.device_id)
    await websocket.send_json(auth_ok(message.device_id, session.session_id))
    return session


async def _reject(websocket: WebSocket, code: str, message: str) -> None:
    await websocket.send_json(error_message(code, message))
    await websocket.close(code=1008)


async def _serve(websocket: WebSocket, session: Session, settings: Settings) -> None:
    pipeline = build_pipeline()
    buffer: AudioBuffer | None = None
    request_id: str | None = None

    while True:
        try:
            message = await asyncio.wait_for(
                websocket.receive(), timeout=settings.websocket_idle_timeout_seconds
            )
        except TimeoutError:
            logger.info("idle timeout device=%s", session.device_id)
            await websocket.close(code=1001)
            return

        if message["type"] == "websocket.disconnect":
            raise WebSocketDisconnect(message.get("code") or 1000)

        try:
            if message.get("bytes") is not None:
                if buffer is None:
                    raise DeviceError(
                        ErrorCode.NO_ACTIVE_REQUEST, "Audio frame without audio_start"
                    )
                validate_frame(message["bytes"], settings.bytes_per_sample)
                buffer.append(message["bytes"])
            elif message.get("text") is not None:
                buffer, request_id = await _handle_control(
                    websocket, message["text"], buffer, request_id, pipeline, session, settings
                )
        except DeviceError as exc:
            logger.warning(
                "device error device=%s request=%s code=%s: %s",
                session.device_id, request_id, exc.code, exc.message,
            )
            await websocket.send_json(error_message(exc.code, exc.message, request_id))
            buffer, request_id = None, None
        except WebSocketDisconnect:
            raise
        except Exception:
            logger.exception("unexpected error device=%s request=%s", session.device_id, request_id)
            await websocket.send_json(
                error_message(ErrorCode.INTERNAL_ERROR, "Internal server error", request_id)
            )
            buffer, request_id = None, None


async def _handle_control(
    websocket: WebSocket,
    raw: str,
    buffer: AudioBuffer | None,
    request_id: str | None,
    pipeline: VoicePipeline,
    session: Session,
    settings: Settings,
) -> tuple[AudioBuffer | None, str | None]:
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        raise DeviceError(ErrorCode.INVALID_MESSAGE, "Control message is not valid JSON")
    msg_type = payload.get("type") if isinstance(payload, dict) else None

    if msg_type == "audio_start":
        start = _parse(AudioStartMessage, payload)
        if buffer is not None:
            raise DeviceError(ErrorCode.REQUEST_IN_PROGRESS, "Previous request still in progress")
        return AudioBuffer(settings.max_audio_bytes), start.request_id

    if msg_type == "audio_end":
        end = _parse(AudioEndMessage, payload)
        if buffer is None or end.request_id != request_id:
            raise DeviceError(ErrorCode.NO_ACTIVE_REQUEST, "audio_end without matching audio_start")
        pcm = buffer.getvalue()
        if not pcm:
            raise DeviceError(ErrorCode.INVALID_AUDIO, "No audio received")
        await pipeline.run(websocket, request_id, pcm, session)
        return None, None

    raise DeviceError(ErrorCode.INVALID_MESSAGE, f"Unsupported message type: {msg_type}")


def _parse[T: BaseModel](model: type[T], payload: dict) -> T:
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        raise DeviceError(ErrorCode.INVALID_MESSAGE, f"Invalid {payload.get('type')} message") from exc
