# 음성인식 캐릭터 AI Bot 최종 개발 기획서

> 문서 버전: v1.0  
> 작성일: 2026-07-26  
> 프로젝트명: 음성인식 캐릭터 AI Bot  
> 문서 상태: 개발 기준선(Baseline)  
> 대상 환경: Windows 11 로컬 개발 → Azure VM 운영  
> 주요 기술: XIAO ESP32S3, FastAPI, WebSocket, OpenClaw, Azure Speech, Azure AI Foundry, Docker, GitHub Actions

---

## 1. 문서 목적

본 문서는 XIAO ESP32S3 기반 음성인식 캐릭터 AI Bot의 하드웨어, 펌웨어, 서버, AI 연동, Docker 개발환경, Azure 운영환경 및 GitHub 기반 CI/CD 운영 방안을 하나의 개발 기준 문서로 통합한다.

이 문서는 다음 용도로 사용한다.

- 전체 시스템 아키텍처 합의
- 개발 범위와 우선순위 관리
- 하드웨어와 서버 간 인터페이스 정의
- 로컬 및 운영 환경의 재현성 확보
- GitHub 기반 코드 리뷰, 테스트, 배포 기준 수립
- Azure VM 운영 및 장애 대응 기준 수립
- 향후 기능 확장 시 설계 기준 제공

---

## 2. 프로젝트 개요

### 2.1 프로젝트 목표

사용자가 물리 버튼을 누르고 말하면 ESP32-S3가 음성을 수집하여 서버로 전송하고, 서버가 음성을 텍스트로 변환한 뒤 OpenClaw 및 Azure AI Foundry 모델을 이용하여 캐릭터 응답을 생성한다. 생성된 응답은 Azure Speech TTS를 통해 음성으로 합성되어 ESP32-S3 스피커로 재생된다.

### 2.2 핵심 사용자 흐름

1. 사용자가 푸시 버튼을 누른다.
2. OLED에 `Listening` 상태가 표시된다.
3. INMP441 마이크에서 PCM 음성을 수집한다.
4. ESP32-S3가 Wi-Fi WebSocket으로 음성 데이터를 서버에 전송한다.
5. 서버가 Azure Speech STT로 음성을 텍스트로 변환한다.
6. OpenClaw가 세션, 캐릭터 설정, 도구 호출 정책을 처리한다.
7. Azure AI Foundry 모델이 캐릭터 응답을 생성한다.
8. Azure Speech TTS가 응답 텍스트를 음성으로 합성한다.
9. 서버가 합성 음성을 WebSocket으로 ESP32-S3에 전송한다.
10. MAX98357A와 스피커를 통해 음성을 재생한다.
11. OLED가 다시 `Ready` 상태로 전환된다.

### 2.3 성공 기준

| 구분 | 목표 |
|---|---|
| 버튼 반응 | 100ms 이내 |
| 음성 전송 | 실시간 또는 준실시간 스트리밍 |
| STT 처리 | 발화 종료 후 약 1초 내외 |
| LLM 응답 | 일반 응답 기준 1~3초 |
| TTS 첫 오디오 | 응답 생성 후 약 1초 내외 |
| 전체 체감 지연 | 초기 목표 3~5초 |
| 운영 가용성 | 단일 VM 기준 자동 재시작 및 헬스체크 |
| 배포 재현성 | 동일 Docker 이미지로 로컬/운영 배포 |
| 보안 | Azure 비밀정보는 ESP32에 저장하지 않음 |

---

## 3. 개발 범위

### 3.1 1차 개발 범위

- 푸시 투 토크 기반 음성 입력
- 단일 ESP32 장치 연결
- PCM 16kHz, 16-bit, mono 음성 전송
- FastAPI WebSocket 게이트웨이
- Azure Speech STT
- OpenClaw 연동
- Azure AI Foundry LLM 연동
- Azure Speech TTS
- ESP32 음성 재생
- OLED 상태 표시
- Docker 기반 로컬 실행
- GitHub Actions 기반 CI
- ACR 기반 이미지 배포
- Azure VM 기반 운영
- 기본 로그, 헬스체크, 롤백

### 3.2 1차 범위 제외

- 다중 사용자 대규모 동시 접속
- 상용 수준의 완전한 무중단 배포
- 복수 지역 Azure 이중화
- 음성 생체 인증
- 완전한 오프라인 AI
- 모바일 앱
- OTA 자동 강제 배포
- 음성 중첩 재생 및 완전한 Full Duplex
- Kubernetes 운영

### 3.3 향후 확장 후보

- 여러 캐릭터 선택
- 장기 기억
- 음성 감정 분석
- Wake Word
- OTA 펌웨어 업데이트
- 디바이스 프로비저닝
- 관리자 웹 대시보드
- 텔레메트리와 사용량 분석
- Azure Container Apps 또는 AKS 이전
- 다국어 STT/TTS
- 스트리밍 LLM 및 스트리밍 TTS

---

## 4. 시스템 아키텍처

### 4.1 논리 아키텍처

```text
┌───────────────────────────────────────────────┐
│ XIAO ESP32S3                                  │
│                                               │
│ Push Button ─┐                                │
│ INMP441 ─────┼─> Firmware State Machine       │
│ OLED ────────┤                                │
│ MAX98357A <──┘                                │
└────────────────┬──────────────────────────────┘
                 │ Wi-Fi / WebSocket
                 │ PCM + JSON Control
                 ▼
┌───────────────────────────────────────────────┐
│ Voice Gateway                                │
│ FastAPI + Uvicorn                            │
│                                               │
│ - WebSocket Session                          │
│ - Audio Buffer                               │
│ - Authentication                             │
│ - STT Adapter                                │
│ - OpenClaw Adapter                           │
│ - Foundry LLM Adapter                        │
│ - TTS Adapter                                │
│ - Logging / Metrics                          │
└───────┬──────────────┬──────────────┬─────────┘
        │              │              │
        ▼              ▼              ▼
 Azure Speech       OpenClaw      Azure AI Foundry
 STT / TTS          Session       Character LLM
        │
        ▼
   Audio Response
```

