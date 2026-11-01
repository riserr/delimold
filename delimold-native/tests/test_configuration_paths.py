"""Keep application data paths centralized and portable across folder moves."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.adapters.configuration import (
    default_database_path,
    default_seed_path,
    load_config,
    package_root,
    resolve_seed_path,
    save_config,
)
from app.domain.errors import ConfigurationError


class ConfigurationPathTests(unittest.TestCase):
    def test_packaged_database_is_sibling_of_application_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            application = Path(directory) / "TENDERLOIN" / "APLIKASI"
            expected = Path(directory) / "TENDERLOIN" / "DATABASE" / "delimold.sqlite3"
            self.assertEqual(expected, default_database_path(application))
            self.assertEqual(application.parent, package_root(application))

    def test_source_tree_database_is_under_project_root(self):
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory) / "delimold-native"
            self.assertEqual(source_root / "DATABASE" / "delimold.sqlite3",
                             default_database_path(source_root))

    def test_missing_or_legacy_seed_uses_one_canonical_seed_path(self):
        with tempfile.TemporaryDirectory() as directory:
            application = Path(directory) / "APLIKASI"
            seed = default_seed_path(application)
            seed.parent.mkdir(parents=True)
            seed.write_text("{}", encoding="utf-8")
            self.assertEqual(seed, resolve_seed_path(application, "seed/catalog.json"))
            self.assertEqual(seed, resolve_seed_path(application, None))

    def test_saved_database_path_follows_package_when_root_moves(self):
        with tempfile.TemporaryDirectory() as directory:
            old_root = Path(directory) / "old" / "TENDERLOIN"
            old_app = old_root / "APLIKASI"
            old_database = old_root / "DATABASE" / "delimold.sqlite3"
            old_seed = old_app / "app" / "data" / "seed" / "catalog.json"
            local_appdata = Path(directory) / "profile"
            old_database.parent.mkdir(parents=True)
            old_seed.parent.mkdir(parents=True)
            old_seed.write_text("{}", encoding="utf-8")
            previous_local = os.environ.get("LOCALAPPDATA")
            os.environ["LOCALAPPDATA"] = str(local_appdata)
            try:
                save_config({"mode": "master", "database_path": str(old_database),
                             "seed_path": str(old_seed)}, old_app)
                saved = json.loads((local_appdata / "DELIMOLD" / "config.json").read_text(encoding="utf-8"))
                self.assertEqual("../DATABASE/delimold.sqlite3", saved["database_path"])
                new_root = Path(directory) / "new" / "TENDERLOIN"
                new_app = new_root / "APLIKASI"
                new_seed = new_app / "app" / "data" / "seed" / "catalog.json"
                new_seed.parent.mkdir(parents=True)
                new_seed.write_text("{}", encoding="utf-8")
                loaded = load_config(new_app)
                self.assertEqual(new_root / "DATABASE" / "delimold.sqlite3",
                                 Path(loaded["database_path"]))
                self.assertEqual(new_seed, Path(loaded["seed_path"]))
            finally:
                if previous_local is None:
                    os.environ.pop("LOCALAPPDATA", None)
                else:
                    os.environ["LOCALAPPDATA"] = previous_local

    def test_missing_localappdata_uses_home_appdata_and_keeps_user_config(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "user"
            application = Path(directory) / "TENDERLOIN" / "APLIKASI"
            application.mkdir(parents=True)
            expected = home / "AppData" / "Local" / "DELIMOLD"
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("LOCALAPPDATA", None)
                with patch.object(Path, "home", return_value=home):
                    save_config({"mode": "viewer"}, application)
                    loaded = load_config(application)
            self.assertEqual("viewer", loaded["mode"])
            self.assertTrue((expected / "config.json").is_file())

    def test_corrupt_config_recovers_from_last_good_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            application = root / "APLIKASI"
            application.mkdir()
            local_appdata = root / "profile"
            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_appdata)}):
                save_config({"mode": "viewer", "publish_path": "first"}, application)
                save_config({"mode": "master", "publish_path": "second"}, application)
                config_path = local_appdata / "DELIMOLD" / "config.json"
                backup_path = config_path.with_name("config.json.bak")
                config_path.write_text("{ damaged", encoding="utf-8")

                recovered = load_config(application)

                self.assertEqual("viewer", recovered["mode"])
                self.assertEqual("first", recovered["publish_path"])
                self.assertEqual("viewer", json.loads(config_path.read_text(encoding="utf-8"))["mode"])
                self.assertTrue(backup_path.is_file())
                config_path.unlink()
                self.assertEqual("viewer", load_config(application)["mode"])
                self.assertTrue(config_path.is_file())

    def test_damaged_primary_and_backup_fail_visibly_instead_of_resetting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            application = root / "APLIKASI"
            application.mkdir()
            local_appdata = root / "profile"
            config_dir = local_appdata / "DELIMOLD"
            config_dir.mkdir(parents=True)
            (config_dir / "config.json").write_text("bad", encoding="utf-8")
            (config_dir / "config.json.bak").write_text("also bad", encoding="utf-8")
            with patch.dict(os.environ, {"LOCALAPPDATA": str(local_appdata)}):
                with self.assertRaisesRegex(ConfigurationError, "tidak dapat dipulihkan"):
                    load_config(application)


if __name__ == "__main__":
    unittest.main()
