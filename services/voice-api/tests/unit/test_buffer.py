import pytest

from app.audio.buffer import AudioBuffer
from app.core.errors import DeviceError, ErrorCode


def test_append_and_getvalue():
    buf = AudioBuffer(max_bytes=10)
    buf.append(b"abcd")
    buf.append(b"ef")
    assert buf.getvalue() == b"abcdef"
    assert len(buf) == 6


def test_overflow_raises_audio_too_long():
    buf = AudioBuffer(max_bytes=4)
    buf.append(b"abcd")
    with pytest.raises(DeviceError) as exc_info:
        buf.append(b"e")
    assert exc_info.value.code == ErrorCode.AUDIO_TOO_LONG