### 4.2 배포 아키텍처

```text
개발자 PC
Windows 11
├─ Arduino IDE / PlatformIO
├─ WSL2
└─ Docker Desktop
   └─ Linux Containers
      ├─ voice-api
      ├─ openclaw
      ├─ redis
      └─ caddy

GitHub
├─ Repository
├─ Pull Request
├─ GitHub Actions
└─ GitHub Environments

Azure
├─ Microsoft Entra ID / OIDC
├─ Azure Container Registry
├─ Azure Key Vault
├─ Azure Monitor / Log Analytics
└─ Ubuntu VM
   └─ Docker Engine + Compose
      ├─ caddy
      ├─ voice-api
      ├─ openclaw
      └─ redis
```

### 4.3 운영체제 기준

- 로컬 개발: Windows 11
- 로컬 컨테이너: Docker Desktop의 Linux container mode
- 권장 운영: Azure Ubuntu VM + Docker Engine
- 대안 운영: Azure Windows Server/Windows 11 + Docker 환경
- 핵심 재현성 기준: 호스트 OS가 아니라 Docker 이미지, Compose 정의, 환경변수 계약을 동일하게 유지

---

## 5. 하드웨어 구성

### 5.1 사용 부품

- Seeed Studio XIAO ESP32S3
- OLED Display 0.96"
- MAX98357A I2S Amplifier
- INMP441 Microphone Module
- Speaker
- Push Switch
- Wires
- Windows 11 노트북
- USB-C 케이블

### 5.2 현재 확인된 연결 상태

- 푸시 스위치: XIAO ESP32S3의 D9와 GND에 연결
- XIAO ESP32S3: Windows 11 노트북 USB-C 포트와 연결
- Arduino 개발환경: 설치 및 기본 설정 완료

### 5.3 핀맵 관리 원칙

현재 문서에서 확정된 핀은 D9 버튼 입력뿐이다. OLED, INMP441, MAX98357A의 실제 핀 번호는 최종 회로 검증 후 `firmware/include/board_pins.h`에 단일 정의한다.

예시:

```cpp
#pragma once

#define PIN_BUTTON      D9

#define PIN_I2C_SDA     D4
#define PIN_I2C_SCL     D5

#define PIN_MIC_BCLK    D1
#define PIN_MIC_WS      D2
#define PIN_MIC_SD      D3

#define PIN_SPK_BCLK    D6
#define PIN_SPK_LRC     D7
#define PIN_SPK_DIN     D8
```

> 위 핀 번호는 구조 예시이며 실제 배선 검증 후 확정해야 한다.

### 5.4 전기적 검토 항목

- XIAO ESP32S3 GPIO 전압은 3.3V 기준으로 사용
- INMP441 전원 및 L/R 채널 설정 확인
- MAX98357A 입력 전압 및 스피커 임피던스 확인
- OLED I2C 주소 확인
- I2S 입력/출력 핀 충돌 여부 확인
- USB 전원 공급 시 최대 소비전류 검토
- 스피커 출력 시 전원 노이즈가 마이크 입력에 유입되는지 확인
- 마이크와 스피커의 물리적 거리 확보
- GND 공통 연결 확인
- 버튼 입력은 `INPUT_PULLUP` 사용

---

## 6. ESP32 펌웨어 설계

### 6.1 상태 머신

```text
BOOT
  ↓
WIFI_CONNECTING
  ↓
SERVER_CONNECTING
  ↓
IDLE
  ↓ 버튼 누름
RECORDING
  ↓ 버튼 해제
UPLOADING / PROCESSING
  ↓ STT 완료
THINKING
  ↓ TTS 시작
SPEAKING
  ↓ 재생 완료
IDLE
```

오류 발생 시:

```text
ANY STATE
  ↓
ERROR
  ↓ 재시도 또는 사용자 입력
IDLE / WIFI_CONNECTING
```

### 6.2 OLED 표시

| 상태 | 표시 문자열 |
|---|---|
| 부팅 | `Booting` |
| Wi-Fi 연결 | `WiFi...` |
| 서버 연결 | `Server...` |
| 대기 | `Ready` |
| 녹음 | `Listening` |
| 음성 인식 | `Recognizing` |
| AI 처리 | `Thinking` |
| 음성 재생 | `Speaking` |
| 오류 | `Error` |

### 6.3 FreeRTOS 태스크 권장 구성

- `buttonTask`
- `microphoneCaptureTask`
- `websocketSendTask`
- `websocketReceiveTask`
- `speakerPlaybackTask`
- `displayTask`
- `connectionManagerTask`

### 6.4 오디오 규격

| 항목 | 값 |
|---|---|
| 포맷 | PCM |
| Sample Rate | 16000 Hz |
| Channel | Mono |
| Bit Depth | 16-bit signed |
| Endian | Little Endian |
| 프레임 길이 | 20ms 권장 |
| 프레임 크기 | 640 bytes |

계산:

```text
16000 samples/sec × 2 bytes/sample × 0.02 sec = 640 bytes
```

### 6.5 Half Duplex 정책

초기 버전은 Half Duplex를 사용한다.

- 녹음 중 스피커 재생 금지
- 재생 중 마이크 처리 중지 또는 폐기
- 에코 제거 미적용
- 사용자가 버튼을 다시 누르면 재생 중단 여부는 2차 단계에서 결정

### 6.6 버튼 처리

- D9를 `INPUT_PULLUP`으로 설정
- 누름 상태: LOW
- 소프트웨어 디바운싱 20~50ms
- 길게 누르는 동안 녹음
- 버튼 해제 시 발화 종료 메시지 전송
- 최대 녹음 시간 제한 권장: 15~30초

### 6.7 펌웨어 설정 구조

```cpp
struct DeviceConfig {
    String websocketUrl;
    String deviceId;
    String authToken;
    String wifiSsid;
    String wifiPassword;
};
```

서버 URL은 코드에 하드코딩하지 않는다.

개발:

```text
ws://192.168.x.x:8000/ws/audio
```

운영:

```text
wss://voice.example.com/ws/audio
```

