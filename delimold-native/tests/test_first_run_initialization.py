"""Verify fresh installation creates schema, then account, then starter data."""
import tempfile
import unittest
from pathlib import Path

from app.adapters.seed_catalog_reader import JsonSeedCatalogReader
from app.adapters.sqlite_repository import SQLiteCatalogRepository
from app.application.dto import InitialSupervisorRequest
from app.application.use_cases import DelimoldUseCases


class FirstRunInitializationTests(unittest.TestCase):
    def test_new_database_prompts_for_supervisor_before_seed_catalog_load(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "DATABASE" / "delimold.sqlite3"
            repository = SQLiteCatalogRepository(database)
            use_cases = DelimoldUseCases(
                repository, publisher=object(), seed_reader=JsonSeedCatalogReader())
            seed = Path(__file__).resolve().parents[1] / "app" / "data" / "seed" / "catalog.json"
            try:
                self.assertTrue(database.is_file())
                self.assertEqual(0, repository.user_count())
                self.assertTrue(repository.is_empty())
                self.assertTrue(use_cases.needs_initial_setup())

                use_cases.setup_initial_supervisor(
                    InitialSupervisorRequest("sup", "Supervisor", "1234"))

                self.assertFalse(use_cases.needs_initial_setup())
                self.assertTrue(use_cases.initialize_catalog_if_empty(str(seed)))
                self.assertEqual(1, repository.user_count())
                self.assertFalse(repository.is_empty())
            finally:
                use_cases.close()


if __name__ == "__main__":
    unittest.main()
