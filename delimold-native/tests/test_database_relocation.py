"""Integration checks for safe SQLite database relocation."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.adapters.sqlite_repository import SQLiteCatalogRepository
from app.domain.errors import StorageError


class DatabaseRelocationTests(unittest.TestCase):
    def test_relocation_copies_data_and_switches_live_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "old" / "delimold.sqlite3"
            target = root / "new" / "delimold.sqlite3"
            repository = SQLiteCatalogRepository(source)
            try:
                repository.connection.execute(
                    "INSERT INTO records(collection, record_key, payload) VALUES (?, ?, ?)",
                    ("molds", "MD-001", '{"spec":"MD-001"}'),
                )
                repository.connection.commit()

                repository.relocate_database(target)

                self.assertEqual(target.resolve(), repository.path.resolve())
                self.assertTrue(source.is_file())  # relocation preserves the original copy
                row = repository.connection.execute(
                    "SELECT payload FROM records WHERE collection=? AND record_key=?",
                    ("molds", "MD-001"),
                ).fetchone()
                self.assertEqual('{"spec":"MD-001"}', row["payload"])
            finally:
                repository.close()

            reopened = SQLiteCatalogRepository(target)
            try:
                row = reopened.connection.execute(
                    "SELECT payload FROM records WHERE collection=? AND record_key=?",
                    ("molds", "MD-001"),
                ).fetchone()
                self.assertEqual('{"spec":"MD-001"}', row["payload"])
            finally:
                reopened.close()

    def test_existing_target_is_not_overwritten_or_selected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "old.sqlite3"
            target = root / "existing.sqlite3"
            repository = SQLiteCatalogRepository(source)
            try:
                repository.connection.execute(
                    "INSERT INTO records(collection, record_key, payload) VALUES (?, ?, ?)",
                    ("molds", "MD-002", '{"spec":"MD-002"}'),
                )
                repository.connection.commit()
                original_target = sqlite3.connect(str(target))
                original_target.execute("CREATE TABLE keep_me (value TEXT)")
                original_target.execute("INSERT INTO keep_me(value) VALUES ('preserve')")
                original_target.commit()
                original_target.close()
                before = target.read_bytes()

                with self.assertRaises(StorageError):
                    repository.relocate_database(target)

                self.assertEqual(source.resolve(), repository.path.resolve())
                self.assertEqual(before, target.read_bytes())
            finally:
                repository.close()


if __name__ == "__main__":
    unittest.main()
