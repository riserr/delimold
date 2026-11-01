"""Load the desktop configuration and resolve its file paths at startup."""
import json
import os
from pathlib import Path

from app.domain.errors import ConfigurationError


def local_data_directory():
    local = os.environ.get("LOCALAPPDATA")
    return Path(local) / "DELIMOLD" if local else Path.home() / "AppData" / "Local" / "DELIMOLD"


def load_config(application_dir):
    # Keep user-selected paths in a writable per-user location. The packaged
    # config remains a read-only set of defaults beside the executable.
    user_path = local_data_directory() / "config.json"
    packaged_path = Path(application_dir) / "config.json"
    path = user_path if user_path.exists() else packaged_path
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


def save_config(config):
    """Atomically persist user configuration outside the install/package folder."""
    target = local_data_directory() / "config.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".tmp")
    try:
        with temporary.open("w", encoding="utf-8") as stream:
            json.dump(config, stream, ensure_ascii=False, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(str(temporary), str(target))
    except OSError as exc:
        try:
            temporary.unlink()
        except OSError:
            pass
        raise ConfigurationError("Pengaturan DELIMOLD tidak dapat disimpan.") from exc


def resolve_path(application_dir, value):
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else Path(application_dir) / path
