"""Framework-independent DELIMOLD values and records."""
from dataclasses import dataclass
from typing import Any, Dict, Mapping


@dataclass(frozen=True)
class Actor:
    username: str
    display_name: str
    role: str
    computer: str = ""


@dataclass(frozen=True)
class Record:
    collection: str
    key: str
    value: Mapping[str, Any]


@dataclass(frozen=True)
class PublicSnapshot:
    schema_version: int
    revision: int
    updated_at: str
    collections: Dict[str, Dict[str, Any]]

    def as_dict(self):
        return {
            "schemaVersion": self.schema_version,
            "revision": self.revision,
            "updatedAt": self.updated_at,
            "collections": self.collections,
            "events": [],
            "deleted": [],
        }


@dataclass(frozen=True)
class SaveResult:
    revision: int
    publish_pending: bool = False


@dataclass(frozen=True)
class AppConfig:
    mode: str
    database_path: str
    seed_path: str
    publish_path: str
    publish_on_start: bool = True
    snapshot_path: str = ""
