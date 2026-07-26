from app.core.errors import DeviceError, ErrorCode


class AudioBuffer:
    def __init__(self, max_bytes: int):
        self.max_bytes = max_bytes
        self._data = bytearray()

    def append(self, chunk: bytes) -> None:
        if len(self._data) + len(chunk) > self.max_bytes:
            raise DeviceError(ErrorCode.AUDIO_TOO_LONG, "Maximum recording length exceeded")
        self._data.extend(chunk)

    def getvalue(self) -> bytes:
        return bytes(self._data)

    def __len__(self) -> int:
        return len(self._data)
