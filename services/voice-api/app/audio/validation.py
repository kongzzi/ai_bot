from app.core.errors import DeviceError, ErrorCode


def validate_frame(chunk: bytes, bytes_per_sample: int = 2) -> None:
    if not chunk:
        raise DeviceError(ErrorCode.INVALID_AUDIO, "Empty audio frame")
    if len(chunk) % bytes_per_sample != 0:
        raise DeviceError(ErrorCode.INVALID_AUDIO, "Audio frame is not 16-bit aligned")
