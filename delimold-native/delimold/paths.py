"""Native, first-run location setup for the TENDERLOIN desktop app."""
import json
import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog
from uuid import uuid4


DARK = "#151d18"
SIDEBAR = "#1d2922"
PANEL = "#1d2a22"
CARD = "#202d25"
INPUT = "#18221c"
TEXT = "#edf3eb"
MUTED = "#b3c2ad"
GREEN = "#55ad7e"
LINE = "#37483c"


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


class _RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command, primary=False):
        self.label = text
        self.command = command
        self.primary = primary
        self.width = max(78, len(text) * 7 + 26)
        self.height = 36
        self.fill = GREEN if primary else CARD
        self.hover = "#67bd8f" if primary else "#29392f"
        self.foreground = "#102017" if primary else TEXT
        super().__init__(parent, width=self.width, height=self.height, bd=0, highlightthickness=0,
                         bg=parent.cget("bg"), takefocus=True, cursor="hand2")
        self._draw(self.fill)
        self.bind("<Enter>", lambda _event: self._draw(self.hover))
        self.bind("<Leave>", lambda _event: self._draw(self.fill))
        self.bind("<Button-1>", self._invoke)
        self.bind("<Return>", self._invoke)
        self.bind("<space>", self._invoke)

    def _rounded(self, x1, y1, x2, y2, radius, color):
        r = radius
        self.create_rectangle(x1 + r, y1, x2 - r, y2, fill=color, outline=color)
        self.create_rectangle(x1, y1 + r, x2, y2 - r, fill=color, outline=color)
        for x, y in ((x1, y1), (x2 - 2*r, y1), (x1, y2 - 2*r), (x2 - 2*r, y2 - 2*r)):
            self.create_oval(x, y, x + 2*r, y + 2*r, fill=color, outline=color)

    def _draw(self, color):
        self.delete("all")
        self._rounded(0, 0, self.width - 1, self.height - 1, 5, LINE if not self.primary else color)
        self._rounded(1, 1, self.width - 2, self.height - 2, 4, color)
        self.create_text(self.width // 2, self.height // 2, text=self.label, fill=self.foreground,
                         font=("Segoe UI", 9))

    def _invoke(self, _event=None):
        self.command()


