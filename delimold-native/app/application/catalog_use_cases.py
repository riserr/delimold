"""Catalog query, mutation, and publication workflows."""
from typing import Tuple

from app.application.dto import (CatalogExportQuery, CatalogExportResult, CatalogPageQuery,
                                CatalogPageResult, CatalogResult, FilterOption,
                                FilterOptionsQuery, RecordBatchSaveRequest,
                                RecordDeleteRequest, RecordSaveRequest, SnapshotReadRequest)
from app.application.ports import (CatalogRepository, SeedCatalogReader, SnapshotPublisher,
                                   SnapshotReader)
from app.domain.errors import PublishError, ValidationError
from app.domain.models import Actor, PublicSnapshot, SaveResult
from app.domain.permissions import PUBLIC_COLLECTIONS, SUPERVISOR_COLLECTIONS, require_access
from app.domain.validation import validate_record


class CatalogUseCases:
    def __init__(self, repository: CatalogRepository, publisher: SnapshotPublisher,
                 snapshot_reader: SnapshotReader = None, publish_path: str = "",
                 seed_reader: SeedCatalogReader = None):
        self._repository = repository
        self._publisher = publisher
        self._snapshot_reader = snapshot_reader
        self._publish_path = publish_path
        self._seed_reader = seed_reader

    def initialize_catalog_if_empty(self, seed_path: str) -> bool:
        if not self._repository:
            raise ValidationError("Database utama belum disiapkan.")
        if not self._repository.is_empty():
            return False
        if self._seed_reader is None:
            raise ValidationError("Pembaca katalog awal belum disiapkan.")
        self._repository.import_catalog(self._seed_reader.read(seed_path), publish_required=True)
        return True

    def catalog(self, actor: Actor) -> CatalogResult:
        allowed = SUPERVISOR_COLLECTIONS if actor.role == "SUPERVISOR" else tuple(
            name for name in SUPERVISOR_COLLECTIONS if name in PUBLIC_COLLECTIONS or
            (actor.role == "ENGINEER" and name == "projects"))
        collections = self._repository.get_collections(allowed)
        metadata = self._repository.catalog_metadata()
        return CatalogResult(2, metadata["revision"], metadata["updated_at"], collections)

    def catalog_page(self, actor: Actor, query: CatalogPageQuery) -> CatalogPageResult:
        collection = query.collection
        require_access(actor, "read", collection)
        if collection in ("accounts", "history", "pattern_art"):
            raise ValidationError("Koleksi ini belum mendukung halaman katalog.")
        unique_fields = {"molds": "spec", "containers": "code", "patterns": "code",
                         "stickers": "name", "projects": "spec", "purchases": "spec"}
        unique_field = unique_fields.get(collection)
        if not unique_field:
            raise ValidationError("Koleksi tidak dikenal.")
        rows = self._repository.list_records_page(collection, query.offset, query.limit,
                                                  query.search, query.filters)
        stats = self._repository.record_stats(collection, unique_field, query.search, query.filters)
        lookups = self._repository.get_collections(("patterns", "containers")) if collection == "molds" else {}
        return CatalogPageResult(collection, rows, stats, lookups)

    def filter_options(self, actor: Actor, query: FilterOptionsQuery) -> Tuple[FilterOption, ...]:
        collection, field = query.collection, query.field
        require_access(actor, "read", collection)
        values = self._repository.record_filter_values(collection, field)
        if collection == "molds" and field == "patternId":
            patterns = self._repository.get_collection("patterns")
            options = [FilterOption(str(patterns.get(str(key), {}).get("code", key)), str(key))
                       for key in values]
            return tuple(sorted(options, key=lambda item: item.label.lower()))
        if field == "status" and collection != "purchases":
            active = any(str(value).lower() in ("active", "aktif") for value in values)
            inactive = any(str(value).lower() not in ("active", "aktif") for value in values)
            options = []
            if active:
                options.append(FilterOption("Aktif", "active"))
            if inactive:
                options.append(FilterOption("Nonaktif", "inactive"))
            return tuple(options)
        return tuple(FilterOption(str(value), str(value)) for value in values)

    def catalog_export(self, actor: Actor, query: CatalogExportQuery) -> CatalogExportResult:
        collection = query.collection
        require_access(actor, "read", collection)
        unique_field = {"molds": "spec", "containers": "code", "patterns": "code",
                        "stickers": "name", "projects": "spec", "purchases": "spec"}.get(collection)
        if not unique_field:
            raise ValidationError("Koleksi ini tidak diekspor melalui katalog.")
        stats = self._repository.record_stats(collection, unique_field, query.search, query.filters)
        rows = {}
        batch_size = 500
        for offset in range(0, stats["total"], batch_size):
            rows.update(self._repository.list_records_page(collection, offset, batch_size,
                                                           query.search, query.filters))
        lookups = self._repository.get_collections(("patterns", "containers")) if collection == "molds" else {}
        return CatalogExportResult(rows, lookups)

    def published_catalog(self, query: SnapshotReadRequest) -> CatalogResult:
        if self._snapshot_reader is None:
            raise ValidationError("Pembaca snapshot belum disiapkan.")
        payload = self._snapshot_reader.read(query.path)
        return CatalogResult(
            int(payload.get("schemaVersion", 2)), int(payload.get("revision", 0)),
            str(payload.get("updatedAt", "")), payload.get("collections", {}),
            tuple(payload.get("events", ())), tuple(payload.get("deleted", ())))

    def save_record(self, request: RecordSaveRequest) -> SaveResult:
        actor, collection, key, value, action, reason = (
            request.actor, request.collection, request.key, request.value,
            request.action, request.reason)
        require_access(actor, action, collection)
        value = validate_record(collection, key, value, action)
        public = collection in PUBLIC_COLLECTIONS
        self._repository.save_record(collection, key, value, actor.username, actor.computer,
                                     action, reason, public)
        return self._publish_after_commit(public)

    def save_records(self, request: RecordBatchSaveRequest) -> SaveResult:
        actor, collection, items, action = request.actor, request.collection, request.items, request.action
        require_access(actor, action, collection)
        validated_items = tuple(
            (key, validate_record(collection, key, value, action))
            for key, value in items)
        public = collection in PUBLIC_COLLECTIONS
        self._repository.save_records(collection, validated_items, actor.username,
                                      actor.computer, action, public)
        return self._publish_after_commit(public)

    def delete_record(self, request: RecordDeleteRequest) -> SaveResult:
        actor, collection, key, reason = request.actor, request.collection, request.key, request.reason
        require_access(actor, "delete", collection)
        public = collection in PUBLIC_COLLECTIONS
        self._repository.delete_record(collection, key, actor.username, actor.computer, reason, public)
        return self._publish_after_commit(public)

    def publish_pending(self, force: bool = False) -> bool:
        if not self._publish_path:
            return False
        required_revision = self._repository.pending_publish_revision()
        if not force and required_revision <= 0:
            return False
        collections = self._repository.get_collections(PUBLIC_COLLECTIONS)
        metadata = self._repository.catalog_metadata()
        snapshot = PublicSnapshot(2, metadata["revision"], metadata["updated_at"], collections)
        try:
            self._repository.mark_publish_required(snapshot.revision)
            self._publisher.publish(snapshot, self._publish_path)
            self._repository.mark_published(snapshot.revision)
            return True
        except Exception as exc:
            raise PublishError("Data tersimpan, tetapi publikasi SALAK belum berhasil.") from exc

    def set_publish_path(self, path: str) -> None:
        self._publish_path = str(path or "")

    def close(self) -> None:
        self._repository.close()

    def _publish_after_commit(self, public: bool) -> SaveResult:
        if not public or not self._publish_path:
            return SaveResult(self._repository.catalog_metadata()["revision"], False)
        try:
            self.publish_pending()
            return SaveResult(self._repository.catalog_metadata()["revision"], False)
        except PublishError:
            return SaveResult(self._repository.catalog_metadata()["revision"], True)