### 6.8 펌웨어 디렉터리

```text
firmware/xiao-esp32s3/
├─ include/
│  ├─ board_pins.h
│  ├─ config.h
│  ├─ protocol.h
│  └─ states.h
├─ src/
│  ├─ main.cpp
│  ├─ audio_input.cpp
│  ├─ audio_output.cpp
│  ├─ button.cpp
│  ├─ display.cpp
│  ├─ websocket_client.cpp
│  └─ state_machine.cpp
├─ test/
├─ partitions.csv
└─ platformio.ini
```

---

## 7. WebSocket 프로토콜

### 7.1 엔드포인트

```text
GET /health
WS  /ws/audio
```

### 7.2 연결 인증

초기 권장 방식:

```http
Authorization: Bearer <device-token>
X-Device-ID: device-001
```

ESP32 WebSocket 라이브러리가 커스텀 헤더 처리를 지원하지 않는 경우, 초기 연결 JSON으로 인증한다.

```json
{
  "type": "auth",
  "device_id": "device-001",
  "token": "<device-token>",
  "protocol_version": "1.0"
}
```

운영에서는 반드시 TLS 기반 `wss://`를 사용한다.

### 7.3 제어 메시지

#### 녹음 시작

```json
{
  "type": "audio_start",
  "request_id": "uuid",
  "format": "pcm_s16le",
  "sample_rate": 16000,
  "channels": 1
}
```

#### 녹음 종료

```json
{
  "type": "audio_end",
  "request_id": "uuid"
}
```

#### 서버 상태

```json
{
  "type": "state",
  "request_id": "uuid",
  "state": "thinking"
}
```

#### STT 결과

```json
{
  "type": "transcript",
  "request_id": "uuid",
  "text": "안녕하세요"
}
```

#### TTS 시작

```json
{
  "type": "tts_start",
  "request_id": "uuid",
  "format": "pcm_s16le",
  "sample_rate": 16000,
  "channels": 1
}
```

#### TTS 종료

```json
{
  "type": "tts_end",
  "request_id": "uuid"
}
```

#### 오류

```json
{
  "type": "error",
  "request_id": "uuid",
  "code": "STT_FAILED",
  "message": "Speech recognition failed"
}
```

### 7.4 바이너리 프레임

- 클라이언트 → 서버: PCM 음성 프레임
- 서버 → 클라이언트: PCM TTS 음성 프레임
- 각 바이너리 스트림은 직전 제어 메시지의 `request_id`에 귀속
- 한 연결에서 초기 버전은 동시에 하나의 요청만 허용

### 7.5 프로토콜 버전

모든 장치 연결은 `protocol_version`을 포함한다.

호환성 정책:

- 서버는 최소 1개 이전 펌웨어 버전을 지원
- Breaking change는 major version 증가
- 서버 선배포 후 펌웨어 순차 배포
- 펌웨어와 서버를 동시에 강제 변경하지 않음

---

## 8. 서버 애플리케이션 설계

### 8.1 기술 스택

- Python 3.12
- FastAPI
- Uvicorn
- WebSocket
- Azure Speech SDK
- OpenAI 호환 SDK 또는 Azure AI Foundry SDK
- httpx
- Redis
- Pydantic Settings
- structlog 또는 표준 logging
- pytest
- Ruff
- MyPy

### 8.2 서버 역할

- 장치 WebSocket 연결 관리
- 디바이스 인증
- PCM 버퍼링
- STT 요청
- OpenClaw 세션 처리
- LLM 호출
- TTS 생성
- 음성 스트리밍 반환
- 상태 메시지 전달
- 요청별 타임아웃 관리
- 로그 및 메트릭 기록
- 오류를 장치 친화적인 코드로 변환

### 8.3 서버 디렉터리

```text
services/voice-api/
├─ app/
│  ├─ main.py
│  ├─ config.py
│  ├─ api/
│  │  ├─ health.py
│  │  └─ websocket.py
│  ├─ core/
│  │  ├─ errors.py
│  │  ├─ logging.py
│  │  └─ security.py
│  ├─ audio/
│  │  ├─ buffer.py
│  │  ├─ format.py
│  │  └─ validation.py
│  ├─ clients/
│  │  ├─ azure_speech.py
│  │  ├─ foundry.py
│  │  └─ openclaw.py
│  ├─ sessions/
│  │  ├─ manager.py
│  │  └─ models.py
│  └─ schemas/
│     └─ websocket.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ contract/
├─ Dockerfile
├─ pyproject.toml
└─ README.md
```

### 8.4 처리 파이프라인

```text
WebSocket Receive
  ↓
Audio Validation
  ↓
Audio Buffer
  ↓
Azure Speech STT
  ↓
OpenClaw Context
  ↓
Azure AI Foundry LLM
  ↓
Azure Speech TTS
  ↓
PCM Chunk Streaming
  ↓
WebSocket Send
```

### 8.5 타임아웃 권장값

| 구간 | 초기값 |
|---|---:|
| WebSocket idle | 60초 |
| 최대 녹음 | 30초 |
| STT | 15초 |
| LLM | 30초 |
| TTS | 20초 |
| 전체 요청 | 60초 |

### 8.6 세션 관리

Redis에 저장할 수 있는 항목:

- `device_id`
- `session_id`
- 최근 대화 요약
- 캐릭터 설정 ID
- 요청 상태
- 마지막 연결 시간
- Rate Limit 카운터
- 최근 오류

초기 프로토타입에서는 메모리 세션도 가능하지만 운영 배포 시 Redis 사용을 권장한다.

---

## 9. Azure Speech 설계

### 9.1 STT

입력:

- PCM 16kHz
- 16-bit
- mono
- 한국어 기본

출력:

- 인식 텍스트
- 신뢰도 또는 상세 결과
- 인식 시간
- 오류 코드

### 9.2 TTS

입력:

- 캐릭터 응답 텍스트
- 음성 이름
- 언어
- 발화 속도 및 스타일

출력:

- PCM 16kHz mono 권장
- ESP32가 바로 재생할 수 있는 포맷

