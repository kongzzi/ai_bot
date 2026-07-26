"""마이크 푸시 투 토크 클라이언트 — 컴퓨터 마이크로 voice-api를 테스트한다.

ESP32의 버튼 대신 Enter 키로 녹음을 시작/종료하고, 실제 목소리를
20ms PCM 프레임으로 실시간 전송한 뒤 서버의 TTS 응답을 스피커로 재생한다.

사용법:
  python scripts/mic_client.py                # 대화형: Enter로 녹음 시작/종료, q로 종료
  python scripts/mic_client.py --seconds 3    # 3초 자동 녹음 후 종료 (비대화형 테스트용)

주의: 처음 실행하면 macOS가 터미널 앱에 마이크 권한을 요청한다.
"""

import argparse
import asyncio
import json
import sys
import uuid

import sounddevice as sd
import websockets

SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_SAMPLES = 320  # 20ms → 640 bytes
MAX_RECORD_SECONDS = 25  # 서버 제한(30초) 전에 클라이언트에서 차단


def make_input_stream(
    loop: asyncio.AbstractEventLoop, queue: asyncio.Queue
) -> sd.RawInputStream:
    def callback(indata, frames, time_info, status):
        if status:
            print(f"[mic] {status}", file=sys.stderr)
        loop.call_soon_threadsafe(queue.put_nowait, bytes(indata))

    return sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        blocksize=FRAME_SAMPLES,
        callback=callback,
    )


async def send_frames(ws, queue: asyncio.Queue) -> int:
    """None 센티널을 받을 때까지 큐의 PCM 프레임을 서버로 보낸다."""
    sent = 0
    max_bytes = SAMPLE_RATE * 2 * MAX_RECORD_SECONDS
    capped = False
    while True:
        chunk = await queue.get()
        if chunk is None:
            return sent
        if sent + len(chunk) > max_bytes:
            if not capped:
                capped = True
                print(f"(최대 {MAX_RECORD_SECONDS}초 도달, 이후 오디오는 버립니다)")
            continue
        await ws.send(chunk)
        sent += len(chunk)


async def receive_response(ws) -> tuple[bytes, dict | None]:
    """state=ready 또는 error까지 수신. (TTS PCM, 오류) 반환."""
    tts = bytearray()
    while True:
        message = await asyncio.wait_for(ws.recv(), timeout=30)
        if isinstance(message, bytes):
            tts.extend(message)
            continue
        event = json.loads(message)
        match event.get("type"):
            case "transcript":
                print(f"  인식 결과: {event['text']}")
            case "tts_end":
                print(f"  TTS 수신 완료 ({len(tts)} bytes)")
            case "state" if event.get("state") == "ready":
                return bytes(tts), None
            case "error":
                return bytes(tts), event


def play_pcm(pcm: bytes) -> None:
    if not pcm:
        return
    with sd.RawOutputStream(
        samplerate=SAMPLE_RATE, channels=CHANNELS, dtype="int16"
    ) as out:
        out.write(pcm)


async def run_turn(ws, seconds: float | None) -> None:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    request_id = str(uuid.uuid4())

    await ws.send(json.dumps({
        "type": "audio_start",
        "request_id": request_id,
        "format": "pcm_s16le",
        "sample_rate": SAMPLE_RATE,
        "channels": CHANNELS,
    }))

    stream = make_input_stream(loop, queue)
    sender = asyncio.create_task(send_frames(ws, queue))
    stream.start()
    try:
        if seconds is not None:
            print(f"● 녹음 중... ({seconds:.0f}초, 말해보세요)")
            await asyncio.sleep(seconds)
        else:
            await asyncio.to_thread(input, "● 녹음 중... 말한 뒤 [Enter]로 종료: ")
    finally:
        stream.stop()
        stream.close()
    queue.put_nowait(None)
    sent = await sender
    await ws.send(json.dumps({"type": "audio_end", "request_id": request_id}))
    print(f"  전송: {sent} bytes ({sent / (SAMPLE_RATE * 2):.1f}초)")

    tts, error = await receive_response(ws)
    if error:
        print(f"  오류: {error.get('code')} — {error.get('message')}")
        return
    print("  응답 재생 중... (Phase 3은 목업이라 톤이 들립니다)")
    await asyncio.to_thread(play_pcm, tts)


async def main_async(args: argparse.Namespace) -> int:
    try:
        sd.query_devices(kind="input")
    except Exception as exc:
        print(f"사용 가능한 마이크가 없습니다: {exc}")
        return 1

    async with websockets.connect(args.url) as ws:
        await ws.send(json.dumps({
            "type": "auth",
            "device_id": args.device_id,
            "token": args.token,
            "protocol_version": "1.0",
        }))
        reply = json.loads(await ws.recv())
        if reply.get("type") != "auth_ok":
            print(f"인증 실패: {reply}")
            return 1
        print(f"연결됨: {args.url} (session={reply['session_id']})")

        try:
            if args.seconds is not None:
                await run_turn(ws, args.seconds)
                return 0
            while True:
                cmd = await asyncio.to_thread(
                    input, "\n[Enter] 녹음 시작 / q+[Enter] 종료: "
                )
                if cmd.strip().lower() == "q":
                    return 0
                await run_turn(ws, None)
        except websockets.ConnectionClosed:
            print("서버가 연결을 닫았습니다 (유휴 60초 초과 등). 다시 실행해 주세요.")
            return 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Microphone push-to-talk client for voice-api")
    parser.add_argument("--url", default="ws://localhost:8000/ws/audio")
    parser.add_argument("--device-id", default="device-001")
    parser.add_argument("--token", default="dev-token-001")
    parser.add_argument("--seconds", type=float, default=None,
                        help="지정 시 Enter 없이 해당 초만큼 자동 녹음")
    args = parser.parse_args()
    try:
        sys.exit(asyncio.run(main_async(args)))
    except KeyboardInterrupt:
        print("\n종료")


if __name__ == "__main__":
    main()
