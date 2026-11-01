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

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "AppConfig":
        return cls(
            mode=str(values.get("mode", "master")),
            database_path=str(values.get("database_path", "")),
            seed_path=str(values.get("seed_path", "")),
            publish_path=str(values.get("publish_path", "")),
            publish_on_start=bool(values.get("publish_on_start", True)),
            snapshot_path=str(values.get("snapshot_path", "")),
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "database_path": self.database_path,
            "seed_path": self.seed_path,
            "publish_path": self.publish_path,
            "publish_on_start": self.publish_on_start,
            "snapshot_path": self.snapshot_path,
        }
