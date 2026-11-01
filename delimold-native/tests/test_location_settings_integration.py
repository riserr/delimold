"""Exercise configuration save, SQLite relocation, and snapshot publish together."""
import json
import os
import tempfile
import unittest
from pathlib import Path

from app.adapters.configuration import JsonConfigurationStore
from app.adapters.salak_publisher import JsonSnapshotPublisher, JsonSnapshotReader
from app.adapters.sqlite_repository import SQLiteCatalogRepository
from app.application.dto import LocationUpdateRequest
from app.application.use_cases import DelimoldUseCases
from app.domain.models import Actor, AppConfig


class LocationSettingsIntegrationTests(unittest.TestCase):
    def test_configuration_database_and_publication_complete_as_one_flow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            application_dir = root / "TENDERLOIN" / "APLIKASI"
            old_database = root / "previous" / "delimold.sqlite3"
            new_database = root / "TENDERLOIN" / "DATABASE" / "delimold.sqlite3"
            salak_folder = root / "salak-share" / "published-python"
            local_appdata = root / "profile"
            application_dir.mkdir(parents=True)
            previous_local = os.environ.get("LOCALAPPDATA")
            os.environ["LOCALAPPDATA"] = str(local_appdata)
            repository = SQLiteCatalogRepository(old_database)
            try:
                repository.connection.execute(
                    "INSERT INTO records(collection, record_key, payload) VALUES (?, ?, ?)",
                    ("molds", "MD-003", '{"spec":"MD-003","status":"active"}'),
                )
                repository.connection.commit()
                use_cases = DelimoldUseCases(
                    repository,
                    JsonSnapshotPublisher(),
                    JsonSnapshotReader(),
                    publish_path=str(root / "old-share"),
                    configuration_store=JsonConfigurationStore(application_dir),
                )
                current = {"mode": "master", "database_path": str(old_database),
                           "publish_path": str(root / "old-share")}
                updated = {"mode": "master", "database_path": str(new_database),
                           "publish_path": str(salak_folder)}

                result = use_cases.update_locations(LocationUpdateRequest(
                    Actor("sup", "Supervisor", "SUPERVISOR"),
                    AppConfig.from_mapping(current), AppConfig.from_mapping(updated)))

                self.assertFalse(result.publication_pending)
                self.assertEqual(new_database.resolve(), repository.path.resolve())
                self.assertTrue(old_database.is_file())
                self.assertEqual(0, repository.pending_publish_revision())
                snapshot = JsonSnapshotReader().read(salak_folder / "catalog.json")
                self.assertEqual("MD-003", snapshot["collections"]["molds"]["MD-003"]["spec"])
                stored_config = json.loads(
                    (local_appdata / "DELIMOLD" / "config.json").read_text(encoding="utf-8"))
                self.assertEqual("../DATABASE/delimold.sqlite3", stored_config["database_path"])
                self.assertEqual(str(salak_folder), stored_config["publish_path"])
            finally:
                repository.close()
                if previous_local is None:
                    os.environ.pop("LOCALAPPDATA", None)
                else:
                    os.environ["LOCALAPPDATA"] = previous_local


if __name__ == "__main__":
    unittest.main()
