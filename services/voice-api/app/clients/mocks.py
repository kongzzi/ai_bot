from app.audio.format import pcm_duration_seconds, sine_wave_pcm


class MockSTT:
    async def transcribe(self, pcm: bytes) -> str:
        seconds = pcm_duration_seconds(len(pcm))
        return f"{seconds:.1f}초 분량의 목업 발화입니다"


class MockLLM:
    async def respond(self, transcript: str, history: list[dict]) -> str:
        turn = len(history) + 1
        return f"방금 '{transcript}'라고 들었어요. 저는 목업 캐릭터고, {turn}번째 대화예요."


class MockTTS:
    async def synthesize(self, text: str) -> bytes:
        # 텍스트 길이에 비례한 440Hz 톤. 실제 음성은 Phase 4의 Azure TTS에서.
        seconds = min(2.0, max(0.5, len(text) * 0.04))
        return sine_wave_pcm(440, seconds)
