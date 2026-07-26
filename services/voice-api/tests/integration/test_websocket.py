"""WebSocket 왕복 통합 테스트 — ESP32 없이 프로토콜 전체 흐름을 검증한다."""

import json

from fastapi.testclient import TestClient

from app.audio.format import chunk_pcm, sine_wave_pcm
from app.main import app

AUTH = {
    "type": "auth",
    "device_id": "device-001",
    "token": "dev-token-001",
    "protocol_version": "1.0",
}


def _recv(ws):
    """텍스트 메시지는 dict로, 바이너리는 bytes로 반환한다."""
    message = ws.receive()
    if message.get("text") is not None:
        return json.loads(message["text"])
    return message["bytes"]


def test_rejects_invalid_token():
    client = TestClient(app)
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_json({**AUTH, "token": "wrong-token"})
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "AUTH_FAILED"


def test_audio_frame_before_start_returns_error():
    client = TestClient(app)
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_json(AUTH)
        assert ws.receive_json()["type"] == "auth_ok"
        ws.send_bytes(b"\x00" * 640)
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert msg["code"] == "NO_ACTIVE_REQUEST"


def test_full_roundtrip():
    client = TestClient(app)
    with client.websocket_connect("/ws/audio") as ws:
        ws.send_json(AUTH)
        assert ws.receive_json()["type"] == "auth_ok"

        ws.send_json(
            {
                "type": "audio_start",
                "request_id": "req-1",
                "format": "pcm_s16le",
                "sample_rate": 16000,
                "channels": 1,
            }
        )
        for chunk in chunk_pcm(sine_wave_pcm(220, 1.0), 640):
            ws.send_bytes(chunk)
        ws.send_json({"type": "audio_end", "request_id": "req-1"})

        events = []
        tts_bytes = 0
        while True:
            received = _recv(ws)
            if isinstance(received, bytes):
                tts_bytes += len(received)
                continue
            events.append(received)
            if received.get("type") == "state" and received.get("state") == "ready":
                break

        types = [e["type"] for e in events]
        assert types == ["state", "transcript", "state", "tts_start", "tts_end", "state"]
        transcript = next(e for e in events if e["type"] == "transcript")
        assert "1.0초" in transcript["text"]
        assert tts_bytes > 0
        assert tts_bytes % 2 == 0
