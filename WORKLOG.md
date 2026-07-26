# 작업 일지 — 음성인식 캐릭터 AI Bot

> 기준 문서: [PROJECT_PLAN.md](PROJECT_PLAN.md) v1.0 · 체크리스트: [TODO.md](TODO.md)

---

## 2026-07-26 — 기획 분석 및 Phase 3 로컬 서버 구축

### 상황

- 프로젝트 기획서(v1.0)를 검토하고 작업을 기능별/단계별로 정리
- **납땜 불량으로 하드웨어(Phase 1~2) 보류** → 진행 순서를 Phase 0 → 3 → 4 → 5 → 6으로 조정, 하드웨어 수리 후 Phase 1 → 2 합류

### 완료한 작업

#### 1. 문서

| 파일 | 내용 |
|---|---|
| [TODO.md](TODO.md) | Phase 0~9 전체 작업 체크리스트 (하드웨어 단계 보류 표시, 완료 항목 체크) |
| [.gitignore](.gitignore) | Python/PlatformIO/시크릿 제외 규칙 (Phase 0) |
| [.env.example](.env.example) | 환경변수 예시 — Phase 4용 Azure 항목은 주석 처리 (Phase 0) |
| [services/voice-api/README.md](services/voice-api/README.md) | 실행법, 테스트 도구 사용법, 프로토콜 요약 |

#### 2. Voice API 서버 (Phase 3) — `services/voice-api/`

기획서 8.3 디렉터리 구조 그대로 구현. Python 3.12 + FastAPI.

- **`GET /health`** — 상태/버전/mock 여부 응답
- **`WS /ws/audio`** — 기획서 7장 프로토콜 v1.0 구현
  - 첫 메시지 JSON 인증 (10초 제한, device_id + token, `hmac.compare_digest` 비교)
  - 제어 메시지: `audio_start` → PCM 바이너리 → `audio_end` / 응답: `state`, `transcript`, `tts_start`, PCM, `tts_end`, `error`
  - **`auth_ok`는 기획서에 없어서 추가한 서버 응답** → 펌웨어 개발 시 이 메시지 대기 필요, 계약 테스트에 포함할 것
  - 유휴 60초 타임아웃, 최대 녹음 30초 버퍼 제한, 오류는 장치 친화적 코드로 변환 (`AUTH_FAILED`, `AUDIO_TOO_LONG`, `NO_ACTIVE_REQUEST` 등)
- **파이프라인** ([app/pipeline.py](services/voice-api/app/pipeline.py)) — STT → LLM → TTS, 단계별 오류 코드 매핑
- **Mock 어댑터** ([app/clients/mocks.py](services/voice-api/app/clients/mocks.py)) — STT(발화 길이 리포트), LLM(대화 횟수 기억), TTS(440Hz 톤). [base.py](services/voice-api/app/clients/base.py)의 Protocol 인터페이스라 Phase 4에서 Azure 구현으로 교체만 하면 됨
- **세션** — 메모리 방식 (운영 시 Redis 교체 예정, 기획서 8.6)
- **로깅** — device_id/request_id 포함, 발화 내용은 기록 안 함 (기획서 19.3 개인정보 원칙)

#### 3. 테스트 도구 3종 (하드웨어 대체)

| 도구 | 용도 | 사용법 |
|---|---|---|
| [esp32_simulator.py](services/voice-api/scripts/esp32_simulator.py) | 자동 왕복 검증 (CI용). 사인파 발화 전송, `--realtime`으로 20ms 페이싱 | `.venv/bin/python scripts/esp32_simulator.py` |
| [mic_client.py](services/voice-api/scripts/mic_client.py) | 터미널에서 실제 마이크로 푸시 투 토크 (`sounddevice` 사용) | `.venv/bin/python scripts/mic_client.py` |
| **웹 테스트 콘솔** ([test.html](services/voice-api/app/static/test.html)) | 브라우저에서 버튼 홀드 녹음 + OLED 상태 표시 + TTS 재생. **개발 모드에서만 서빙** | 서버 실행 후 http://localhost:8000/test |

웹 콘솔 기능: 홀드(마우스/터치/스페이스바) 녹음 → 실시간 PCM 스트리밍, OLED 모사 상태 표시(`Ready`/`Listening`/`Recognizing`/`Thinking`/`Speaking`/`Error`), transcript·지연 로그, **보낸 음성 확인(재생/WAV 다운로드)** — 서버가 받은 것과 동일한 16kHz PCM 사본.

#### 4. 검증 결과

- **pytest 12개 전부 통과** (단위: 보안/버퍼/포맷, 통합: health/인증 거부/전체 왕복)
- 시뮬레이터 왕복 성공 — 2초 발화 100프레임 전송, transcript 수신, TTS 64KB 수신, 지연 6~16ms
- 마이크 클라이언트 왕복 성공 — 실제 마이크 2초 녹음 전송 확인
- 웹 콘솔 실사용 확인 — 1.3~4.1초 실발화 3회 왕복 성공, 유휴 타임아웃 후 재접속 동작 확인

### 실행 방법 (요약)

```bash
cd services/voice-api
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000   # 서버
# 브라우저: http://localhost:8000/test  (개발 토큰: device-001 / dev-token-001)
.venv/bin/pytest                                             # 테스트
```

### 결정 사항 기록

1. **`auth_ok` 메시지 추가** — 기획서 7.2에 인증 성공 응답이 미정의라 신설. 프로토콜 문서화 및 펌웨어 계약 테스트 반영 필요
2. **웹 테스트 콘솔은 `APP_ENV=development`에서만 서빙** — 운영 이미지 노출 금지
3. **클라이언트 녹음 확인 기능** — 전송 전 원본이 아닌 "전송된 것과 동일한" 16kHz PCM 사본을 재생/저장 (STT 디버깅 자료로 활용)
4. 구간별 타임아웃(STT 15s/LLM 30s/TTS 20s)과 재시도는 Phase 4에서 실연동과 함께 적용

### 추가 기록 (같은 날 오후)

- **서버 실행 방식 변경**: 백그라운드 실행을 정리하고, 이후로는 개발자가 직접 터미널에서 `uvicorn` 실행 (로그 실시간 확인 목적). 코드 수정 시 `--reload` 옵션 권장
- **사용자 직접 검증 완료**: 직접 띄운 서버 + 웹 콘솔로 1.3초 실발화 왕복 성공. 클라이언트 로그(전송 40,960B, 지연 28ms)와 서버 로그(`pcm_in=40960B pcm_out=64000B`)가 세션 ID·request_id 단위로 일치함을 확인
- **관찰 방법 정리**: WebSocket은 Swagger(`/docs`)에 표시되지 않음 — 음성 요청 관찰은 ① 브라우저 개발자 도구 Network → WS → Messages(프레임 단위 상세), ② 서버 터미널 로그(처리 결과), ③ `/test` 로그 패널(요약) 사용
- **Phase 4 반영 예정**: `request completed` 로그에 구간별 지연(`stt_ms`/`llm_ms`/`tts_ms`) 추가 (기획서 19.2 — 현재는 Mock이라 생략)

### 다음 작업

- [ ] **Phase 4**: Azure Speech STT/TTS + AI Foundry LLM + OpenClaw 실연동 (Azure 리소스 키 필요 — Speech는 `koreacentral` 권장)
- [ ] **Phase 0 마무리**: `git init` + 첫 커밋, GitHub 저장소 생성
- [ ] 납땜 재작업 후 Phase 1 (하드웨어 검증) 시작
- [ ] 참고: VSCode 인터프리터를 `services/voice-api/.venv/bin/python`으로 선택하면 IDE 경고 사라짐
