# 음성인식 캐릭터 AI Bot — 작업 체크리스트

> 기준 문서: [PROJECT_PLAN.md](PROJECT_PLAN.md) v1.0 (2026-07-26)
> 현재 상황: 납땜 문제로 하드웨어 보류 → **Phase 0 → 3 → 4 → 5 → 6 순서로 서버부터 진행**, 하드웨어 수리 후 Phase 1 → 2 합류

---

## Phase 0. 프로젝트 기준선 (하드웨어 불필요)

- [ ] GitHub 저장소 생성 (모노레포)
- [ ] 디렉터리 구조 생성 — `firmware/`, `services/voice-api/`, `deploy/`, `infrastructure/`, `docs/`
- [x] `.env.example` 작성
- [x] `.gitignore` 작성 (`.env`, `.pio/`, 캐시 폴더 등)
- [ ] PR 템플릿, CODEOWNERS, main 브랜치 보호 규칙 설정
- [ ] 기획서를 `docs/PROJECT_PLAN.md`로 커밋

## Phase 1. 하드웨어 검증 ⏸ 보류 (납땜 재작업 후 진행)

- [ ] 버튼: D9 + `INPUT_PULLUP` 입력 확인 (누르면 LOW)
- [ ] OLED: I2C 주소 확인 후 텍스트 출력 확인
- [ ] INMP441 마이크: PCM 16kHz 수집 확인, L/R 채널 설정 확인
- [ ] MAX98357A 앰프: 사인파 재생 테스트
- [ ] 스피커: 음량·노이즈 확인, 마이크와 물리적 거리 확보
- [ ] I2S 입력/출력 핀 충돌 여부, GND 공통 연결, USB 전원 소비전류 확인
- [ ] 최종 핀맵 확정 → `firmware/include/board_pins.h`에 단일 정의

## Phase 2. 펌웨어 통합 ⏸ 보류 (Phase 1 이후)

- [ ] 상태 머신 구현: `BOOT → WIFI_CONNECTING → SERVER_CONNECTING → IDLE → RECORDING → THINKING → SPEAKING → IDLE` (+ ERROR 처리)
- [ ] 버튼 디바운싱 (20~50ms), 길게 누르는 동안 녹음, 최대 녹음 15~30초 제한
- [ ] Wi-Fi 연결 및 재연결 로직
- [ ] WebSocket 클라이언트: 연결, 인증 JSON 전송, 재연결
- [ ] 마이크 → PCM 프레임(20ms, 640 bytes) 전송
- [ ] 서버에서 받은 PCM 수신 → 스피커 재생
- [ ] OLED 상태 표시: `Ready` / `Listening` / `Thinking` / `Speaking` / `Error` 등
- [ ] Half Duplex 보장: 녹음 중 재생 금지, 재생 중 마이크 폐기
- [ ] FreeRTOS 태스크 분리: 버튼 / 마이크 / 송신 / 수신 / 재생 / 디스플레이 / 연결 관리

## Phase 3. 로컬 서버 ▶ 현재 진행 (하드웨어 없이 가능)

- [x] FastAPI 프로젝트 생성 (`services/voice-api/`, Python 3.12)
- [x] `GET /health` 엔드포인트
- [x] `WS /ws/audio` 엔드포인트 + 인증 처리 (device_id + token)
- [x] WebSocket 메시지 스키마 정의: `audio_start`, `audio_end`, `state`, `transcript`, `tts_start`, `tts_end`, `error` (+ 서버 추가 응답 `auth_ok`)
- [x] 오디오 버퍼 구현 (PCM 검증 포함)
- [x] Mock STT / Mock LLM / Mock TTS 어댑터 (실제 Azure 없이 왕복 확인용)
- [x] ESP32 시뮬레이터 스크립트로 왕복 테스트 (하드웨어 대체: 인증 → PCM 전송 → transcript → TTS 수신) — 2026-07-26 왕복 성공, 지연 6ms
- [ ] 구간별 타임아웃·재시도 정교화는 Phase 4에서 (현재는 인증 10초·유휴 60초·최대 녹음 30초만 적용)
- [ ] 실물 ESP32 ↔ 서버 왕복 테스트 (Phase 2 완료 후)

