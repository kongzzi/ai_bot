"""WebSocket 제어 메시지 스키마 (기획서 7장, protocol_version 1.0).

`auth_ok`는 기획서에 명시되지 않은 서버 응답으로, 인증 성공을 장치에
알리기 위해 추가했다. 펌웨어 계약 테스트에 포함시킬 것.
"""

from typing import Literal

from pydantic import BaseModel

PROTOCOL_VERSION = "1.0"


class AuthMessage(BaseModel):
    type: Literal["auth"]
    device_id: str
    token: str
    protocol_version: str = PROTOCOL_VERSION


class AudioStartMessage(BaseModel):
    type: Literal["audio_start"]
    request_id: str
    format: Literal["pcm_s16le"] = "pcm_s16le"
    sample_rate: Literal[16000] = 16000
    channels: Literal[1] = 1


class AudioEndMessage(BaseModel):
    type: Literal["audio_end"]
    request_id: str


def auth_ok(device_id: str, session_id: str) -> dict:
    return {
        "type": "auth_ok",
        "device_id": device_id,
        "session_id": session_id,
        "protocol_version": PROTOCOL_VERSION,
    }


def state_message(request_id: str, state: str) -> dict:
    return {"type": "state", "request_id": request_id, "state": state}


def transcript_message(request_id: str, text: str) -> dict:
    return {"type": "transcript", "request_id": request_id, "text": text}


def tts_start_message(request_id: str) -> dict:
    return {
        "type": "tts_start",
        "request_id": request_id,
        "format": "pcm_s16le",
        "sample_rate": 16000,
        "channels": 1,
    }


def tts_end_message(request_id: str) -> dict:
    return {"type": "tts_end", "request_id": request_id}


def error_message(code: str, message: str, request_id: str | None = None) -> dict:
    payload = {"type": "error", "code": code, "message": message}
    if request_id is not None:
        payload["request_id"] = request_id
    return payload