### 9.3 음성 설정

환경변수 예시:

```env
AZURE_SPEECH_REGION=koreacentral
AZURE_SPEECH_LANGUAGE=ko-KR
AZURE_SPEECH_VOICE=ko-KR-SunHiNeural
```

실제 음성 이름은 배포 시점의 Azure Speech 지원 목록을 기준으로 확정한다.

### 9.4 오류 처리

- No speech
- Timeout
- Invalid audio
- Authentication failure
- Quota exceeded
- Service unavailable

서비스 오류 시 장치에는 간결한 오류 코드만 전달하고, 상세 원인은 서버 로그에 기록한다.

---

## 10. OpenClaw 및 Azure AI Foundry 설계

### 10.1 역할 분리

OpenClaw:

- 캐릭터 프롬프트 관리
- 대화 세션
- 도구 호출
- 메모리 정책
- 응답 가드레일
- 외부 컨텍스트 조합

Azure AI Foundry 모델:

- 자연어 응답 생성
- 캐릭터 말투 반영
- 필요 시 Function Calling
- 짧은 음성 응답 생성

### 10.2 응답 정책

음성 대화 특성을 고려하여:

- 한 응답은 기본 1~3문장
- 불필요한 Markdown 금지
- 코드 블록 금지
- URL 직접 낭독 최소화
- 너무 긴 목록 금지
- 특수문자 최소화
- TTS 친화적 문장 사용

### 10.3 환경변수

```env
AZURE_FOUNDRY_BASE_URL=https://example.services.ai.azure.com/
AZURE_FOUNDRY_DEPLOYMENT_NAME=character-model
AZURE_FOUNDRY_API_KEY=replace-me

OPENCLAW_BASE_URL=http://openclaw:8080
OPENCLAW_TOKEN=replace-me
```

### 10.4 프롬프트 계층

```text
System Policy
  ↓
Character Definition
  ↓
Safety / Response Length Policy
  ↓
Conversation Summary
  ↓
Recent Messages
  ↓
Current User Transcript
```

---

## 11. 로컬 개발환경

### 11.1 필수 소프트웨어

Windows 11:

- Git
- GitHub CLI 선택
- Docker Desktop
- WSL2
- Visual Studio Code
- VS Code Remote - WSL
- Arduino IDE 또는 PlatformIO
- USB Serial Driver
- PowerShell 7 권장

WSL2:

- Ubuntu
- Git
- Make
- Docker CLI
- Python 선택
- Azure CLI 선택

### 11.2 소스 위치

권장:

```text
/home/<user>/projects/character-ai-bot
```

비권장:

```text
/mnt/c/Users/<user>/...
```

WSL Linux 파일시스템을 사용하면 파일 I/O 및 Docker 빌드 성능이 더 안정적이다.

### 11.3 로컬 실행

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f voice-api
```

### 11.4 개발용 URL

```text
HTTP Health:
http://localhost:8000/health

ESP32 WebSocket:
ws://<WINDOWS_LAN_IP>:8000/ws/audio
```

Windows 방화벽에서 개발 포트 접근 허용이 필요하다.

---

## 12. Docker 설계

### 12.1 원칙

- 모든 서버 애플리케이션은 Linux 컨테이너로 실행
- 하나의 이미지를 여러 환경에서 실행
- 설정은 환경변수와 외부 파일로 주입
- 이미지 내부에 비밀정보를 포함하지 않음
- 운영 VM에서 빌드하지 않음
- 버전을 고정
- non-root 사용자 사용
- 헬스체크 제공
- `latest`를 운영 기준 태그로 사용하지 않음

### 12.2 Voice API Dockerfile 예시

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml ./
COPY app ./app

RUN pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --retries=5 \
  CMD curl --fail http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 12.3 Compose 기본 구조

```yaml
services:
  voice-api:
    build:
      context: ./services/voice-api
    restart: unless-stopped
    env_file:
      - .env
    depends_on:
      redis:
        condition: service_healthy
    networks:
      - backend
    ports:
      - "8000:8000"

  openclaw:
    build:
      context: ./services/openclaw
    restart: unless-stopped
    networks:
      - backend

  redis:
    image: redis:7.4-alpine
    restart: unless-stopped
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis-data:/data
    networks:
      - backend
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

networks:
  backend:

volumes:
  redis-data:
