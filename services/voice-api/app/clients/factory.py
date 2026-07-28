"""설정(STT_PROVIDER 등)에 따라 클라이언트 구현을 선택한다.

lru_cache로 프로세스당 한 번만 생성한다 (Whisper 모델 로딩 비용 때문).
"""

from functools import lru_cache

from app.clients.base import CharacterLLM, SpeechToText, TextToSpeech
from app.clients.mocks import MockLLM, MockSTT, MockTTS
from app.config import get_settings


@lru_cache
def get_stt() -> SpeechToText:
    settings = get_settings()
    if settings.stt_provider == "whisper":
        from app.clients.whisper_stt import WhisperSTT

        return WhisperSTT(
            model_size=settings.whisper_model,
            language=settings.whisper_language,
            compute_type=settings.whisper_compute_type,
        )
    return MockSTT()


@lru_cache
def get_llm() -> CharacterLLM:
    return MockLLM()  # Phase 4: Azure AI Foundry + OpenClaw


@lru_cache
def get_tts() -> TextToSpeech:
    return MockTTS()  # Phase 4: Azure Speech TTS
