"""A failed SALAK publication must not undo a successful local location change."""
import unittest
import tempfile
from pathlib import Path

from app.adapters.sqlite_repository import SQLiteCatalogRepository
from app.application.dto import LocationUpdateRequest
from app.application.use_cases import DelimoldUseCases
from app.domain.models import Actor, AppConfig


class RelocatingRepository:
    def __init__(self):
        self.relocated_to = None
        self.required_revision = 0
        self.published_revision = None

    def relocate_database(self, path):
        self.relocated_to = path

    def pending_publish_revision(self):
        published = self.published_revision or 0
        return self.required_revision if self.required_revision > published else 0

    def mark_publish_required(self, revision):
        self.required_revision = max(self.required_revision, revision)

    def get_collections(self, collections):
        return {name: {} for name in collections}

    def catalog_metadata(self):
        return {"revision": 4, "updated_at": "2026-11-01T00:00:00"}

    def mark_published(self, revision):
        self.published_revision = revision


class FailingPublisher:
    def publish(self, snapshot, destination):
        raise OSError("SALAK tidak tersedia")


class RecoveringPublisher:
    def __init__(self):
        self.attempts = 0

    def publish(self, snapshot, destination):
        self.attempts += 1
        if self.attempts == 1:
            raise OSError("SALAK tidak tersedia")


class RecordingConfigurationStore:
    def __init__(self):
        self.saved = []

    def save(self, config):
        self.saved.append(dict(config))


class LocationPublicationFailureTests(unittest.TestCase):
    def test_local_location_remains_saved_when_salak_publish_fails(self):
        repository = RelocatingRepository()
        configuration_store = RecordingConfigurationStore()
        use_cases = DelimoldUseCases(
            repository,
            FailingPublisher(),
            publish_path="old-share",
            configuration_store=configuration_store,
        )
        current = {"database_path": "old.sqlite3", "publish_path": "old-share"}
        updated = {"database_path": "new.sqlite3", "publish_path": "new-share"}

        result = use_cases.update_locations(LocationUpdateRequest(
            Actor("sup", "Supervisor", "SUPERVISOR"),
            AppConfig.from_mapping(current), AppConfig.from_mapping(updated)))

        self.assertTrue(result.publication_pending)
        self.assertIn("publikasi SALAK belum berhasil", result.message)
        self.assertEqual([AppConfig.from_mapping(updated).as_dict()], configuration_store.saved)
        self.assertEqual("new.sqlite3", repository.relocated_to)
        self.assertEqual("new-share", use_cases.catalogs._publish_path)
        self.assertEqual(4, repository.required_revision)
        self.assertIsNone(repository.published_revision)

    def test_pending_publication_succeeds_on_a_later_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            repository = SQLiteCatalogRepository(root / "old.sqlite3")
            publisher = RecoveringPublisher()
            use_cases = DelimoldUseCases(
                repository,
                publisher,
                publish_path="share",
                configuration_store=RecordingConfigurationStore(),
            )
            try:
                result = use_cases.update_locations(LocationUpdateRequest(
                    Actor("sup", "Supervisor", "SUPERVISOR"),
                    AppConfig.from_mapping({"mode": "master", "database_path": str(root / "old.sqlite3"),
                                            "publish_path": "old-share"}),
                    AppConfig.from_mapping({"mode": "master", "database_path": str(root / "new.sqlite3"),
                                            "publish_path": "share"})))
                self.assertTrue(result.publication_pending)
                self.assertGreater(repository.pending_publish_revision(), 0)

                self.assertTrue(use_cases.publish_pending())
                self.assertEqual(0, repository.pending_publish_revision())
                self.assertEqual(2, publisher.attempts)
            finally:
                repository.close()


if __name__ == "__main__":
    unittest.main()