```

### 12.4 환경 파일 분리

```text
compose.yaml
compose.dev.yaml
compose.prod.yaml
.env.example
```

실행:

```bash
docker compose -f compose.yaml -f compose.dev.yaml up -d
```

운영:

```bash
docker compose -f compose.yaml -f compose.prod.yaml up -d
```

---

## 13. GitHub 저장소 구조

```text
character-ai-bot/
├─ .github/
│  ├─ workflows/
│  │  ├─ ci.yml
│  │  ├─ build-images.yml
│  │  ├─ deploy-staging.yml
│  │  ├─ deploy-production.yml
│  │  └─ firmware.yml
│  ├─ CODEOWNERS
│  └─ pull_request_template.md
├─ firmware/
│  └─ xiao-esp32s3/
├─ services/
│  ├─ voice-api/
│  └─ openclaw/
├─ deploy/
│  ├─ compose.yaml
│  ├─ compose.dev.yaml
│  ├─ compose.prod.yaml
│  ├─ Caddyfile
│  └─ scripts/
│     ├─ deploy.sh
│     ├─ healthcheck.sh
│     └─ rollback.sh
├─ infrastructure/
│  └─ bicep/
├─ docs/
│  └─ PROJECT_PLAN.md
├─ .env.example
├─ .gitignore
├─ Makefile
└─ README.md
```

### 13.1 모노레포 선택 이유

- 펌웨어와 서버 프로토콜 변경을 하나의 PR에서 검토 가능
- Docker, 인프라, 서버, 펌웨어 버전 추적 용이
- 초기 프로젝트 운영 복잡도 감소
- GitHub Actions path filter로 필요한 작업만 실행 가능

---

## 14. Git 브랜치 전략

### 14.1 권장 방식

Trunk-based development를 사용한다.

```text
feature/*
  ↓ Pull Request
main
  ├─ staging 자동 배포
  └─ production 승인 배포
```

### 14.2 main 보호 규칙

- 직접 Push 금지
- Pull Request 필수
- CI 성공 필수
- 최소 1명 승인
- 최신 main 기준 rebase 또는 update 요구
- 대화 해결 요구
- force push 금지
- branch deletion 금지
- CODEOWNERS 적용

### 14.3 릴리스 태그

```text
server-v1.0.0
firmware-v1.0.0
infra-v1.0.0
```

서버와 펌웨어 버전은 독립적으로 관리할 수 있다.

---

## 15. CI 설계

### 15.1 PR CI 흐름

```text
Pull Request
  ↓
Changed Paths Detection
  ├─ Firmware Build/Test
  ├─ Voice API Lint/Test
  ├─ Docker Build
  ├─ Contract Test
  ├─ Secret Scan
  └─ Vulnerability Scan
  ↓
Required Checks
  ↓
Review / Merge
```

### 15.2 서버 검사

- Ruff lint
- Ruff format 또는 Black
- MyPy
- Pytest
- Coverage
- FastAPI API test
- WebSocket contract test
- Docker build
- Trivy scan
- Dependency vulnerability scan
- Secret scanning

### 15.3 펌웨어 검사

- PlatformIO build
- 컴파일 경고
- 단위 테스트
- 펌웨어 크기
- 프로토콜 상수 검증
- 빌드 산출물 업로드

### 15.4 CI 예시

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  voice-api:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: services/voice-api

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install
        run: pip install -e ".[dev]"

      - name: Lint
        run: ruff check app tests

      - name: Type check
        run: mypy app

      - name: Test
        run: pytest --cov=app --cov-report=term-missing

      - name: Docker build
        run: docker build -t character-voice-api:test .
```

---

## 16. CD 설계

### 16.1 최종 권장 구조

```text
GitHub Actions
  ↓ OIDC
Microsoft Entra ID
  ↓
Azure Container Registry
  ↓
Azure VM Managed Identity Pull
  ↓
Docker Compose
  ↓
Health Check / Smoke Test
  ↓
Success or Rollback
```

### 16.2 배포 흐름

```text
main 병합
  ↓
Docker 이미지 빌드
  ↓
SHA 태그 생성
  ↓
ACR Push
  ↓
staging 자동 배포
  ↓
health check
  ↓
smoke test
  ↓
production 승인
  ↓
production 배포
  ↓
실패 시 이전 SHA로 롤백
```

### 16.3 이미지 태그

```text
character-voice-api:sha-a82f37c2e118
character-voice-api:v1.3.0
character-voice-api:production
```

운영 Compose는 불변 SHA 태그를 사용한다.

### 16.4 Azure 인증

GitHub Actions는 OIDC를 사용한다.

GitHub Variables:

```text
AZURE_CLIENT_ID
AZURE_TENANT_ID
AZURE_SUBSCRIPTION_ID
AZURE_RESOURCE_GROUP
AZURE_VM_NAME
ACR_NAME
```

장기 Azure 비밀번호 또는 Service Principal Secret 저장은 피한다.

### 16.5 ACR 권한

| 주체 | 권한 |
|---|---|
| GitHub Actions Identity | ACR Push |
| Azure VM Managed Identity | ACR Pull |
| 애플리케이션 Managed Identity | Key Vault Secret Read |
| 운영자 | 최소 권한 |

### 16.6 운영 VM 배포 방식

초기 권장:

- GitHub-hosted runner
- Azure OIDC 로그인
- Azure VM Run Command로 배포 스크립트 실행
- VM에서 `docker compose pull`
- VM에서 `docker compose up -d`
- 헬스체크 실패 시 rollback

운영 VM에 GitHub self-hosted runner를 직접 설치하는 방식은 공격 표면과 권한 범위가 커지므로 기본안으로 채택하지 않는다.

### 16.7 배포 워크플로 예시

```yaml
name: Deploy Production

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: Image tag
        required: true

permissions:
  contents: read
  id-token: write

concurrency:
  group: production
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
      - uses: actions/checkout@v4

      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}

      - name: Deploy
        env:
          IMAGE_TAG: ${{ inputs.image_tag }}
        run: |
          az vm run-command invoke \
            --resource-group "${{ vars.AZURE_RESOURCE_GROUP }}" \
            --name "${{ vars.AZURE_VM_NAME }}" \
            --command-id RunShellScript \
            --scripts "
              cd /opt/character-bot &&
              ./scripts/deploy.sh '$IMAGE_TAG'
            "
```

---

## 17. Azure 운영환경

### 17.1 권장 리소스

- Resource Group
- Virtual Network
- Subnet
- Network Security Group
- Ubuntu VM
- Managed Disk
- Public IP
- Azure Container Registry
- Azure Key Vault
- Log Analytics Workspace
- Azure Monitor
- DNS Zone 또는 외부 DNS
- Azure Speech Resource
- Azure AI Foundry Project/Deployment

### 17.2 네트워크 포트

| 포트 | 공개 범위 |
|---|---|
| 22 | 관리자 IP 또는 Bastion만 |
| 80 | HTTPS redirect 용도 선택 |
| 443 | 외부 공개 |
| 8000 | 외부 공개 금지 |
| 6379 | 외부 공개 금지 |
| OpenClaw 내부 포트 | 외부 공개 금지 |

### 17.3 VM 디렉터리

```text
/opt/character-bot/
├─ compose.yaml
├─ compose.prod.yaml
├─ Caddyfile
├─ runtime.env
├─ secrets/
├─ scripts/
│  ├─ deploy.sh
│  ├─ healthcheck.sh
│  └─ rollback.sh
└─ state/
   └─ current-image.env
```

운영 VM에는 애플리케이션 소스 전체를 둘 필요가 없다.

### 17.4 Reverse Proxy

Caddy 권장:

- TLS 자동 관리
- `wss://` WebSocket 프록시
- HTTP → HTTPS 리다이렉트
- 보안 헤더
- 요청 로그

예시:

```caddyfile
voice.example.com {
    reverse_proxy voice-api:8000
}
```

---

## 18. 비밀정보 및 보안

### 18.1 금지 사항

- Azure API Key를 ESP32 펌웨어에 저장
- `.env`를 Git에 Commit
- Docker 이미지에 Secret 포함
- 운영 VM에 GitHub Personal Access Token 저장
- ACR admin 계정 상시 사용
- HTTP 또는 `ws://` 운영
- Redis 외부 공개
- 운영 서버에서 root 컨테이너 실행
- `latest`만 이용한 운영 배포

### 18.2 Key Vault 저장 대상

- Azure Speech Key
- Azure AI Foundry API Key
- OpenClaw Token
- Device Token Signing Key
- 관리자용 내부 Secret

가능한 Azure 서비스는 Managed Identity 인증으로 전환한다.

### 18.3 장치 인증

초기:

- 장치별 임의 토큰
- 서버에서 해시 또는 안전한 저장소 관리
- 토큰 폐기 가능
- Device ID와 토큰 동시 검증

향후:

- 장치별 인증서
- 프로비저닝 API
- 짧은 수명의 액세스 토큰
- OTA 서명 검증

### 18.4 Rate Limiting

장치별 제한 예시:

- 동시 요청 1개
- 분당 요청 수 제한
- 최대 음성 길이
- 최대 메시지 크기
- 연결 재시도 backoff
- 인증 실패 차단

---

## 19. 로깅 및 모니터링

### 19.1 로그 필드

```json
{
  "timestamp": "2026-07-26T12:00:00Z",
  "level": "INFO",
  "service": "voice-api",
  "version": "sha-a82f37c2e118",
  "device_id": "device-001",
  "session_id": "session-uuid",
  "request_id": "request-uuid",
  "event": "tts_completed",
  "duration_ms": 820
}
```

### 19.2 기록 대상

- 연결 및 해제
- 인증 성공/실패
- 녹음 길이
- STT 지연
- LLM 지연
- TTS 지연
- 전체 요청 지연
- 오류 코드
- 재시도
- 배포 버전
- 장치 펌웨어 버전

### 19.3 개인정보 원칙

- 원본 음성은 기본적으로 영구 저장하지 않음
- 전체 사용자 발화 로그는 개발 환경에서만 제한적으로 사용
- 운영에서는 필요 최소 텍스트만 저장
- 민감정보 마스킹
- 보존 기간 정의
- 디버깅 모드와 운영 모드 분리

### 19.4 주요 메트릭

- WebSocket active connections
- Requests per minute
- STT success rate
- LLM success rate
- TTS success rate
- P50/P95 latency
- Error rate
- Container restart count
- Redis availability
- CPU/Memory/Disk
- VM health

---

## 20. 헬스체크 및 롤백

### 20.1 Health Endpoint

```json
{
  "status": "ok",
  "version": "sha-a82f37c2e118",
  "redis": "ok",
  "openclaw": "ok",
  "azure_speech": "configured",
  "azure_foundry": "configured"
}
```

일반 헬스체크에서는 Azure API를 매번 실제 호출하지 않는다.

### 20.2 Smoke Test

배포 후 별도 실행:

1. WebSocket 연결
2. 인증
3. 짧은 테스트 PCM 전송
4. STT 확인
5. LLM 응답 확인
6. TTS 데이터 수신 확인
7. 전체 지연 기록

### 20.3 롤백

```text
현재 버전 저장
  ↓
신규 이미지 Pull
  ↓
신규 컨테이너 시작
  ↓
Health Check
  ↓
Smoke Test
  ├─ 성공: current version 갱신
  └─ 실패: 이전 SHA 이미지 재기동
```

롤백 스크립트 예시:

```bash
#!/usr/bin/env bash
set -euo pipefail

PREVIOUS_TAG="$(cat /opt/character-bot/state/previous-tag)"
export VOICE_API_IMAGE_TAG="$PREVIOUS_TAG"

docker compose \
  -f compose.yaml \
  -f compose.prod.yaml \
  pull voice-api

docker compose \
  -f compose.yaml \
  -f compose.prod.yaml \
  up -d --no-deps voice-api
```

---

## 21. 테스트 전략

### 21.1 테스트 피라미드

```text
          Hardware E2E
         Integration
        Contract Tests
       Unit Tests
```

### 21.2 단위 테스트

- 오디오 헤더 및 프레임 검증
- 상태 전이
- 오류 매핑
- 프롬프트 생성
- 세션 만료
- 환경설정 유효성
- 인증 토큰 검증

### 21.3 통합 테스트

- FastAPI WebSocket
- Redis
- OpenClaw mock
- Azure Speech mock
- Foundry mock
- TTS binary chunk return

### 21.4 계약 테스트

펌웨어와 서버가 공유해야 하는 항목:

- 메시지 type
- 필수 필드
- 오디오 포맷
- 상태 코드
- 프로토콜 버전
- 최대 프레임 크기

### 21.5 하드웨어 E2E

- 버튼 누름/해제
- 5초 발화
- OLED 상태 순서
- STT 결과
- 캐릭터 응답
- 스피커 재생
- 재연결
- Wi-Fi 단절 복구
- 서버 재시작 복구
- 장시간 반복 테스트

### 21.6 성능 테스트

- 10분 연속 반복
- 100회 대화
- 최대 녹음 길이
- Wi-Fi 품질 저하
- TTS 긴 응답
- Redis 지연
- Azure API 일시 실패

---

## 22. 펌웨어 CI/CD

### 22.1 CI

```text
Firmware PR
  ↓
PlatformIO Build
  ↓
Unit Test
  ↓
Size Report
  ↓
Artifact Upload
```

### 22.2 Release Artifact

- `firmware.bin`
- `bootloader.bin`
- `partitions.bin`
- `firmware-manifest.json`
- checksum
- release notes

### 22.3 OTA 확장

향후 OTA 시:

- HTTPS 다운로드
- 서명된 Manifest
- SHA-256 검증
- 펌웨어 서명
- 이전 버전 fallback
- 단계적 배포
- 서버 API 하위 호환성 유지

---

## 23. 인프라 코드화

Azure 리소스는 Bicep 우선 사용을 권장한다.

```text
infrastructure/bicep/
├─ main.bicep
├─ modules/
│  ├─ network.bicep
│  ├─ vm.bicep
│  ├─ acr.bicep
│  ├─ keyvault.bicep
│  ├─ monitor.bicep
│  └─ role-assignments.bicep
└─ parameters/
   ├─ staging.bicepparam
   └─ production.bicepparam
```

### 23.1 관리 대상

- VNet/Subnet
- NSG
- VM
- Public IP
- Managed Identity
- ACR
- Key Vault
- Log Analytics
- Role Assignment
- Monitoring Alert

### 23.2 인프라 변경 절차

```text
Bicep 변경
  ↓
Pull Request
  ↓
Lint / What-if
  ↓
Review
  ↓
승인
  ↓
배포
```

---

## 24. 개발 단계 및 WBS

### Phase 0. 프로젝트 기준선

- [ ] GitHub 저장소 생성
- [ ] 디렉터리 구조 생성
- [ ] `.env.example` 작성
- [ ] PR 규칙 및 CODEOWNERS
- [ ] 개발 문서 Commit

### Phase 1. 하드웨어 검증

- [ ] 버튼 D9 입력 확인
- [ ] OLED 출력 확인
- [ ] INMP441 PCM 수집 확인
- [ ] MAX98357A 사인파 재생
- [ ] 스피커 음량 및 노이즈 확인
- [ ] 실제 핀맵 확정

### Phase 2. 펌웨어 통합

- [ ] 상태 머신
- [ ] 버튼 디바운싱
- [ ] Wi-Fi 연결
- [ ] WebSocket 연결
- [ ] PCM 프레임 전송
- [ ] PCM 수신 및 재생
- [ ] OLED 상태 표시
- [ ] 재연결 로직

### Phase 3. 로컬 서버

- [ ] FastAPI 기본 프로젝트
- [ ] `/health`
- [ ] `/ws/audio`
- [ ] 오디오 버퍼
- [ ] Mock STT
- [ ] Mock LLM
- [ ] Mock TTS
- [ ] ESP32 왕복 테스트

### Phase 4. Azure AI 연동

- [ ] Azure Speech STT
- [ ] Foundry 모델 호출
- [ ] OpenClaw 세션
- [ ] Azure Speech TTS
- [ ] 오류 처리
- [ ] 타임아웃 및 재시도

### Phase 5. Docker

- [ ] Voice API Dockerfile
- [ ] OpenClaw 컨테이너
- [ ] Redis
- [ ] Compose
- [ ] 개발 환경변수
- [ ] Caddy 개발 설정
- [ ] Windows 11 Docker 검증

### Phase 6. CI

- [ ] Python lint
- [ ] Python test
- [ ] Firmware build
- [ ] Docker build
- [ ] Secret scan
- [ ] Vulnerability scan
- [ ] Required checks

### Phase 7. Azure Staging

- [ ] Bicep
- [ ] ACR
- [ ] Ubuntu VM
- [ ] Managed Identity
- [ ] Key Vault
- [ ] DNS/TLS
- [ ] Staging 자동 배포
- [ ] Smoke test

### Phase 8. Production

- [ ] GitHub Environment 승인
- [ ] Production VM
- [ ] 운영 Secret
- [ ] 모니터링
- [ ] 로그 보존
- [ ] 자동 롤백
- [ ] 백업
- [ ] 운영 절차서

### Phase 9. 안정화

- [ ] 100회 반복 테스트
- [ ] 장시간 연결 테스트
- [ ] Wi-Fi 장애 테스트
- [ ] Azure 장애 테스트
- [ ] 메모리 누수 확인
- [ ] 음성 품질 튜닝
- [ ] 지연 최적화

---

## 25. 완료 기준

### 25.1 MVP 완료 조건

- ESP32 버튼 입력으로 녹음 시작/종료
- 로컬 Docker 서버와 WebSocket 통신
- Azure STT로 발화 인식
- OpenClaw 및 Foundry로 응답 생성
- Azure TTS 음성을 ESP32로 재생
- OLED 상태 표시 정상
- 20회 연속 대화 성공
- 인증되지 않은 장치 차단
- Docker Compose 한 명령 실행
- GitHub PR CI 통과
- Azure Staging 자동 배포 성공

### 25.2 Production Ready 조건

- HTTPS/WSS
- Key Vault
- Managed Identity
- ACR SHA 이미지
- GitHub Environment 승인
- 자동 헬스체크
- 자동 롤백
- 중앙 로그
- 경고 알림
- 운영 백업
- 장애 대응 문서
- 부하 및 장시간 테스트 완료

---

## 26. 주요 리스크 및 대응

| 리스크 | 영향 | 대응 |
|---|---|---|
| 마이크와 스피커 간 에코 | STT 품질 저하 | Half Duplex, 물리적 분리 |
| I2S 핀 충돌 | 동작 불가 | 핀맵 단일 관리 및 초기 검증 |
| Wi-Fi 불안정 | 음성 끊김 | 재연결, 버퍼, backoff |
| Azure 지연 | 체감 품질 저하 | 짧은 응답, 스트리밍 확장 |
| Azure API 장애 | 대화 실패 | 명확한 오류, 재시도, 타임아웃 |
| Secret 유출 | 보안 사고 | OIDC, Key Vault, scanning |
| 운영 VM 단일 장애 | 서비스 중단 | 백업, 자동 재시작, 향후 이중화 |
| 펌웨어/서버 불일치 | 프로토콜 오류 | Versioning, 하위 호환성 |
| 긴 LLM 응답 | TTS 지연 | 응답 길이 정책 |
| Docker Desktop 의존 | 운영 불안정 | 운영은 Ubuntu Docker Engine 권장 |

---

## 27. 최종 기술 결정 요약

| 영역 | 결정 |
|---|---|
| MCU | Seeed Studio XIAO ESP32S3 |
| 입력 | INMP441 + Push-to-Talk |
| 출력 | MAX98357A + Speaker |
| 표시 | 0.96" OLED |
| 버튼 | D9-GND, INPUT_PULLUP |
| 오디오 | PCM 16kHz, mono, signed 16-bit LE |
| 통신 | Wi-Fi WebSocket |
| 서버 | Python FastAPI/Uvicorn |
| STT/TTS | Azure Speech |
| LLM | Azure AI Foundry |
| 에이전트 | OpenClaw |
| 세션 | Redis |
| 로컬 | Windows 11 + WSL2 + Docker Desktop |
| 운영 | Azure Ubuntu VM + Docker Engine |
| Reverse Proxy | Caddy |
| Registry | Azure Container Registry |
| Secret | Azure Key Vault |
| CI/CD | GitHub Actions |
| Azure 인증 | GitHub OIDC |
| 배포 단위 | SHA 태그 Docker 이미지 |
| 배포 방식 | ACR Pull + Docker Compose |
| 운영 승인 | GitHub Environment |
| 롤백 | 이전 SHA 이미지 재기동 |
| 인프라 코드 | Bicep |
| 저장소 | GitHub Monorepo |

---

## 28. 환경변수 예시

```env
APP_ENV=development
LOG_LEVEL=INFO
APP_VERSION=dev

HOST=0.0.0.0
PORT=8000

REDIS_URL=redis://redis:6379/0
OPENCLAW_BASE_URL=http://openclaw:8080
OPENCLAW_TOKEN=replace-me

AZURE_SPEECH_REGION=koreacentral
AZURE_SPEECH_KEY=replace-me
AZURE_SPEECH_LANGUAGE=ko-KR
AZURE_SPEECH_VOICE=ko-KR-SunHiNeural

AZURE_FOUNDRY_BASE_URL=https://example.services.ai.azure.com/
AZURE_FOUNDRY_API_KEY=replace-me
AZURE_FOUNDRY_DEPLOYMENT_NAME=character-model

DEVICE_TOKEN_SIGNING_KEY=replace-me
MAX_AUDIO_SECONDS=30
WEBSOCKET_IDLE_TIMEOUT_SECONDS=60
```

`.gitignore`:

```gitignore
.env
.env.*
!.env.example

__pycache__/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

.vscode/
.idea/

.pio/
firmware/**/.pio/

