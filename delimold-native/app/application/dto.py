"""Typed request and response values for UI-to-use-case interactions."""
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from app.domain.models import Actor, AppConfig


RecordData = Mapping[str, Any]
RecordRows = Mapping[str, RecordData]
FilterValues = Mapping[str, str]
ExportRow = Sequence[Any]


@dataclass(frozen=True)
class AuthenticationRequest:
    username: str
    password: str
    computer: str = ""


@dataclass(frozen=True)
class InitialSupervisorRequest:
    username: str
    display_name: str
    password: str


@dataclass(frozen=True)
class UserSaveRequest:
    actor: Actor
    username: str
    display_name: str
    role: str
    password: str = ""
    enabled: bool = True
    existing: bool = False


@dataclass(frozen=True)
class UserEnabledRequest:
    actor: Actor
    username: str
    enabled: bool


@dataclass(frozen=True)
class UserDeleteRequest:
    actor: Actor
    username: str


@dataclass(frozen=True)
class UserSummary:
    username: str
    display_name: str
    role: str
    enabled: bool

    def as_dict(self) -> Dict[str, Any]:
        return {"username": self.username, "display_name": self.display_name,
                "role": self.role, "enabled": self.enabled}


@dataclass(frozen=True)
class AuditEntry:
    id: int
    at: str
    action: str
    collection: str
    record_key: str
    username: str
    computer: str
    reason: str
    detail: str = ""

    def as_dict(self) -> Dict[str, Any]:
        return {"id": self.id, "at": self.at, "action": self.action,
                "collection": self.collection, "record_key": self.record_key,
                "username": self.username, "computer": self.computer,
                "reason": self.reason, "detail": self.detail}


@dataclass(frozen=True)
class FilterOptionsQuery:
    collection: str
    field: str


@dataclass(frozen=True)
class AuditQuery:
    limit: int = 200


@dataclass(frozen=True)
class SnapshotReadRequest:
    path: str


@dataclass(frozen=True)
class CatalogPageQuery:
    collection: str
    offset: int
    limit: int
    search: str = ""
    filters: Optional[FilterValues] = None


@dataclass(frozen=True)
class CatalogPageResult:
    collection: str
    rows: RecordRows
    stats: Mapping[str, int]
    lookups: Mapping[str, RecordRows] = field(default_factory=dict)


@dataclass(frozen=True)
class CatalogResult:
    schema_version: int
    revision: int
    updated_at: str
    collections: RecordRows
    events: Tuple[Any, ...] = ()
    deleted: Tuple[Any, ...] = ()

    def as_dict(self) -> Dict[str, Any]:
        return {"schemaVersion": self.schema_version, "revision": self.revision,
                "updatedAt": self.updated_at, "collections": dict(self.collections),
                "events": list(self.events), "deleted": list(self.deleted)}


@dataclass(frozen=True)
class FilterOption:
    label: str
    value: str


@dataclass(frozen=True)
class CatalogExportQuery:
    collection: str
    search: str = ""
    filters: Optional[FilterValues] = None


@dataclass(frozen=True)
class CatalogExportResult:
    rows: RecordRows
    lookups: Mapping[str, RecordRows] = field(default_factory=dict)


@dataclass(frozen=True)
class RecordSaveRequest:
    actor: Actor
    collection: str
    key: str
    value: RecordData
    action: str = "save"
    reason: str = ""


@dataclass(frozen=True)
class RecordBatchSaveRequest:
    actor: Actor
    collection: str
    items: Tuple[Tuple[str, RecordData], ...]
    action: str = "import"


@dataclass(frozen=True)
class RecordDeleteRequest:
    actor: Actor
    collection: str
    key: str
    reason: str = ""


@dataclass(frozen=True)
class LocationUpdateRequest:
    actor: Actor
    current_config: AppConfig
    updated_config: AppConfig


@dataclass(frozen=True)
class LocationUpdateResult:
    publication_pending: bool = False
    message: str = ""


@dataclass(frozen=True)
class WorkbookReadRequest:
    actor: Actor
    collection: str
    path: str


@dataclass(frozen=True)
class WorkbookTemplateRequest:
    actor: Actor
    collection: str
    path: str
    headings: Tuple[str, ...]


@dataclass(frozen=True)
class ExcelExportRequest:
    actor: Actor
    collection: str
    path: str
    headings: Tuple[str, ...]
    rows: Tuple[ExportRow, ...]


@dataclass(frozen=True)
class PdfExportRequest:
    actor: Actor
    collection: str
    path: str
    title: str
    headings: Tuple[str, ...]
    rows: Tuple[ExportRow, ...]
