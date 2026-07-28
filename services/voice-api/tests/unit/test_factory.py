from app.clients.factory import get_llm, get_stt, get_tts
from app.clients.mocks import MockLLM, MockSTT, MockTTS


def test_default_providers_are_mock():
    get_stt.cache_clear()
    assert isinstance(get_stt(), MockSTT)
    assert isinstance(get_llm(), MockLLM)
    assert isinstance(get_tts(), MockTTS)