def configure_master_paths(root, base, config, force=False):
    """Show the approved DELIMOLD settings screen and save local/share paths."""
    if not force and config.get("publish_path"):
        return config

    base = Path(base).resolve()
    configured_database = config.get("database_path", "")
    if configured_database:
        default_database = Path(configured_database)
        if not default_database.is_absolute():
            default_database = base / default_database
    else:
        local_app_data = os.environ.get("LOCALAPPDATA") or str(base.parent)
        default_database = Path(local_app_data) / "DELIMOLD" / "delimold.sqlite3"
    default_publish = config.get("publish_path", "")

    root.title("DELIMOLD · Data Cetakan Ban")
    root.geometry("980x700")
    root.minsize(920, 620)
    root.configure(bg=DARK)
    root.deiconify()
    root.update_idletasks()

    shell = tk.Frame(root, bg=DARK)
    shell.pack(fill="both", expand=True, padx=9, pady=9)

    top = tk.Frame(shell, bg="#1c2921", height=48, highlightbackground=LINE, highlightthickness=1)
    top.pack(fill="x")
    top.pack_propagate(False)
    tk.Label(top, text="DELIMOLD · Data Cetakan Ban", bg="#1c2921", fg=TEXT,
             font=("Segoe UI", 9)).pack(side="left", padx=18)
    tk.Label(top, text="TENDERLOIN  ·  Supervisor", bg="#1c2921", fg=TEXT,
             font=("Segoe UI", 9)).pack(side="right", padx=18)

    body = tk.Frame(shell, bg=DARK)
    body.pack(fill="both", expand=True)
    sidebar = tk.Frame(body, bg=SIDEBAR, width=206, highlightbackground=LINE, highlightthickness=1)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)
    brand = tk.Frame(sidebar, bg=SIDEBAR)
    brand.pack(fill="x", padx=18, pady=(27, 28))
    tk.Label(brand, text="M", bg=GREEN, fg=TEXT, font=("Georgia", 18), width=2, height=1).pack(side="left", padx=(0, 9))
    tk.Label(brand, text="DELIMOLD\nDATA CETAKAN\nBAN", bg=SIDEBAR, fg=TEXT, justify="left",
             font=("Segoe UI", 9, "bold")).pack(side="left")

    for label in ("Data Cetakan", "Data Container", "Data Pattern", "Development Project", "Riwayat perubahan"):
        tk.Label(sidebar, text="▤   " + label, anchor="w", bg=SIDEBAR, fg=MUTED,
                 font=("Segoe UI", 9), padx=12, pady=10).pack(fill="x", padx=10, pady=1)
    tk.Label(sidebar, text="⚙   Atur lokasi data", anchor="w", bg="#2b3b30", fg=TEXT,
             font=("Segoe UI", 9, "bold"), padx=12, pady=10).pack(fill="x", padx=10, pady=2)
    tk.Frame(sidebar, bg=SIDEBAR).pack(fill="both", expand=True)
    tk.Label(sidebar, text="Satu sumber data.\nHak akses mengikuti peran.", anchor="w", bg=SIDEBAR,
             fg=MUTED, font=("Segoe UI", 8), padx=17, pady=14).pack(fill="x")

    content = tk.Frame(body, bg=DARK)
    content.pack(side="left", fill="both", expand=True, padx=26, pady=25)
    tk.Label(content, text="PENGATURAN TENDERLOIN", bg=DARK, fg=MUTED,
             font=("Segoe UI", 8)).pack(anchor="w")
    tk.Label(content, text="Lokasi data DELIMOLD", bg=DARK, fg=TEXT,
             font=("Segoe UI", 20)).pack(anchor="w", pady=(10, 3))
    tk.Label(content, text="Atur database utama dan folder publikasi bersama.", bg=DARK, fg=MUTED,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 17))

    card = tk.Frame(content, bg=CARD, highlightbackground=LINE, highlightthickness=1, padx=18, pady=17)
    card.pack(fill="both", expand=True)
    tk.Label(card, text="Database TENDERLOIN", bg=CARD, fg=TEXT,
             font=("Segoe UI", 12, "bold")).pack(anchor="w")
    tk.Label(card, text="Database aktif tetap di komputer TENDERLOIN, tidak disimpan di share Engineer atau SALAK.",
             bg=CARD, fg=MUTED, justify="left", wraplength=650,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(9, 16))

    database_row = tk.Frame(card, bg=CARD)
    database_row.pack(fill="x")
    tk.Label(database_row, text="File database", width=20, anchor="w", bg=CARD, fg=TEXT,
             font=("Segoe UI", 9, "bold")).pack(side="left")
    database_var = tk.StringVar(root, str(default_database))
    database_entry = tk.Entry(database_row, textvariable=database_var, bg=INPUT, fg=TEXT,
                              insertbackground=TEXT, relief="flat", highlightthickness=1,
                              highlightbackground=LINE, highlightcolor=GREEN,
                              font=("Segoe UI", 9))
    database_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))

    def browse_database():
        current = Path(database_var.get())
        chosen = filedialog.asksaveasfilename(
            parent=root, title="Pilih file database lokal TENDERLOIN",
            initialdir=str(current.parent if current.parent.exists() else base),
            initialfile=current.name or "delimold.sqlite3", defaultextension=".sqlite3",
            filetypes=(("Database DELIMOLD", "*.sqlite3"), ("Semua file", "*.*")))
        if chosen:
            database_var.set(chosen)

    db_button = _RoundedButton(database_row, "Pilih…", browse_database)
    db_button.pack(side="right")
    tk.Label(card, text="Disimpan lokal pada komputer TENDERLOIN.", bg=CARD, fg=MUTED,
             font=("Segoe UI", 8)).pack(anchor="w", padx=(160, 0), pady=(8, 18))

    tk.Frame(card, bg=LINE, height=1).pack(fill="x", pady=(0, 16))
    tk.Label(card, text="Publikasi SALAK", bg=CARD, fg=TEXT,
             font=("Segoe UI", 12, "bold")).pack(anchor="w")
    tk.Label(card, text="Snapshot baca-saja akan ditulis ke folder bersama ini.", bg=CARD, fg=MUTED,
             font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 14))
    publish_row = tk.Frame(card, bg=CARD)
    publish_row.pack(fill="x")
    tk.Label(publish_row, text="Folder tujuan", width=20, anchor="w", bg=CARD, fg=TEXT,
             font=("Segoe UI", 9, "bold")).pack(side="left")
    publish_var = tk.StringVar(root, default_publish)
    publish_entry = tk.Entry(publish_row, textvariable=publish_var, bg=INPUT, fg=TEXT,
                             insertbackground=TEXT, relief="flat", highlightthickness=1,
                             highlightbackground=LINE, highlightcolor=GREEN,
                             font=("Segoe UI", 9))
    publish_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))

    def browse_publish():
        selected = filedialog.askdirectory(parent=root, title="Pilih folder App bersama di SALAK", mustexist=True)
        if selected:
            selected_path = Path(selected)
            target = selected_path if selected_path.name.lower() == "published-python" else selected_path / "published-python"
            publish_var.set(str(target))

    publish_button = _RoundedButton(publish_row, "Cari di SALAK…", browse_publish)
    publish_button.pack(side="right")
    tk.Label(card, text="Jika memilih folder App, subfolder published-python dibuat otomatis.",
             bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=(160, 0), pady=(8, 18))

    footer = tk.Frame(card, bg=CARD)
    footer.pack(fill="x", side="bottom", pady=(16, 0))
    tk.Frame(footer, bg=LINE, height=1).pack(fill="x", pady=(0, 14))
    done = tk.StringVar(root, "")
    error_label = tk.Label(footer, textvariable=done, bg=CARD, fg=GREEN,
                           font=("Segoe UI", 8), anchor="w")
    error_label.pack(side="left", fill="x", expand=True)
    result = {"config": None}

    def save():
        try:
            database = Path(database_var.get().strip()).expanduser()
            if not database.is_absolute():
                database = (base / database).resolve()
            if str(database).startswith(("\\\\", "//")):
                raise ValueError("Database harus berada di disk lokal TENDERLOIN.")
            if database.exists() and database.is_dir():
                raise ValueError("Pilih nama file database, bukan folder.")
            _writable_folder(database.parent)

            if not publish_var.get().strip():
                raise ValueError("Pilih folder App bersama di SALAK terlebih dahulu.")
            publish = Path(publish_var.get().strip())
            _writable_folder(publish)

            updated = dict(config)
            updated.update({"mode": "master", "database_path": str(database),
                            "publish_path": str(publish), "publish_on_start": True})
            _save_config(base, updated)
            result["config"] = updated
            done.set("Lokasi tersimpan. DELIMOLD sedang disiapkan…")
            for child in root.winfo_children():
                child.destroy()
        except Exception as exc:
            error_label.configure(fg="#f1a79b")
            done.set("Belum tersimpan: %s" % exc)

    save_button = _RoundedButton(footer, "Simpan lokasi", save, primary=True)
    save_button.pack(side="right", padx=(12, 0))

    root.protocol("WM_DELETE_WINDOW", lambda: done.set("cancelled"))
    root.wait_variable(done)
    return result["config"]
