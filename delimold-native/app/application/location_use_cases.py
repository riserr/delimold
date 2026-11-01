"""Supervisor-only configuration and database relocation workflow."""
from app.application.dto import LocationUpdateRequest, LocationUpdateResult
from app.application.catalog_use_cases import CatalogUseCases
from app.application.ports import CatalogRepository, ConfigurationStore
from app.domain.errors import PublishError, ValidationError
from app.domain.permissions import can_manage_accounts


class LocationUseCases:
    def __init__(self, repository: CatalogRepository, configuration_store: ConfigurationStore,
                 catalog_use_cases: CatalogUseCases):
        self._repository = repository
        self._configuration_store = configuration_store
        self._catalog_use_cases = catalog_use_cases

    def update_locations(self, request: LocationUpdateRequest) -> LocationUpdateResult:
        can_manage_accounts(request.actor)
        if self._configuration_store is None:
            raise ValidationError("Penyimpanan konfigurasi belum disiapkan.")
        if self._repository is None:
            raise ValidationError("Mode ini tidak menggunakan database utama.")
        self._configuration_store.save(request.updated_config.as_dict())
        try:
            self._repository.relocate_database(request.updated_config.database_path)
        except Exception:
            try:
                self._configuration_store.save(request.current_config.as_dict())
            except Exception as restore_error:
                raise ValidationError(
                    "Database gagal dipindahkan dan konfigurasi lama gagal dipulihkan: %s"
                    % restore_error
                )
            raise
        self._catalog_use_cases.set_publish_path(request.updated_config.publish_path)
        try:
            self._catalog_use_cases.publish_pending(force=True)
            return LocationUpdateResult()
        except PublishError as exc:
            return LocationUpdateResult(True, str(exc))
