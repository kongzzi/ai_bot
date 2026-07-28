"""ESP32 시뮬레이터 — 하드웨어 없이 서버와 음성 왕복을 수행한다.

실제 펌웨어와 같은 프로토콜로 동작한다:
  인증 → audio_start → PCM 프레임(640B) 전송 → audio_end
  → transcript / TTS PCM 수신 → wav 파일 저장

사용법:
  python scripts/esp32_simulator.py
  python scripts/esp32_simulator.py --url ws://localhost:8000/ws/audio --seconds 2 --realtime
"""

import argparse
import array
import asyncio
import json
import math
import sys
import time
import uuid
import wave

import websockets

SAMPLE_RATE = 16000
FRAME_BYTES = 640  # 20ms


def sine_wave_pcm(freq_hz: float, seconds: float, amplitude: float = 0.3) -> bytes:
    num_samples = int(SAMPLE_RATE * seconds)
    peak = amplitude * 32767
    samples = array.array(
        "h",
        (
            int(peak * math.sin(2 * math.pi * freq_hz * i / SAMPLE_RATE))
            for i in range(num_samples)
        ),
    )
    if sys.byteorder == "big":
        samples.byteswap()
    return samples.tobytes()


def save_wav(path: str, pcm: bytes) -> None:
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(pcm)


def load_wav_pcm(path: str) -> bytes:
    """16kHz mono 16-bit wav에서 PCM을 읽는다 (실제 음성으로 STT 테스트용)."""
    with wave.open(path, "rb") as wav:
        if (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise SystemExit(
                f"{path}: 16kHz mono 16-bit wav가 아닙니다 "
                f"(rate={wav.getframerate()}, ch={wav.getnchannels()}, width={wav.getsampwidth()}). "
                f"변환: afconvert -f WAVE -d LEI16@16000 -c 1 in.wav out.wav"
            )
        return wav.readframes(wav.getnframes())


async def run(
    url: str, device_id: str, token: str, seconds: float, realtime: bool, out: str,
    wav: str | None = None,
) -> int:
    print(f"connecting: {url}")
    async with websockets.connect(url) as ws:
        # 1. 인증
        await ws.send(json.dumps({
            "type": "auth",
            "device_id": device_id,
            "token": token,
            "protocol_version": "1.0",
        }))
        reply = json.loads(await ws.recv())
        if reply.get("type") != "auth_ok":
            print(f"auth failed: {reply}")
            return 1
        print(f"auth ok, session={reply['session_id']}")

        # 2. 녹음 전송 (--wav가 있으면 실제 음성, 없으면 사인파)
        request_id = str(uuid.uuid4())
        pcm = load_wav_pcm(wav) if wav else sine_wave_pcm(220, seconds)
        seconds = len(pcm) / (SAMPLE_RATE * 2)
        await ws.send(json.dumps({
            "type": "audio_start",
            "request_id": request_id,
            "format": "pcm_s16le",
            "sample_rate": SAMPLE_RATE,
            "channels": 1,
        }))
        frames = 0
        for i in range(0, len(pcm), FRAME_BYTES):
            await ws.send(pcm[i : i + FRAME_BYTES])
            frames += 1
            if realtime:
                await asyncio.sleep(0.02)  # 실제 20ms 프레임 페이싱
        started = time.monotonic()
        await ws.send(json.dumps({"type": "audio_end", "request_id": request_id}))
        print(f"sent {frames} frames ({len(pcm)} bytes, {seconds:.1f}s)")

        # 3. 응답 수신
        tts_pcm = bytearray()
        while True:
            message = await asyncio.wait_for(ws.recv(), timeout=30)
            if isinstance(message, bytes):
                tts_pcm.extend(message)
                continue
            event = json.loads(message)
            match event.get("type"):
                case "state":
                    print(f"state: {event['state']}")
                    if event["state"] == "ready":
                        break
                case "transcript":
                    print(f"transcript: {event['text']}")
                case "tts_start":
                    print("tts: receiving audio...")
                case "tts_end":
                    print(f"tts: done ({len(tts_pcm)} bytes)")
                case "error":
                    print(f"error: {event.get('code')} {event.get('message')}")
                    return 1

        latency = time.monotonic() - started
        save_wav(out, bytes(tts_pcm))
        print(f"roundtrip ok: latency={latency * 1000:.0f}ms, tts saved to {out}")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="ESP32 simulator for voice-api")
    parser.add_argument("--url", default="ws://localhost:8000/ws/audio")
    parser.add_argument("--device-id", default="device-001")
    parser.add_argument("--token", default="dev-token-001")
    parser.add_argument("--seconds", type=float, default=2.0, help="사인파 발화 길이")
    parser.add_argument("--realtime", action="store_true", help="20ms 프레임 페이싱 사용")
    parser.add_argument("--out", default="tts_output.wav")
    parser.add_argument("--wav", default=None, help="사인파 대신 보낼 16kHz mono 16-bit wav 파일")
    args = parser.parse_args()
    sys.exit(asyncio.run(run(
        args.url, args.device_id, args.token, args.seconds, args.realtime, args.out, args.wav
    )))


if __name__ == "__main__":
    main()
