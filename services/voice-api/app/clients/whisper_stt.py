"""faster-whisper 기반 로컬 STT 어댑터.

Azure 키 없이 실제 음성 인식을 쓰기 위한 구현. `pip install -e ".[whisper]"`
필요. 모델은 첫 로딩 시 HuggingFace에서 내려받아 캐시된다.
"""

import asyncio
import logging
import time

logger = logging.getLogger(__name__)


class WhisperSTT:
    def __init__(
        self,
        model_size: str = "small",
        language: str = "ko",
        compute_type: str = "int8",
    ):
        from faster_whisper import WhisperModel  # 선택 의존성이라 지연 import

        started = time.monotonic()
        logger.info("loading whisper model=%s compute=%s ...", model_size, compute_type)
        self._model = WhisperModel(model_size, device="cpu", compute_type=compute_type)
        logger.info("whisper model loaded in %.1fs", time.monotonic() - started)
        self._language = language

    async def transcribe(self, pcm: bytes) -> str:
        # 디코딩이 CPU 블로킹이라 이벤트 루프를 막지 않도록 스레드에서 실행
        return await asyncio.to_thread(self._transcribe_sync, pcm)

    def _transcribe_sync(self, pcm: bytes) -> str:
        import numpy as np

        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
        started = time.monotonic()
        segments, info = self._model.transcribe(
            audio,
            language=self._language,
            beam_size=5,
            vad_filter=True,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
        logger.info(
            "whisper transcribed %.1fs audio in %.2fs: %d chars",
            len(audio) / 16000,
            time.monotonic() - started,
            len(text),
        )
        return text
