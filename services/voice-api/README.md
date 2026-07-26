# voice-api

음성인식 캐릭터 AI Bot의 Voice Gateway (기획서 8장).
현재 **Phase 3**: STT/LLM/TTS는 Mock이며, Phase 4에서 Azure Speech / AI Foundry / OpenClaw로 교체한다.

## 실행

```bash
cd services/voice-api
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Health: http://localhost:8000/health
- WebSocket: `ws://localhost:8000/ws/audio`
- 개발용 장치 토큰: `device-001` / `dev-token-001` (`.env`의 `DEVICE_TOKENS`로 변경)

## 테스트

```bash
.venv/bin/pytest
```

## ESP32 시뮬레이터 (하드웨어 대체)

서버를 띄운 상태에서:

```bash
.venv/bin/python scripts/esp32_simulator.py
```

인증 → 2초 사인파 발화 전송 → transcript 수신 → TTS PCM 수신 → `tts_output.wav` 저장까지
실제 펌웨어와 동일한 프로토콜로 왕복 검증한다. `--realtime`을 주면 20ms 프레임 페이싱을 흉내낸다.

## 웹 테스트 콘솔 (가장 간편)

서버를 띄운 뒤 브라우저에서 **http://localhost:8000/test** 접속:

- 🎙 버튼(또는 스페이스바)을 **누르고 있는 동안 녹음** — ESP32 푸시 투 토크와 동일한 UX
- OLED 상태(`Ready`/`Listening`/`Recognizing`/`Thinking`/`Speaking`/`Error`)를 화면에 표시
- transcript, 전송량, 응답 지연 로그 표시, TTS는 스피커로 자동 재생
- `APP_ENV=development`일 때만 서빙됨 (운영 노출 금지)
- 브라우저 마이크 정책상 localhost 전용 — 다른 기기에서 접속하려면 https 필요

## 마이크 클라이언트 (실제 목소리로 테스트)

컴퓨터 마이크로 녹음해서 전송하고, 서버 TTS 응답을 스피커로 재생하는 푸시 투 토크 클라이언트:

```bash
.venv/bin/python scripts/mic_client.py               # 대화형: Enter로 녹음 시작/종료, q로 종료
.venv/bin/python scripts/mic_client.py --seconds 3   # 3초 자동 녹음 (스크립트 테스트용)
```

- ESP32의 버튼 역할을 Enter 키가 대신한다 (누름=시작, 다시 누름=발화 종료)
- 마이크 입력을 20ms/640B PCM 프레임으로 실시간 스트리밍 — 펌웨어와 동일한 경로
- 첫 실행 시 macOS가 터미널 앱에 마이크 권한을 요청한다
- 서버 유휴 타임아웃(60초)을 넘기면 연결이 닫히므로 다시 실행하면 된다

## 프로토콜 요약 (v1.0)

| 방향 | 메시지 | 비고 |
|---|---|---|
| C→S | `auth` | 연결 후 첫 메시지, 10초 내 |
| S→C | `auth_ok` | 기획서 미정의, 서버가 추가한 응답 |
| C→S | `audio_start` → PCM 바이너리(640B) → `audio_end` | |
| S→C | `state`(recognizing/thinking/ready), `transcript`, `tts_start` → PCM 바이너리 → `tts_end` | |
| S→C | `error` (`code`, `message`) | 상세 원인은 서버 로그에만 |
