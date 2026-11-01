"""Composition root for the standalone DELIMOLD desktop application."""
import sys
import tkinter as tk
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

from app.adapters.salak_publisher import JsonSnapshotPublisher, JsonSnapshotReader
from app.adapters.seed_catalog_reader import JsonSeedCatalogReader
from app.adapters.configuration import (JsonConfigurationStore, load_config,
                                        default_database_path, legacy_database_path,
                                        local_data_directory, resolve_path, resolve_seed_path,
                                        save_config)
from app.adapters.excel_adapter import OpenpyxlWorkbookAdapter
from app.adapters.pdf_adapter import ReportLabPdfAdapter
from app.adapters.sqlite_repository import SQLiteCatalogRepository
from app.adapters.tkinter_ui.app_window import NativeApp
from app.adapters.tkinter_ui.error_presenter import present_error
from app.application.use_cases import DelimoldUseCases


def application_directory():
    if getattr(sys, "frozen", False):
        # PyInstaller places DELIMOLD.exe directly inside APLIKASI.
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _log_path():
    return local_data_directory() / "startup.log"


def log_error(error):
    try:
        path = _log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as stream:
            stream.write("\n[%s] DELIMOLD gagal dimulai\n" % datetime.now().isoformat())
            stream.write("".join(traceback.format_exception(type(error), error, error.__traceback__)))
        return str(path)
    except OSError:
        return "log startup tidak dapat ditulis"


def select_published_salak_folder(root, config, base):
    """Ask once for an existing SALAK published folder and remember it."""
    if config.get("mode") != "master" or config.get("publish_path"):
        return True

    selected = filedialog.askdirectory(
        parent=root,
        title="Pilih folder published di SALAK",
        mustexist=True,
    )
    if not selected:
        return False

    target = Path(selected).resolve()
    if target.name.lower() != "published":
        published_child = target / "published"
        if published_child.is_dir():
            target = published_child.resolve()
        else:
            raise ValueError(
                "Pilih folder bernama 'published' yang sudah ada di SALAK. "
                "DELIMOLD tidak membuat folder publikasi baru."
            )

    config["publish_path"] = str(target)
    config["publish_on_start"] = True
    save_config(config, base)
    return True


def main():
    base = application_directory()
    try:
        config = load_config(base)
        if config["mode"] not in ("master", "viewer"):
            raise ValueError("Mode yang didukung adalah master atau viewer.")
        root = tk.Tk()
        root.withdraw()
        if not select_published_salak_folder(root, config, base):
            root.destroy()
            return 0

        repository = None
        use_cases = None
        seed_path = None
        app = None
        try:
            publisher = JsonSnapshotPublisher()
            reader = JsonSnapshotReader()
            seed_reader = JsonSeedCatalogReader()
            workbook = OpenpyxlWorkbookAdapter()
            pdf_exporter = ReportLabPdfAdapter()
            if config["mode"] == "master":
                database_path = resolve_path(base, config["database_path"])
                package_database = default_database_path(base).resolve()
                old_database = legacy_database_path().resolve()
                if database_path and database_path.resolve() == old_database and old_database.is_file():
                    if not package_database.exists():
                        SQLiteCatalogRepository.migrate_database(old_database, package_database)
                    if package_database.exists():
                        config["database_path"] = str(package_database)
                        save_config(config, base)
                        database_path = package_database
                repository = SQLiteCatalogRepository(database_path)
                seed_path = resolve_seed_path(base, config.get("seed_path"))
                use_cases = DelimoldUseCases(repository, publisher, reader,
                                             resolve_path(base, config.get("publish_path", "")),
                                             workbook, pdf_exporter, seed_reader,
                                             JsonConfigurationStore(base))
            else:
                use_cases = DelimoldUseCases(None, publisher, reader, workbook=workbook,
                                             pdf_exporter=pdf_exporter,
                                             configuration_store=JsonConfigurationStore(base))
                snapshot_path = resolve_path(base, config.get("snapshot_path", "published/catalog.json"))
                config["snapshot_path"] = str(snapshot_path)
            root.deiconify()
            app = NativeApp(root, config, use_cases=use_cases, base_dir=base)
            # On a fresh install the repository constructor creates only the
            # SQLite schema. Let the first Supervisor account be created and
            # authenticated before importing the starter catalog.
            if config["mode"] == "master" and app.account is not None and root.winfo_exists():
                if seed_path and seed_path.is_file():
                    use_cases.initialize_catalog_if_empty(seed_path)
                    app.refresh()
                if config.get("publish_on_start", True) and config.get("publish_path"):
                    try:
                        use_cases.publish_pending(force=True)
                    except Exception as exc:
                        messagebox.showwarning("Publikasi SALAK belum siap",
                                               "Data lokal tetap dapat dipakai. Publikasi SALAK tertunda dan akan dicoba lagi otomatis.\n\n%s" % present_error(exc),
                                               parent=root)
            root.mainloop()
        except Exception:
            if use_cases:
                try:
                    use_cases.close()
                except Exception:
                    pass
            elif repository:
                repository.close()
            raise
        return 0
    except Exception as exc:
        path = log_error(exc)
        try:
            messagebox.showerror("DELIMOLD tidak dapat dimulai",
                                 "%s\n\nLog: %s" % (present_error(exc), path))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
