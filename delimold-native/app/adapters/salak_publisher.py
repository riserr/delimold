"""Filesystem adapter for atomically publishing an already-filtered snapshot."""
import json
import os
import tempfile
from pathlib import Path

from app.application.ports import SnapshotPublisher, SnapshotReader
from app.domain.errors import PublishError, StorageError


class JsonSnapshotPublisher(SnapshotPublisher):
    def publish(self, snapshot, destination):
        target = Path(destination)
        try:
            target.mkdir(parents=True, exist_ok=True)
            fd, temporary = tempfile.mkstemp(prefix=".delimold-", suffix=".tmp", dir=str(target))
            try:
                with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                    payload = snapshot.as_dict() if hasattr(snapshot, "as_dict") else snapshot
                    json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, str(target / "catalog.json"))
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        except (OSError, TypeError, ValueError) as exc:
            raise PublishError("Snapshot tidak dapat ditulis ke folder SALAK.") from exc


class JsonSnapshotReader(SnapshotReader):
    def read(self, path):
        try:
            with Path(path).open("r", encoding="utf-8") as stream:
                payload = json.load(stream)
            if not isinstance(payload, dict) or not isinstance(payload.get("collections"), dict):
                raise ValueError("format snapshot tidak valid")
            return payload
        except (OSError, ValueError) as exc:
            raise StorageError("Snapshot DELIMOLD tidak dapat dibaca.") from exc
