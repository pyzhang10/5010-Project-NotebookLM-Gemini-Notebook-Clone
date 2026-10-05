from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Notebook:
    id: str
    name: str
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Chunk:
    id: str
    source_id: str
    source_name: str
    source_type: str
    location: str
    text: str
    url: str = ""

    def metadata(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_type": self.source_type,
            "location": self.location,
            "url": self.url,
            "chunk_id": self.id,
        }

