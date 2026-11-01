"""Load the desktop configuration and resolve its file paths at startup."""
import json
import os
from pathlib import Path

from app.domain.errors import ConfigurationError


def local_data_directory():
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "DELIMOLD" if local else Path.home() / "AppData" / "Local" / "DELIMOLD"


def load_config(application_dir):
    path = Path(application_dir) / "config.json"
    defaults = {"mode": "master", "database_path": str(local_data_directory() / "delimold.sqlite3"),
                "seed_path": "seed/catalog.json", "publish_path": "", "publish_on_start": True,
                "snapshot_path": "published-python/catalog.json"}
    if not path.exists():
        return defaults
    try:
        with path.open("r", encoding="utf-8") as stream:
            loaded = json.load(stream)
        if not isinstance(loaded, dict):
            raise ValueError("config.json harus berupa objek JSON")
        defaults.update(loaded)
        if not defaults.get("database_path"):
            defaults["database_path"] = str(local_data_directory() / "delimold.sqlite3")
        return defaults
    except (OSError, ValueError) as exc:
        raise ConfigurationError("config.json tidak dapat dibaca: %s" % exc) from exc


def resolve_path(application_dir, value):
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else Path(application_dir) / path
