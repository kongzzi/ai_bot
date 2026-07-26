from app.sessions.models import Session


class SessionManager:
    """메모리 세션 (Phase 3). 운영 배포 시 Redis로 교체한다 (기획서 8.6)."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, device_id: str) -> Session:
        session = Session(device_id=device_id)
        self._sessions[device_id] = session
        return session

    def get(self, device_id: str) -> Session | None:
        return self._sessions.get(device_id)

    def remove(self, device_id: str) -> None:
        self._sessions.pop(device_id, None)