logs/
*.log
```

---

## 29. 운영 체크리스트

### 배포 전

- [ ] CI 성공
- [ ] 이미지 취약점 기준 통과
- [ ] Staging smoke test 성공
- [ ] DB/Redis 호환성 확인
- [ ] 프로토콜 하위 호환성 확인
- [ ] 운영 승인
- [ ] 이전 이미지 태그 기록

### 배포 후

- [ ] Container healthy
- [ ] `/health` 정상
- [ ] WebSocket 연결 정상
- [ ] STT 정상
- [ ] LLM 정상
- [ ] TTS 정상
- [ ] P95 지연 확인
- [ ] 오류율 확인
- [ ] 이전 버전 rollback 가능 확인

### 장애 발생 시

1. 신규 배포 직후인지 확인
2. 컨테이너 상태 확인
3. 최근 배포 SHA 확인
4. Caddy/Voice API/Redis 로그 확인
5. Azure Speech 및 Foundry 상태 확인
6. 이전 SHA로 롤백
7. 원인 분석 Issue 생성
8. 수정 PR 작성
9. 재배포 전 Staging 검증

---

## 30. 결론

본 프로젝트의 최종 기준 구조는 Windows 11에서 Linux 컨테이너 기반으로 개발하고, GitHub Pull Request와 GitHub Actions로 검증한 이미지를 Azure Container Registry에 등록한 뒤, Azure Ubuntu VM에서 동일 이미지를 Docker Compose로 실행하는 방식이다.

ESP32는 음성 입출력과 장치 UI에 집중하고, Azure 자격 증명, STT, LLM, TTS, 세션 및 운영 로직은 서버에 집중한다. 이를 통해 장치 펌웨어의 복잡도를 낮추고, AI 모델과 서버 기능을 독립적으로 개선할 수 있다.

초기에는 단일 VM과 Half Duplex 구조로 안정적인 MVP를 완성하고, 이후 스트리밍 처리, OTA, 다중 장치, 관리 대시보드, 고가용성 구조로 확장한다.

---

## 부록 A. 전체 처리 시퀀스

```text
User
 │
 │ Press Button
 ▼