## Phase 4. Azure AI 연동 (Mock을 실제 서비스로 교체)

- [ ] Azure Speech STT 연동 (ko-KR, PCM 16kHz 입력)
- [ ] Azure AI Foundry LLM 호출 연동
- [ ] OpenClaw 연동: 캐릭터 프롬프트, 세션, 응답 가드레일
- [ ] Azure Speech TTS 연동 (ESP32가 바로 재생 가능한 PCM 16kHz mono 출력)
- [ ] 응답 정책 적용: 1~3문장, 마크다운·코드블록 금지, TTS 친화적 문장
- [ ] 오류 처리: 무음, 타임아웃, 인증 실패, 쿼터 초과 → 장치에는 간결한 오류 코드만
- [ ] 구간별 타임아웃 적용 (STT 15초, LLM 30초, TTS 20초, 전체 60초) + 재시도

## Phase 5. Docker

- [ ] Voice API Dockerfile (non-root, 헬스체크 포함)
- [ ] OpenClaw 컨테이너 구성
- [ ] Redis 컨테이너 (세션 저장, appendonly)
- [ ] `compose.yaml` + `compose.dev.yaml` / `compose.prod.yaml` 분리
- [ ] 환경변수 주입 구조 정리 (`.env`, 이미지에 시크릿 미포함)
- [ ] Caddy 개발 설정
- [ ] 로컬 Docker 환경에서 `docker compose up` 검증

## Phase 6. CI (GitHub Actions)

- [ ] Python: Ruff lint + format, MyPy, pytest + coverage
- [ ] WebSocket 계약 테스트 (펌웨어-서버 공유 항목: 메시지 type, 필드, 포맷, 버전)
- [ ] 펌웨어: PlatformIO 빌드, 크기 리포트, 산출물 업로드
- [ ] Docker 빌드 검증
- [ ] Secret scan + 취약점 스캔 (Trivy)
- [ ] main 병합 조건으로 Required checks 설정

## Phase 7. Azure Staging

- [ ] Bicep으로 인프라 코드화: VNet/NSG, VM, ACR, Key Vault, Log Analytics, Role Assignment
- [ ] Ubuntu VM 세팅 (`/opt/character-bot/` 구조, Docker Engine)
- [ ] Managed Identity: VM은 ACR Pull, 앱은 Key Vault Read
- [ ] GitHub Actions OIDC 인증 설정 (장기 시크릿 저장 금지)
- [ ] DNS + Caddy TLS (`wss://`) 설정
- [ ] main 병합 → 이미지 빌드 → SHA 태그 → ACR Push → Staging 자동 배포 파이프라인
- [ ] 배포 후 스모크 테스트: WebSocket 연결 → 인증 → 테스트 PCM → STT/LLM/TTS 확인

## Phase 8. Production

- [ ] GitHub Environment 승인 게이트 설정
- [ ] Production VM 구축 + 운영 Secret (Key Vault)
- [ ] 배포 스크립트: `deploy.sh` / `healthcheck.sh` / `rollback.sh`
- [ ] 헬스체크 실패 시 이전 SHA 이미지로 자동 롤백
- [ ] 모니터링·알림 (Azure Monitor), 로그 보존 정책
- [ ] 백업 및 장애 대응 절차서 작성

## Phase 9. 안정화

- [ ] 100회 연속 대화 반복 테스트
- [ ] 장시간 연결 유지 테스트, 메모리 누수 확인
- [ ] Wi-Fi 단절 → 복구 테스트
- [ ] Azure API 일시 장애 시나리오 테스트
- [ ] 음성 품질 튜닝, 전체 지연 최적화 (목표 3~5초)

---

## 완료 기준 메모

- **MVP**: Phase 4까지 + 20회 연속 대화 성공 + 미인증 장치 차단 + `docker compose` 한 명령 실행 + PR CI 통과 + Staging 자동 배포
- **Production Ready**: HTTPS/WSS, Key Vault, Managed Identity, SHA 태그 배포, 자동 헬스체크·롤백, 중앙 로그, 경고 알림, 부하 테스트 완료
