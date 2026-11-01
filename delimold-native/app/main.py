"""Composition root for the standalone DELIMOLD desktop application."""
import sys
import tkinter as tk
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

from app.adapters.salak_publisher import JsonSnapshotPublisher, JsonSnapshotReader
from app.adapters.seed_catalog_reader import JsonSeedCatalogReader
from app.adapters.configuration import load_config, local_data_directory, resolve_path
from app.adapters.excel_adapter import OpenpyxlWorkbookAdapter
from app.adapters.pdf_adapter import ReportLabPdfAdapter
from app.adapters.sqlite_repository import SQLiteCatalogRepository
from app.adapters.tkinter_ui.app_window import NativeApp
from app.adapters.tkinter_ui.location_settings import configure_master_paths
from app.application.use_cases import DelimoldUseCases


def application_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "APLIKASI"
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


def main():
    base = application_directory()
    try:
        config = load_config(base)
        if config["mode"] not in ("master", "viewer"):
            raise ValueError("Mode yang didukung adalah master atau viewer.")
        root = tk.Tk()
        root.withdraw()
        if config["mode"] == "master" and not config.get("publish_path"):
            root.title("DELIMOLD · Pengaturan lokasi")
            root.geometry("1x1+0+0")
            root.deiconify()
            root.update_idletasks()
            configured = configure_master_paths(root, base, config)
            if not configured:
                root.destroy()
                return 0
            config = configured
            root.withdraw()

        repository = None
        use_cases = None
        try:
            publisher = JsonSnapshotPublisher()
            reader = JsonSnapshotReader()
            seed_reader = JsonSeedCatalogReader()
            workbook = OpenpyxlWorkbookAdapter()
            pdf_exporter = ReportLabPdfAdapter()
            if config["mode"] == "master":
                database_path = resolve_path(base, config["database_path"])
                repository = SQLiteCatalogRepository(database_path)
                seed_path = resolve_path(base, config.get("seed_path", "seed/catalog.json"))
                if seed_path and not seed_path.is_file():
                    source_seed = base / "app" / "data" / "seed" / "catalog.json"
                    seed_path = source_seed if source_seed.is_file() else seed_path
                use_cases = DelimoldUseCases(repository, publisher, reader,
                                             resolve_path(base, config.get("publish_path", "")),
                                             workbook, pdf_exporter, seed_reader)
                if seed_path and seed_path.is_file():
                    use_cases.initialize_catalog_if_empty(seed_path)
                if config.get("publish_on_start", True) and config.get("publish_path"):
                    try:
                        use_cases.publish_pending(force=True)
                    except Exception as exc:
                        messagebox.showwarning("Publikasi SALAK belum siap",
                                               "Data utama tetap dapat dipakai. Snapshot SALAK belum diperbarui.\n\n%s" % exc,
                                               parent=root)
            else:
                use_cases = DelimoldUseCases(None, publisher, reader, workbook=workbook,
                                             pdf_exporter=pdf_exporter)
                snapshot_path = resolve_path(base, config.get("snapshot_path", "published/catalog.json"))
                config["snapshot_path"] = str(snapshot_path)
            root.deiconify()
            NativeApp(root, config, use_cases=use_cases, base_dir=base)
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
            messagebox.showerror("DELIMOLD tidak dapat dimulai", "%s\n\nLog: %s" % (exc, path))
        except Exception:
            pass
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
