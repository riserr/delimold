"""Application use cases; dependencies are expressed only as ports."""
import base64
import hashlib
import hmac
import os
from typing import Optional

from app.application.ports import (CatalogRepository, PdfExporterPort, SnapshotPublisher,
                                   SeedCatalogReader, SnapshotReader, WorkbookPort)
from app.domain.errors import AuthenticationFailed, DataNotFound, PublishError, ValidationError
from app.domain.models import Actor, PublicSnapshot, SaveResult
from app.domain.permissions import PUBLIC_COLLECTIONS, SUPERVISOR_COLLECTIONS, can_manage_accounts, require_access


class DelimoldUseCases:
    def __init__(self, repository: Optional[CatalogRepository], publisher: SnapshotPublisher,
                 snapshot_reader: Optional[SnapshotReader] = None, publish_path: str = "",
                 workbook: Optional[WorkbookPort] = None,
                 pdf_exporter: Optional[PdfExporterPort] = None,
                 seed_reader: Optional[SeedCatalogReader] = None):
        self._repository = repository
        self._publisher = publisher
        self._snapshot_reader = snapshot_reader
        self._publish_path = publish_path
        self._workbook = workbook
        self._pdf_exporter = pdf_exporter
        self._seed_reader = seed_reader

    def initialize_catalog_if_empty(self, seed_path):
        """Import the packaged catalog only when the local repository is empty."""
        if self._repository is None:
            raise ValidationError("Database utama belum disiapkan.")
        if not self._repository.is_empty():
            return False
        if self._seed_reader is None:
            raise ValidationError("Pembaca katalog awal belum disiapkan.")
        self._repository.import_catalog(self._seed_reader.read(seed_path), publish_required=True)
        return True

    def read_excel_rows(self, actor, collection, path):
        require_access(actor, "import", collection)
        if self._workbook is None:
            raise ValidationError("Adapter Excel belum disiapkan.")
        return self._workbook.read_rows(path)

    def write_excel_template(self, actor, collection, path, headings):
        require_access(actor, "read", collection)
        if self._workbook is None:
            raise ValidationError("Adapter Excel belum disiapkan.")
        self._workbook.write_template(path, collection, headings)

    def export_excel(self, actor, collection, path, headings, rows):
        require_access(actor, "read", collection)
        if self._workbook is None:
            raise ValidationError("Adapter Excel belum disiapkan.")
        self._workbook.write_workbook(path, collection, headings, rows)

    def print_pdf(self, actor, collection, path, title, headings, rows):
        require_access(actor, "read", collection)
        if self._pdf_exporter is None:
            raise ValidationError("Adapter PDF belum disiapkan.")
        self._pdf_exporter.write_pdf(path, title, headings, rows)

    def needs_initial_setup(self):
        return self._repository.user_count() == 0

    def authenticate(self, username, password, computer=""):
        credential = self._repository.get_user_credentials(username.strip())
        if not credential:
            raise AuthenticationFailed("Nama akun atau password salah.")
        salt = base64.b64decode(credential["salt"])
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        if not hmac.compare_digest(base64.b64encode(digest).decode("ascii"), credential["password_hash"]):
            raise AuthenticationFailed("Nama akun atau password salah.")
        return Actor(credential["username"], credential["display_name"], credential["role"], computer)

    def setup_initial_supervisor(self, username, display_name, password):
        username = username.strip()
        self._validate_user(username, display_name, "SUPERVISOR", password, required=True)
        if self._repository.user_count():
            raise ValidationError("Supervisor awal sudah dibuat.")
        salt, password_hash = self._hash_password(password)
        self._repository.create_user(username, display_name.strip() or username, "SUPERVISOR", salt, password_hash)

    def save_user(self, actor, username, display_name, role, password="", enabled=True, existing=False):
        can_manage_accounts(actor)
        username = username.strip()
        self._validate_user(username, display_name, role, password, required=not existing)
        if not existing:
            if not password:
                raise ValidationError("Password wajib diisi untuk akun baru.")
            salt, password_hash = self._hash_password(password)
            self._repository.create_user(username, display_name.strip() or username, role, salt, password_hash)
            return
        if password:
            salt, password_hash = self._hash_password(password)
            self._repository.update_user(username, display_name.strip() or username, role,
                                         enabled=enabled, salt=salt, password_hash=password_hash)
        else:
            self._repository.update_user(username, display_name.strip() or username, role, enabled=enabled)

    def set_user_enabled(self, actor, username, enabled):
        can_manage_accounts(actor)
        target = self._repository.list_users().get(username)
        if not target:
            raise DataNotFound("Akun tidak ditemukan.")
        if target.get("role") == "SUPERVISOR" and target.get("enabled") and not enabled:
            if self._repository.enabled_supervisor_count() <= 1:
                raise ValidationError("Supervisor aktif terakhir tidak dapat dinonaktifkan.")
        self._repository.update_user(username, target.get("display_name", username),
                                     target.get("role", "ENGINEER"), enabled=enabled)

    def user_count(self):
        return self._repository.user_count()

    def delete_user(self, actor, username):
        can_manage_accounts(actor)
        if username == actor.username:
            raise ValidationError("Akun yang sedang dipakai tidak dapat dihapus.")
        target = self._repository.list_users().get(username)
        if not target:
            raise DataNotFound("Akun tidak ditemukan.")
        if target.get("role") == "SUPERVISOR" and target.get("enabled") and self._repository.enabled_supervisor_count() <= 1:
            raise ValidationError("Supervisor aktif terakhir tidak dapat dihapus.")
        self._repository.delete_user(username)

    def list_users(self, actor):
        can_manage_accounts(actor)
        return self._repository.list_users()

    def audit_rows(self, actor, limit=200):
        require_access(actor, "read", "history")
        return self._repository.audit_rows(limit)

    def catalog(self, actor):
        allowed = SUPERVISOR_COLLECTIONS if actor.role == "SUPERVISOR" else tuple(
            name for name in SUPERVISOR_COLLECTIONS if name in PUBLIC_COLLECTIONS or
            (actor.role == "ENGINEER" and name == "projects"))
        collections = self._repository.get_collections(allowed)
        metadata = self._repository.catalog_metadata()
        return {"schemaVersion": 2, "revision": metadata["revision"],
                "updatedAt": metadata["updated_at"], "collections": collections,
                "events": [], "deleted": []}

    def catalog_page(self, actor, collection, offset, limit, search="", filters=None):
        require_access(actor, "read", collection)
        if collection in ("accounts", "history", "pattern_art"):
            raise ValidationError("Koleksi ini belum mendukung halaman katalog.")
        unique_fields = {"molds": "spec", "containers": "code", "patterns": "code",
                         "stickers": "name", "projects": "spec", "purchases": "spec"}
        unique_field = unique_fields.get(collection)
        if not unique_field:
            raise ValidationError("Koleksi tidak dikenal.")
        rows = self._repository.list_records_page(collection, offset, limit, search, filters)
        stats = self._repository.record_stats(collection, unique_field, search, filters)
        lookups = {}
        if collection == "molds":
            lookups = self._repository.get_collections(("patterns", "containers"))
        return {"collection": collection, "rows": rows, "stats": stats, "lookups": lookups}

    def filter_options(self, actor, collection, field):
        require_access(actor, "read", collection)
        values = self._repository.record_filter_values(collection, field)
        if collection == "molds" and field == "patternId":
            patterns = self._repository.get_collection("patterns")
            options = []
            for pattern_id in values:
                pattern = patterns.get(str(pattern_id), {})
                options.append((str(pattern.get("code", pattern_id)), str(pattern_id)))
            return sorted(options, key=lambda item: item[0].lower())
        if field == "status" and collection != "purchases":
            active = any(str(value).lower() in ("active", "aktif") for value in values)
            inactive = any(str(value).lower() not in ("active", "aktif") for value in values)
            options = []
            if active:
                options.append(("Aktif", "active"))
            if inactive:
                options.append(("Nonaktif", "inactive"))
            return options
        return [(str(value), str(value)) for value in values]

    def catalog_export(self, actor, collection, search="", filters=None):
        require_access(actor, "read", collection)
        unique_field = {"molds": "spec", "containers": "code", "patterns": "code",
                        "stickers": "name", "projects": "spec", "purchases": "spec"}.get(collection)
        if not unique_field:
            raise ValidationError("Koleksi ini tidak diekspor melalui katalog.")
        stats = self._repository.record_stats(collection, unique_field, search, filters)
        rows = {}
        batch_size = 500
        for offset in range(0, stats["total"], batch_size):
            rows.update(self._repository.list_records_page(collection, offset, batch_size, search, filters))
        lookups = self._repository.get_collections(("patterns", "containers")) if collection == "molds" else {}
        return {"rows": rows, "lookups": lookups}

    def published_catalog(self, path):
        if self._snapshot_reader is None:
            raise ValidationError("Pembaca snapshot belum disiapkan.")
        return self._snapshot_reader.read(path)

    def save_record(self, actor, collection, key, value, action="save", reason=""):
        require_access(actor, action, collection)
        self._validate_record(collection, key, value, action)
        public = collection in PUBLIC_COLLECTIONS
        self._repository.save_record(collection, key, value, actor.username, actor.computer, action, reason, public)
        return self._publish_after_commit(public)

    def save_records(self, actor, collection, items, action="import"):
        require_access(actor, action, collection)
        for key, value in items:
            self._validate_record(collection, key, value, action)
        public = collection in PUBLIC_COLLECTIONS
        self._repository.save_records(collection, items, actor.username, actor.computer, action, public)
        return self._publish_after_commit(public)

    def delete_record(self, actor, collection, key, reason=""):
        require_access(actor, "delete", collection)
        public = collection in PUBLIC_COLLECTIONS
        self._repository.delete_record(collection, key, actor.username, actor.computer, reason, public)
        return self._publish_after_commit(public)

    def publish_pending(self, force=False):
        if not self._publish_path:
            return False
        required_revision = self._repository.pending_publish_revision()
        if not force and required_revision <= 0:
            return False
        selected = PUBLIC_COLLECTIONS
        collections = self._repository.get_collections(selected)
        metadata = self._repository.catalog_metadata()
        snapshot = PublicSnapshot(2, metadata["revision"], metadata["updated_at"], collections)
        try:
            self._publisher.publish(snapshot, self._publish_path)
            self._repository.mark_published(snapshot.revision)
            return True
        except Exception as exc:
            raise PublishError("Data tersimpan, tetapi publikasi SALAK belum berhasil.") from exc

    def close(self):
        self._repository.close()

    def set_publish_path(self, path):
        self._publish_path = str(path or "")

    def _publish_after_commit(self, public):
        if not public or not self._publish_path:
            return SaveResult(self._repository.catalog_metadata()["revision"], False)
        try:
            self.publish_pending()
            return SaveResult(self._repository.catalog_metadata()["revision"], False)
        except PublishError:
            return SaveResult(self._repository.catalog_metadata()["revision"], True)

    @staticmethod
    def _validate_record(collection, key, value, action):
        if not collection or not str(key).strip() or not isinstance(value, dict):
            raise ValidationError("Data tidak lengkap atau formatnya tidak valid.")
        if action == "status" and not str(value.get("statusReason", "")).strip():
            raise ValidationError("Alasan perubahan status wajib diisi.")

    @staticmethod
    def _validate_user(username, display_name, role, password, required):
        if not username or role not in ("SUPERVISOR", "ENGINEER", "VIEWER"):
            raise ValidationError("Nama akun atau peran tidak valid.")
        if required and not (4 <= len(password) <= 12):
            raise ValidationError("Password harus 4–12 karakter.")
        if password and not (4 <= len(password) <= 12):
            raise ValidationError("Password harus 4–12 karakter.")

    @staticmethod
    def _hash_password(password):
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return base64.b64encode(salt).decode("ascii"), base64.b64encode(digest).decode("ascii")
