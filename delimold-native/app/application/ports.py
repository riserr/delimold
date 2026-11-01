"""Outbound contracts owned by the application layer."""
from abc import ABC, abstractmethod


class CatalogRepository(ABC):
    @abstractmethod
    def close(self): ...

    @abstractmethod
    def relocate_database(self, target_path): ...

    @abstractmethod
    def is_empty(self): ...

    @abstractmethod
    def user_count(self): ...

    @abstractmethod
    def get_collection(self, collection): ...

    @abstractmethod
    def get_collections(self, collections): ...

    @abstractmethod
    def list_records_page(self, collection, offset, limit, search="", filters=None): ...

    @abstractmethod
    def record_stats(self, collection, unique_field, search="", filters=None): ...

    @abstractmethod
    def record_filter_values(self, collection, field): ...

    @abstractmethod
    def catalog_metadata(self): ...

    @abstractmethod
    def save_record(self, collection, key, value, actor, computer, action, reason, publish_required): ...

    @abstractmethod
    def save_records(self, collection, items, actor, computer, action, publish_required): ...

    @abstractmethod
    def delete_record(self, collection, key, actor, computer, reason, publish_required): ...

    @abstractmethod
    def pending_publish_revision(self): ...

    @abstractmethod
    def mark_publish_required(self, revision): ...

    @abstractmethod
    def mark_published(self, revision): ...

    @abstractmethod
    def audit_rows(self, limit=200): ...

    @abstractmethod
    def list_users(self): ...

    @abstractmethod
    def get_user_credentials(self, username): ...

    @abstractmethod
    def create_user(self, username, display_name, role, salt, password_hash): ...

    @abstractmethod
    def update_user(self, username, display_name, role, enabled=None, salt=None, password_hash=None): ...

    @abstractmethod
    def delete_user(self, username): ...

    @abstractmethod
    def enabled_supervisor_count(self): ...

    @abstractmethod
    def import_catalog(self, catalog, publish_required=False): ...


class ConfigurationStore(ABC):
    """Outbound port for persisting user-selected application settings."""
    @abstractmethod
    def save(self, config): ...


class SnapshotPublisher(ABC):
    @abstractmethod
    def publish(self, snapshot, destination): ...


class SnapshotReader(ABC):
    @abstractmethod
    def read(self, path): ...


class SeedCatalogReader(ABC):
    """Reads the immutable starter catalog from its packaged representation."""
    @abstractmethod
    def read(self, path): ...


class WorkbookPort(ABC):
    @abstractmethod
    def read_rows(self, path): ...

    @abstractmethod
    def write_workbook(self, path, sheet_name, headings, rows): ...

    @abstractmethod
    def write_template(self, path, sheet_name, headings): ...


class PdfExporterPort(ABC):
    @abstractmethod
    def write_pdf(self, path, title, headings, rows): ...
