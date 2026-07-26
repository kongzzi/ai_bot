import pytest

from app.audio.format import chunk_pcm, pcm_duration_seconds, sine_wave_pcm
from app.audio.validation import validate_frame
from app.core.errors import DeviceError


def test_sine_wave_length():
    pcm = sine_wave_pcm(440, 1.0, sample_rate=16000)
    assert len(pcm) == 16000 * 2


def test_pcm_duration():
    assert pcm_duration_seconds(32000) == 1.0


def test_chunk_pcm_sizes():
    chunks = list(chunk_pcm(b"x" * 1500, 640))
    assert [len(c) for c in chunks] == [640, 640, 220]


def test_validate_frame_rejects_odd_and_empty():
    with pytest.raises(DeviceError):
        validate_frame(b"")
    with pytest.raises(DeviceError):
        validate_frame(b"abc")
    validate_frame(b"abcd")  # 정상: 예외 없음
