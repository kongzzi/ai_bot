"""STT → LLM → TTS 처리 파이프라인 (기획서 8.4).

클라이언트 구현이 Mock이든 실제 Azure든 동일한 흐름을 사용한다.
"""

import logging

from fastapi import WebSocket

from app.audio.format import chunk_pcm
from app.clients.base import CharacterLLM, SpeechToText, TextToSpeech
from app.core.errors import DeviceError, ErrorCode
from app.schemas.websocket import (
    state_message,
    transcript_message,
    tts_end_message,
    tts_start_message,
)
from app.sessions.models import Session

logger = logging.getLogger(__name__)


class VoicePipeline:
    def __init__(
        self,
        stt: SpeechToText,
        llm: CharacterLLM,
        tts: TextToSpeech,
        frame_bytes: int = 640,
    ):
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.frame_bytes = frame_bytes

    async def run(
        self, websocket: WebSocket, request_id: str, pcm: bytes, session: Session
    ) -> None:
        await websocket.send_json(state_message(request_id, "recognizing"))
        try:
            transcript = await self.stt.transcribe(pcm)
        except Exception as exc:
            logger.exception("STT failed request=%s", request_id)
            raise DeviceError(ErrorCode.STT_FAILED, "Speech recognition failed") from exc
        if not transcript.strip():
            raise DeviceError(ErrorCode.NO_SPEECH, "No speech recognized")
        await websocket.send_json(transcript_message(request_id, transcript))

        await websocket.send_json(state_message(request_id, "thinking"))
        try:
            reply = await self.llm.respond(transcript, session.history)
        except Exception as exc:
            logger.exception("LLM failed request=%s", request_id)
            raise DeviceError(ErrorCode.LLM_FAILED, "Response generation failed") from exc
        session.history.append({"user": transcript, "assistant": reply})

        try:
            audio = await self.tts.synthesize(reply)
        except Exception as exc:
            logger.exception("TTS failed request=%s", request_id)
            raise DeviceError(ErrorCode.TTS_FAILED, "Speech synthesis failed") from exc

        await websocket.send_json(tts_start_message(request_id))
        for chunk in chunk_pcm(audio, self.frame_bytes):
            await websocket.send_bytes(chunk)
        await websocket.send_json(tts_end_message(request_id))
        await websocket.send_json(state_message(request_id, "ready"))

        logger.info(
            "request completed device=%s request=%s pcm_in=%dB pcm_out=%dB",
            session.device_id,
            request_id,
            len(pcm),
            len(audio),
        )
