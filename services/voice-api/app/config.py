from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    log_level: str = "INFO"
    app_version: str = "dev"

    # 오디오 규격 (기획서 6.4: PCM 16kHz mono s16le, 20ms 프레임 = 640 bytes)
    sample_rate: int = 16000
    channels: int = 1
    bytes_per_sample: int = 2
    frame_bytes: int = 640

    max_audio_seconds: int = 30
    websocket_idle_timeout_seconds: int = 60
    auth_timeout_seconds: int = 10

    # 개발용 장치 토큰: "device_id:token" 쉼표 구분.
    # 운영에서는 해시 저장 + Key Vault로 전환한다 (기획서 18.3).
    device_tokens: str = "device-001:dev-token-001"

    @property
    def max_audio_bytes(self) -> int:
        return self.sample_rate * self.bytes_per_sample * self.max_audio_seconds


@lru_cache
def get_settings() -> Settings:
    return Settings()
