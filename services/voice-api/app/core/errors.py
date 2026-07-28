class ErrorCode:
    AUTH_FAILED = "AUTH_FAILED"
    AUTH_TIMEOUT = "AUTH_TIMEOUT"
    INVALID_MESSAGE = "INVALID_MESSAGE"
    INVALID_AUDIO = "INVALID_AUDIO"
    AUDIO_TOO_LONG = "AUDIO_TOO_LONG"
    NO_ACTIVE_REQUEST = "NO_ACTIVE_REQUEST"
    REQUEST_IN_PROGRESS = "REQUEST_IN_PROGRESS"
    STT_FAILED = "STT_FAILED"
    NO_SPEECH = "NO_SPEECH"
    LLM_FAILED = "LLM_FAILED"
    TTS_FAILED = "TTS_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class DeviceError(Exception):
    """장치로 전달해도 되는 오류. 상세 원인은 서버 로그에만 남긴다 (기획서 9.4)."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message
