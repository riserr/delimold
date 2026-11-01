"""Authorization checks for changing TENDERLOIN and SALAK locations."""
import unittest

from app.application.dto import LocationUpdateRequest
from app.application.use_cases import DelimoldUseCases
from app.domain.errors import PermissionDenied
from app.domain.models import Actor, AppConfig


class RecordingRepository:
    def __init__(self):
        self.relocated_to = None

    def relocate_database(self, path):
        self.relocated_to = path


class RecordingConfigurationStore:
    def __init__(self):
        self.saved = []

    def save(self, config):
        self.saved.append(dict(config))


class LocationPermissionTests(unittest.TestCase):
    def setUp(self):
        self.repository = RecordingRepository()
        self.config_store = RecordingConfigurationStore()
        self.use_cases = DelimoldUseCases(
            self.repository,
            publisher=object(),
            configuration_store=self.config_store,
        )
        self.current = {"mode": "master", "database_path": "old.sqlite3", "publish_path": ""}
        self.updated = {"mode": "master", "database_path": "new.sqlite3", "publish_path": ""}

    def test_engineer_cannot_change_application_locations(self):
        engineer = Actor("eng", "Engineer", "ENGINEER")

        with self.assertRaises(PermissionDenied):
            self.use_cases.update_locations(LocationUpdateRequest(
                engineer, AppConfig.from_mapping(self.current), AppConfig.from_mapping(self.updated)))

        self.assertEqual([], self.config_store.saved)
        self.assertIsNone(self.repository.relocated_to)

    def test_supervisor_can_change_application_locations(self):
        supervisor = Actor("sup", "Supervisor", "SUPERVISOR")

        result = self.use_cases.update_locations(LocationUpdateRequest(
            supervisor, AppConfig.from_mapping(self.current), AppConfig.from_mapping(self.updated)))

        self.assertFalse(result.publication_pending)
        self.assertEqual([AppConfig.from_mapping(self.updated).as_dict()], self.config_store.saved)
        self.assertEqual("new.sqlite3", self.repository.relocated_to)


if __name__ == "__main__":
    unittest.main()
