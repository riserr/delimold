"""Filesystem adapter for atomically publishing an already-filtered snapshot."""
import json
import os
import tempfile
import threading
import time
from pathlib import Path

from app.application.ports import SnapshotPublisher, SnapshotReader
from app.domain.errors import PublishError, StorageError

_locks_guard = threading.Lock()
_destination_locks = {}
_RETRY_DELAYS = (0.025, 0.05, 0.1, 0.2, 0.2, 0.2)


def _destination_lock(path):
    key = str(path.resolve())
    with _locks_guard:
        return _destination_locks.setdefault(key, threading.Lock())


class JsonSnapshotPublisher(SnapshotPublisher):
    def publish(self, snapshot, destination):
        target = Path(destination)
        try:
            with _destination_lock(target):
                target.mkdir(parents=True, exist_ok=True)
                fd, temporary = tempfile.mkstemp(prefix=".delimold-", suffix=".tmp", dir=str(target))
                try:
                    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                        payload = snapshot.as_dict() if hasattr(snapshot, "as_dict") else snapshot
                        json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
                        stream.flush()
                        os.fsync(stream.fileno())
                    self._replace_with_retry(temporary, target / "catalog.json")
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
        except (OSError, TypeError, ValueError) as exc:
            raise PublishError("Snapshot tidak dapat ditulis ke folder SALAK.") from exc

    @staticmethod
    def _replace_with_retry(source, destination):
        for delay in (*_RETRY_DELAYS, None):
            try:
                os.replace(source, str(destination))
                return
            except OSError:
                if delay is None:
                    raise
                time.sleep(delay)


class JsonSnapshotReader(SnapshotReader):
    def read(self, path):
        for delay in (*_RETRY_DELAYS[:4], None):
            try:
                with Path(path).open("r", encoding="utf-8") as stream:
                    payload = json.load(stream)
                if not isinstance(payload, dict) or not isinstance(payload.get("collections"), dict):
                    raise ValueError("format snapshot tidak valid")
                return payload
            except (OSError, ValueError) as exc:
                if delay is None:
                    raise StorageError("Snapshot DELIMOLD tidak dapat dibaca.") from exc
                # SMB/Windows can briefly deny a read while another process
                # replaces the published file. The previous file remains valid.
                time.sleep(delay)
