"""Load the desktop configuration and resolve its file paths at startup."""
import json
import os
import tempfile
from pathlib import Path

from app.domain.errors import ConfigurationError
from app.application.ports import ConfigurationStore


def local_data_directory():
    local = os.environ.get("LOCALAPPDATA", "").strip()
    base = Path(local).expanduser() if local else Path.home() / "AppData" / "Local"
    return base / "DELIMOLD"


DATABASE_RELATIVE_PATH = Path("DATABASE") / "delimold.sqlite3"
SEED_RELATIVE_PATH = Path("app") / "data" / "seed" / "catalog.json"


def package_root(application_dir):
    """Return TENDERLOIN when called from APLIKASI, or the source root in development."""
    directory = Path(application_dir).resolve()
    return directory.parent if directory.name.lower() == "aplikasi" else directory


def default_database_path(application_dir):
    return package_root(application_dir) / DATABASE_RELATIVE_PATH


def default_seed_path(application_dir):
    return Path(application_dir).resolve() / SEED_RELATIVE_PATH


def legacy_database_path():
    return local_data_directory() / "delimold.sqlite3"


def load_config(application_dir):
    """Load user settings, recovering the last good copy if the primary is damaged.

    User settings live under LOCALAPPDATA/DELIMOLD. If LOCALAPPDATA is absent,
    use the standard per-user AppData/Local path beneath the home directory.
    A valid config.json.bak is used and restored when config.json is missing or
    unreadable. If both user copies are damaged, fail visibly rather than
    silently discarding the user's selected paths.
    """
    user_path = local_data_directory() / "config.json"
    backup_path = user_path.with_name("config.json.bak")
    packaged_path = Path(application_dir) / "config.json"
    defaults = {"mode": "master", "database_path": str(default_database_path(application_dir)),
                "seed_path": str(default_seed_path(application_dir)), "publish_path": "", "publish_on_start": True,
                "snapshot_path": "published-python/catalog.json"}
    if not user_path.exists() and not backup_path.exists() and not packaged_path.exists():
        return defaults
    user_files = (user_path, backup_path)
    failures = []
    if any(candidate.exists() for candidate in user_files):
        for candidate in user_files:
            if not candidate.exists():
                continue
            try:
                loaded = _read_config(candidate)
                config = _normalize_config(loaded, defaults, application_dir)
                if candidate == backup_path:
                    try:
                        _atomic_write(user_path, candidate.read_bytes())
                    except OSError:
                        # The backup is still usable for this run; next save can
                        # restore the primary file when the directory is writable.
                        pass
                return config
            except (OSError, ValueError, TypeError) as exc:
                failures.append("%s: %s" % (candidate.name, exc))
        raise ConfigurationError(
            "Konfigurasi dan cadangannya tidak dapat dipulihkan. "
            "Periksa %s. Detail: %s" % (user_path.parent, "; ".join(failures)))
    if packaged_path.exists():
        try:
            return _normalize_config(_read_config(packaged_path), defaults, application_dir)
        except (OSError, ValueError, TypeError) as exc:
            raise ConfigurationError("config.json paket tidak dapat dibaca.") from exc
    return defaults


def _read_config(path):
    with Path(path).open("r", encoding="utf-8") as stream:
        loaded = json.load(stream)
    if not isinstance(loaded, dict):
        raise ValueError("config.json harus berupa objek JSON")
    return loaded


def _normalize_config(loaded, defaults, application_dir):
    config = dict(defaults)
    config.update(loaded)
    if not config.get("database_path"):
        config["database_path"] = str(default_database_path(application_dir))
    config["database_path"] = str(resolve_path(application_dir, config["database_path"]).resolve())
    config["seed_path"] = str(resolve_seed_path(application_dir, config.get("seed_path")))
    return config


def _atomic_write(path, payload):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".%s-" % path.name, suffix=".tmp",
                                     dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, str(path))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _portable_path(application_dir, value):
    if not value:
        return value
    path = Path(value).expanduser().resolve()
    try:
        return os.path.relpath(str(path), str(Path(application_dir).resolve()))
    except ValueError:
        return str(path)


def save_config(config, application_dir=None):
    """Persist settings atomically and retain one last-known-good backup."""
    target = local_data_directory() / "config.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        if target.exists():
            try:
                current = target.read_bytes()
                if isinstance(json.loads(current.decode("utf-8")), dict):
                    _atomic_write(target.with_name("config.json.bak"), current)
            except (OSError, UnicodeError, ValueError):
                # Never copy a corrupt primary over a valid recovery backup.
                pass
        persisted = dict(config)
        if application_dir is not None:
            for key in ("database_path", "seed_path", "snapshot_path"):
                if persisted.get(key):
                    persisted[key] = _portable_path(application_dir, persisted[key])
        payload = json.dumps(persisted, ensure_ascii=False, indent=2).encode("utf-8")
        _atomic_write(target, payload)
    except OSError as exc:
        raise ConfigurationError("Pengaturan DELIMOLD tidak dapat disimpan.") from exc


class JsonConfigurationStore(ConfigurationStore):
    """Persist user settings as JSON in the per-user DELIMOLD directory."""
    def __init__(self, application_dir=None):
        self._application_dir = application_dir

    def save(self, config):
        save_config(config, self._application_dir)


def resolve_path(application_dir, value):
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else Path(application_dir) / path


def resolve_seed_path(application_dir, value=None):
    """Resolve configured seed data, falling back only to the canonical packaged seed."""
    configured = resolve_path(application_dir, value) if value else None
    if configured is not None and configured.is_file():
        return configured.resolve()
    return default_seed_path(application_dir)
