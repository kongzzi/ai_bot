# 음성인식 캐릭터 AI Bot

버튼을 누르고 말하면, ESP32-S3가 음성을 서버로 보내고 캐릭터가 음성으로 대답하는 장치를 만드는 프로젝트.

```
[사용자] ─ 버튼 누르고 말하기
   ↓
[XIAO ESP32S3] ─ INMP441 마이크 → PCM 16kHz → Wi-Fi WebSocket
   ↓
[Voice API 서버] ─ STT → 캐릭터 LLM → TTS
   ↓
[XIAO ESP32S3] ─ MAX98357A 앰프 → 스피커 재생, OLED 상태 표시
```

| 구성 | 기술 |
|---|---|
| 하드웨어 | Seeed Studio XIAO ESP32S3 + INMP441 + MAX98357A + 0.96" OLED |
| 서버 | Python 3.12 · FastAPI · WebSocket |
| AI | Azure Speech (STT/TTS) · Azure AI Foundry (LLM) · OpenClaw (에이전트) — 현재 STT는 로컬 faster-whisper로 선행 구현 |
| 오디오 | PCM 16kHz mono signed 16-bit LE, 20ms 프레임 |
| 인프라 | Docker Compose · Azure Ubuntu VM · GitHub Actions CI/CD |

## 현재 상태

**Phase 3 완료 + 로컬 STT 실인식 동작** — 하드웨어 없이 실제 한국어 음성 인식까지 되는 로컬 서버.

- ✅ WebSocket 게이트웨이 (인증, 오디오 스트리밍, 프로토콜 v1.0)
- ✅ **faster-whisper 로컬 STT** — 마이크로 말하면 실제 문장 인식 (`STT_PROVIDER=whisper`, 왕복 약 1초)
- ✅ 테스트 도구 3종 (웹 콘솔 / 터미널 마이크 클라이언트 / 자동 시뮬레이터)
- ⏸ 하드웨어 검증(Phase 1~2)은 배선 재작업 후 진행
- ⬜ 다음: Phase 4 — LLM/TTS 실연동 (Azure Foundry/Speech + OpenClaw, LLM/TTS는 아직 Mock)

전체 로드맵은 [TODO.md](TODO.md), 진행 기록은 [WORKLOG.md](WORKLOG.md) 참고.

## 빠른 시작

```bash
git clone https://github.com/kongzzi/ai_bot.git
cd ai_bot/services/voice-api

python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

브라우저에서 **http://localhost:8000/test** 접속 → 🎙 버튼을 누르고 있는 동안 말하기 → 손 떼면 인식 결과와 TTS 응답이 재생됩니다. (개발용 장치 인증: `device-001` / `dev-token-001`)

테스트 실행:

```bash
.venv/bin/pytest
```

자세한 사용법(터미널 마이크 클라이언트, ESP32 시뮬레이터, 프로토콜 명세)은 [services/voice-api/README.md](services/voice-api/README.md) 참고.

## 저장소 구조

```
ai_bot/
├─ PROJECT_PLAN.md        # 개발 기준 문서 (아키텍처, 프로토콜, 운영 설계)
├─ TODO.md                # Phase 0~9 작업 체크리스트
├─ WORKLOG.md             # 날짜별 작업 일지
├─ .env.example           # 환경변수 템플릿 (시크릿은 커밋 금지)
├─ services/
│  └─ voice-api/          # Voice Gateway 서버 (FastAPI)
│     ├─ app/             #   api / audio / clients / core / schemas / sessions
│     ├─ scripts/         #   esp32_simulator.py · mic_client.py
│     ├─ tests/           #   unit / integration
│     └─ app/static/      #   웹 테스트 콘솔 (/test, 개발 모드 전용)
├─ firmware/              # (예정) XIAO ESP32S3 펌웨어 — Phase 2
├─ deploy/                # (예정) Docker Compose, Caddy, 배포 스크립트 — Phase 5
└─ infrastructure/        # (예정) Azure Bicep — Phase 7
```

## 개발 단계 (요약)

| Phase | 내용 | 상태 |
|---|---|---|
| 0 | 저장소·문서·기준선 | ✅ (브랜치 보호는 Phase 6에서) |
| 1 | 하드웨어 부품 검증, 핀맵 확정 | ⏸ 배선 재작업 대기 |
| 2 | 펌웨어 (상태 머신, 녹음/재생, WebSocket) | ⏸ |
| 3 | 로컬 서버 + Mock AI + 왕복 테스트 | ✅ |
| 4 | Azure Speech / AI Foundry / OpenClaw 실연동 | ⬜ 다음 |
| 5 | Docker Compose 컨테이너화 | ⬜ |
| 6 | GitHub Actions CI | ⬜ |
| 7 | Azure Staging (Bicep, ACR, VM) | ⬜ |
| 8 | Production 배포·모니터링·롤백 | ⬜ |
| 9 | 안정화 (반복·장애·지연 테스트) | ⬜ |

## 설계 원칙

- **장치는 단순하게** — ESP32는 음성 입출력과 OLED만. AI 자격 증명과 로직은 전부 서버에 (시크릿을 펌웨어에 저장하지 않음)
- **하나의 이미지, 모든 환경** — 로컬과 운영이 동일한 Docker 이미지 사용, 설정은 환경변수로 주입
- **교체 가능한 어댑터** — STT/LLM/TTS는 Protocol 인터페이스 뒤에 있어 Mock ↔ Azure 교체가 코드 한 곳 수정
- **개인정보 최소화** — 원본 음성 미저장, 로그에는 메타데이터만 (기획서 19.3)