ESP32
 │ audio_start
 │ PCM frames
 │ audio_end
 ▼
Voice API
 │
 ├─> Azure Speech STT
 │      └─ transcript
 │
 ├─> OpenClaw
 │      └─ context / character
 │
 ├─> Azure AI Foundry
 │      └─ response text
 │
 ├─> Azure Speech TTS
 │      └─ PCM audio
 │
 └─> ESP32
        ├─ OLED: Speaking
        └─ Speaker Playback
```

## 부록 B. CI/CD 시퀀스

```text
Developer
 │
 │ Push Feature Branch
 ▼
GitHub Pull Request
 │
 ├─ Lint
 ├─ Test
 ├─ Firmware Build
 ├─ Docker Build
 ├─ Security Scan
 └─ Review
 │
 ▼
Merge to main
 │
 ▼
GitHub Actions
 │ OIDC
 ▼
Azure Container Registry
 │
 │ Push sha-<commit>
 ▼
Staging VM
 │ Pull / Deploy / Smoke Test
 ▼
Production Approval
 │
 ▼
Production VM
 │ Pull / Deploy / Health Check
 ├─ Success
 └─ Failure → Rollback
```

## 부록 C. 문서 변경 관리

문서 변경은 코드와 동일하게 Pull Request로 관리한다.

권장 Commit 예시:

```text
docs: establish project development baseline
docs: update websocket protocol to v1.1
docs: add production rollback procedure
```

문서 버전 규칙:

- v1.0: 초기 개발 기준선
- v1.1: 비파괴적 상세 추가
- v2.0: 아키텍처 또는 프로토콜 주요 변경
