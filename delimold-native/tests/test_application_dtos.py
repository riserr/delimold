"""Contract tests for typed UI-to-use-case request and response DTOs."""
import tempfile
import unittest
from pathlib import Path

from app.adapters.sqlite_repository import SQLiteCatalogRepository
from app.application.account_use_cases import AccountUseCases
from app.application.catalog_use_cases import CatalogUseCases
from app.application.dto import (CatalogExportQuery, CatalogExportResult, CatalogPageQuery,
                                 CatalogPageResult, CatalogResult, FilterOption,
                                 FilterOptionsQuery, InitialSupervisorRequest,
                                 RecordSaveRequest, SnapshotReadRequest, UserSummary)
from app.application.location_use_cases import LocationUseCases
from app.application.transfer_use_cases import TransferUseCases
from app.application.use_cases import DelimoldUseCases
from app.domain.models import Actor


class ApplicationDtoTests(unittest.TestCase):
    def test_facade_composes_focused_workflow_services(self):
        use_cases = DelimoldUseCases(None, publisher=object())
        self.assertIsInstance(use_cases.accounts, AccountUseCases)
        self.assertIsInstance(use_cases.catalogs, CatalogUseCases)
        self.assertIsInstance(use_cases.transfers, TransferUseCases)
        self.assertIsInstance(use_cases.locations, LocationUseCases)

    def test_catalog_use_cases_return_typed_results_and_options(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteCatalogRepository(Path(directory) / "catalog.sqlite3")
            use_cases = DelimoldUseCases(repository, publisher=object())
            actor = Actor("supervisor", "Supervisor", "SUPERVISOR")
            try:
                catalog = use_cases.catalog(actor)
                use_cases.save_record(RecordSaveRequest(
                    actor, "molds", "MD-1", {"spec": "MD-1", "size": "245/45R18",
                                                "patternId": "KU-1", "serial": "01",
                                                "cure": "press"}, "create"))
                page = use_cases.catalog_page(actor, CatalogPageQuery("molds", 0, 20))
                exported = use_cases.catalog_export(actor, CatalogExportQuery("molds"))
                options = use_cases.filter_options(actor, FilterOptionsQuery("molds", "status"))

                self.assertIsInstance(catalog, CatalogResult)
                self.assertIsInstance(page, CatalogPageResult)
                self.assertIsInstance(exported, CatalogExportResult)
                self.assertTrue(all(isinstance(option, FilterOption) for option in options))
                self.assertEqual({}, catalog.collections["molds"])
                self.assertEqual("MD-1", page.rows["MD-1"]["spec"])
                self.assertEqual("MD-1", exported.rows["MD-1"]["spec"])
            finally:
                repository.close()

    def test_account_requests_and_responses_use_dtos(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteCatalogRepository(Path(directory) / "accounts.sqlite3")
            use_cases = DelimoldUseCases(repository, publisher=object())
            try:
                use_cases.setup_initial_supervisor(
                    InitialSupervisorRequest("sup", "Supervisor", "1234"))
                users = use_cases.list_users(Actor("sup", "Supervisor", "SUPERVISOR"))
                self.assertIsInstance(users["sup"], UserSummary)
                self.assertEqual("SUPERVISOR", users["sup"].role)
            finally:
                repository.close()

    def test_snapshot_read_is_converted_to_catalog_result(self):
        class SnapshotReader:
            def read(self, path):
                return {"schemaVersion": 2, "revision": 8, "updatedAt": "now",
                        "collections": {"molds": {"MD-8": {"spec": "MD-8"}}},
                        "events": [], "deleted": []}

        use_cases = DelimoldUseCases(None, publisher=object(), snapshot_reader=SnapshotReader())
        result = use_cases.published_catalog(SnapshotReadRequest("catalog.json"))
        self.assertIsInstance(result, CatalogResult)
        self.assertEqual(8, result.revision)
        self.assertEqual("MD-8", result.collections["molds"]["MD-8"]["spec"])


if __name__ == "__main__":
    unittest.main()
