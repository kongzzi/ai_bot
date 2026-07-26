import array
import math
import sys
from collections.abc import Iterator


def pcm_duration_seconds(
    num_bytes: int,
    sample_rate: int = 16000,
    bytes_per_sample: int = 2,
    channels: int = 1,
) -> float:
    return num_bytes / (sample_rate * bytes_per_sample * channels)


def sine_wave_pcm(
    freq_hz: float,
    seconds: float,
    sample_rate: int = 16000,
    amplitude: float = 0.3,
) -> bytes:
    """PCM s16le mono 사인파. Mock TTS와 하드웨어 재생 테스트에 사용한다."""
    num_samples = int(sample_rate * seconds)
    peak = amplitude * 32767
    samples = array.array(
        "h",
        (
            int(peak * math.sin(2 * math.pi * freq_hz * i / sample_rate))
            for i in range(num_samples)
        ),
    )
    if sys.byteorder == "big":
        samples.byteswap()
    return samples.tobytes()


def chunk_pcm(data: bytes, chunk_size: int = 640) -> Iterator[bytes]:
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]
