"""Native first-run path setup for the TENDERLOIN desktop app."""
import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from uuid import uuid4


def _writable_folder(folder, create=True):
    path = Path(folder)
    if create:
        path.mkdir(parents=True, exist_ok=True)
    probe = path / (".delimold-write-check-" + uuid4().hex + ".tmp")
    try:
        probe.write_text("ok", encoding="ascii")
        probe.unlink()
    except Exception:
        try:
            if probe.exists():
                probe.unlink()
        except Exception:
            pass
        raise


def _save_config(base, config):
    target = Path(base) / "config.json"
    temporary = target.with_name(target.name + ".tmp")
    temporary.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(temporary), str(target))


def configure_master_paths(root, base, config, force=False):
    """Ask once for a local DB and the SALAK App share path; return updated config."""
    if not force and config.get("publish_path"):
        return config

    base = Path(base).resolve()
    configured_database = config.get("database_path", "")
    if configured_database:
        default_database = Path(configured_database)
        if not default_database.is_absolute():
            default_database = base / default_database
    else:
        # Keep the live database off the shared application folder. Engineer
        # clients launch the same EXE from the share, so only TENDERLOIN's
        # local profile should own the writable SQLite file.
        local_app_data = os.environ.get("LOCALAPPDATA") or str(base.parent)
        default_database = Path(local_app_data) / "DELIMOLD" / "delimold.sqlite3"
    default_publish = config.get("publish_path", "")

    dialog = tk.Toplevel(root)
    dialog.title("Pengaturan lokasi DELIMOLD")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()
    box = ttk.Frame(dialog, padding=20)
    box.pack(fill="both", expand=True)

    ttk.Label(box, text="Lokasi data DELIMOLD", font=("Segoe UI", 15, "bold")).grid(
        row=0, column=0, columnspan=3, sticky="w")
    ttk.Label(box, text="Database disimpan lokal di TENDERLOIN. Snapshot SALAK ditulis ke folder bersama.",
              wraplength=600).grid(row=1, column=0, columnspan=3, sticky="w", pady=(5, 16))

    ttk.Label(box, text="Database TENDERLOIN").grid(row=2, column=0, sticky="w", pady=5)
    database_var = tk.StringVar(dialog, str(default_database))
    database_entry = ttk.Entry(box, textvariable=database_var, width=70)
    database_entry.grid(row=2, column=1, sticky="ew", padx=8, pady=5)

    def browse_database():
        current = Path(database_var.get())
        chosen = filedialog.asksaveasfilename(
            parent=dialog, title="Pilih file database lokal TENDERLOIN",
            initialdir=str(current.parent if current.parent.exists() else base),
            initialfile=current.name or "delimold.sqlite3",
            defaultextension=".sqlite3",
            filetypes=(("Database DELIMOLD", "*.sqlite3"), ("Semua file", "*.*")))
        if chosen:
            database_var.set(chosen)

    ttk.Button(box, text="Pilih…", command=browse_database).grid(row=2, column=2, pady=5)
    ttk.Label(box, text="Gunakan folder lokal TENDERLOIN, bukan folder bersama atau SALAK.",
              foreground="#6f806a").grid(row=3, column=1, sticky="w", padx=8, pady=(0, 12))

    ttk.Label(box, text="Folder App di SALAK").grid(row=4, column=0, sticky="w", pady=5)
    publish_var = tk.StringVar(dialog, default_publish)
    ttk.Entry(box, textvariable=publish_var, width=70).grid(row=4, column=1, sticky="ew", padx=8, pady=5)

    def browse_publish():
        selected = filedialog.askdirectory(parent=dialog, title="Pilih folder App bersama di SALAK",
                                           mustexist=True)
        if selected:
            selected_path = Path(selected)
            target = selected_path if selected_path.name.lower() == "published-python" else selected_path / "published-python"
            publish_var.set(str(target))

    ttk.Button(box, text="Cari di SALAK…", command=browse_publish).grid(row=4, column=2, pady=5)
    ttk.Label(box, text="Folder published-python dibuat di dalam folder yang dipilih.",
              foreground="#6f806a").grid(row=5, column=1, sticky="w", padx=8, pady=(0, 12))

    error = tk.StringVar(dialog)
    ttk.Label(box, textvariable=error, foreground="#a34739", wraplength=600).grid(
        row=6, column=0, columnspan=3, sticky="w", pady=(0, 8))
    buttons = ttk.Frame(box)
    buttons.grid(row=7, column=0, columnspan=3, sticky="e")
    result = {"config": None}

    def save():
        try:
            database = Path(database_var.get().strip()).expanduser()
            if not database.is_absolute():
                database = (base / database).resolve()
            if str(database).startswith(("\\\\", "//")):
                raise ValueError("Database harus berada di disk lokal TENDERLOIN. Pilih folder lokal seperti AppData atau C:.")
            if database.exists() and database.is_dir():
                raise ValueError("Pilih nama file database, bukan folder.")
            _writable_folder(database.parent)

            publish = Path(publish_var.get().strip())
            if not publish_var.get().strip():
                raise ValueError("Pilih folder App bersama di SALAK terlebih dahulu.")
            _writable_folder(publish)

            updated = dict(config)
            updated.update({
                "mode": "master",
                "database_path": str(database),
                "publish_path": str(publish),
                "publish_on_start": True,
            })
            _save_config(base, updated)
            result["config"] = updated
            dialog.destroy()
        except Exception as exc:
            error.set("Belum tersimpan: %s" % exc)

    ttk.Button(buttons, text="Batal", command=dialog.destroy).pack(side="right", padx=(8, 0))
    ttk.Button(buttons, text="Simpan lokasi", command=save).pack(side="right")
    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.wait_window()
    return result["config"]
