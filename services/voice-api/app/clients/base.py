"""STT/LLM/TTS 어댑터 인터페이스.

Phase 3은 mocks.py 구현을 사용하고, Phase 4에서 azure_speech.py,
foundry.py, openclaw.py 실구현으로 교체한다 (기획서 8.3, 10장).
"""

from typing import Protocol


class SpeechToText(Protocol):
    async def transcribe(self, pcm: bytes) -> str: ...


class CharacterLLM(Protocol):
    async def respond(self, transcript: str, history: list[dict]) -> str: ...


class TextToSpeech(Protocol):
    async def synthesize(self, text: str) -> bytes: ...
