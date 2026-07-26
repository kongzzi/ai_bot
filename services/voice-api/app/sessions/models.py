import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Session:
    device_id: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    history: list[dict] = field(default_factory=list)
