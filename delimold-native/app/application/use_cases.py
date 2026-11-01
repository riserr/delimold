"""Application service composition and stable facade for UI workflows."""
from typing import Any, Dict, List, Optional, Tuple

from app.application.account_use_cases import AccountUseCases
from app.application.catalog_use_cases import CatalogUseCases
from app.application.dto import (AuditEntry, AuditQuery, AuthenticationRequest, CatalogExportQuery,
                                 CatalogExportResult, CatalogPageQuery, CatalogPageResult,
                                 CatalogResult, ExcelExportRequest, FilterOption,
                                 FilterOptionsQuery, InitialSupervisorRequest,
                                 LocationUpdateRequest, LocationUpdateResult, PdfExportRequest,
                                 RecordBatchSaveRequest, RecordDeleteRequest, RecordSaveRequest,
                                 SnapshotReadRequest, UserDeleteRequest, UserEnabledRequest,
                                 UserSaveRequest, UserSummary, WorkbookReadRequest,
                                 WorkbookTemplateRequest)
from app.application.location_use_cases import LocationUseCases
from app.application.ports import (CatalogRepository, ConfigurationStore, PdfExporterPort,
                                   SeedCatalogReader, SnapshotPublisher, SnapshotReader,
                                   WorkbookPort)
from app.application.transfer_use_cases import TransferUseCases
from app.domain.models import Actor, SaveResult


class DelimoldUseCases:
    """Thin application facade delegating to focused workflow services."""
    def __init__(self, repository: Optional[CatalogRepository], publisher: SnapshotPublisher,
                 snapshot_reader: Optional[SnapshotReader] = None, publish_path: str = "",
                 workbook: Optional[WorkbookPort] = None,
                 pdf_exporter: Optional[PdfExporterPort] = None,
                 seed_reader: Optional[SeedCatalogReader] = None,
                 configuration_store: Optional[ConfigurationStore] = None):
        self.accounts = AccountUseCases(repository)
        self.catalogs = CatalogUseCases(repository, publisher, snapshot_reader, publish_path, seed_reader)
        self.transfers = TransferUseCases(workbook, pdf_exporter)
        self.locations = LocationUseCases(repository, configuration_store, self.catalogs)

    def initialize_catalog_if_empty(self, seed_path: str) -> bool:
        return self.catalogs.initialize_catalog_if_empty(seed_path)

    def read_excel_rows(self, request: WorkbookReadRequest) -> List[Tuple[Any, ...]]:
        return self.transfers.read_excel_rows(request)

    def write_excel_template(self, request: WorkbookTemplateRequest) -> None:
        self.transfers.write_excel_template(request)

    def export_excel(self, request: ExcelExportRequest) -> None:
        self.transfers.export_excel(request)

    def print_pdf(self, request: PdfExportRequest) -> None:
        self.transfers.print_pdf(request)

    def needs_initial_setup(self) -> bool:
        return self.accounts.needs_initial_setup()

    def authenticate(self, request: AuthenticationRequest) -> Actor:
        return self.accounts.authenticate(request)

    def setup_initial_supervisor(self, request: InitialSupervisorRequest) -> None:
        self.accounts.setup_initial_supervisor(request)

    def save_user(self, request: UserSaveRequest) -> None:
        self.accounts.save_user(request)

    def set_user_enabled(self, request: UserEnabledRequest) -> None:
        self.accounts.set_user_enabled(request)

    def user_count(self) -> int:
        return self.accounts.user_count()

    def delete_user(self, request: UserDeleteRequest) -> None:
        self.accounts.delete_user(request)

    def list_users(self, actor: Actor) -> Dict[str, UserSummary]:
        return self.accounts.list_users(actor)

    def audit_rows(self, actor: Actor, query: AuditQuery = AuditQuery()) -> Tuple[AuditEntry, ...]:
        return self.accounts.audit_rows(actor, query)

    def catalog(self, actor: Actor) -> CatalogResult:
        return self.catalogs.catalog(actor)

    def catalog_page(self, actor: Actor, query: CatalogPageQuery) -> CatalogPageResult:
        return self.catalogs.catalog_page(actor, query)

    def filter_options(self, actor: Actor, query: FilterOptionsQuery) -> Tuple[FilterOption, ...]:
        return self.catalogs.filter_options(actor, query)

    def catalog_export(self, actor: Actor, query: CatalogExportQuery) -> CatalogExportResult:
        return self.catalogs.catalog_export(actor, query)

    def published_catalog(self, query: SnapshotReadRequest) -> CatalogResult:
        return self.catalogs.published_catalog(query)

    def save_record(self, request: RecordSaveRequest) -> SaveResult:
        return self.catalogs.save_record(request)

    def save_records(self, request: RecordBatchSaveRequest) -> SaveResult:
        return self.catalogs.save_records(request)

    def delete_record(self, request: RecordDeleteRequest) -> SaveResult:
        return self.catalogs.delete_record(request)

    def publish_pending(self, force: bool = False) -> bool:
        return self.catalogs.publish_pending(force)

    def close(self) -> None:
        self.catalogs.close()

    def update_locations(self, request: LocationUpdateRequest) -> LocationUpdateResult:
        return self.locations.update_locations(request)

    def set_publish_path(self, path: str) -> None:
        self.catalogs.set_publish_path(path)
