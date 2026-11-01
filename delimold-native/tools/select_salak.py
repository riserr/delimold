"""Configure the existing SALAK published folder for DELIMOLD master."""
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from app.adapters.configuration import load_config, save_config


DARK = "#151d18"
PANEL = "#1c2921"
CARD = "#202d25"
INPUT = "#18221c"
TEXT = "#edf3eb"
MUTED = "#b3c2ad"
GREEN = "#55ad7e"
LINE = "#37483c"


def application_directory():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def existing_published_folder(selected):
    target = Path(selected).expanduser().resolve()
    if target.name.lower() != "published":
        child = target / "published"
        if child.is_dir():
            target = child.resolve()
    if target.name.lower() != "published" or not target.is_dir():
        raise ValueError("Pilih folder 'published' yang sudah ada. Program tidak membuat folder SALAK.")
    return target


def main():
    base = application_directory()
    config = load_config(base)
    root = tk.Tk()
    root.title("DELIMOLD · Pilih Publikasi SALAK")
    root.geometry("800x460")
    root.minsize(720, 420)
    root.configure(bg=DARK)

    shell = tk.Frame(root, bg=DARK, padx=24, pady=22)
    shell.pack(fill="both", expand=True)

    header = tk.Frame(shell, bg=PANEL, highlightbackground=LINE, highlightthickness=1,
                      padx=20, pady=16)
    header.pack(fill="x", pady=(0, 16))
    tk.Label(header, text="PENGATURAN TENDERLOIN", bg=PANEL, fg=GREEN,
             font=("Segoe UI", 8, "bold")).pack(anchor="w")
    tk.Label(header, text="Pilih folder publikasi SALAK", bg=PANEL, fg=TEXT,
             font=("Segoe UI", 20, "bold")).pack(anchor="w", pady=(5, 3))
    tk.Label(header,
             text="Pilih folder 'published' yang sudah ada. Lokasi ini disimpan dan dipakai DELIMOLD saat menerbitkan data.",
             bg=PANEL, fg=MUTED, font=("Segoe UI", 9), wraplength=720,
             justify="left").pack(anchor="w")

    card = tk.Frame(shell, bg=CARD, highlightbackground=LINE, highlightthickness=1,
                    padx=20, pady=18)
    card.pack(fill="x", expand=True)
    tk.Label(card, text="TENDERLOIN  →  SALAK", bg="#26382d", fg=GREEN,
             padx=12, pady=7, font=("Segoe UI", 9, "bold")).pack(anchor="w")
    tk.Label(card, text="Folder tujuan", bg=CARD, fg=TEXT,
             font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(16, 6))

    path_var = tk.StringVar(value=config.get("publish_path", ""))
    field_row = tk.Frame(card, bg=CARD)
    field_row.pack(fill="x")
    entry = tk.Entry(field_row, textvariable=path_var, state="readonly", readonlybackground=INPUT,
                     fg=TEXT, relief="flat", highlightthickness=1,
                     highlightbackground=LINE, highlightcolor=GREEN,
                     font=("Segoe UI", 9))
    entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 10))
    status_var = tk.StringVar(value="Lokasi belum dipilih." if not path_var.get() else "Lokasi tersimpan.")
    status = tk.Label(card, textvariable=status_var, bg=CARD, fg=MUTED,
                      font=("Segoe UI", 8), anchor="w")
    status.pack(fill="x", pady=(8, 0))

    def button(parent, text, command, primary=False):
        return tk.Button(parent, text=text, command=command, relief="flat", bd=0,
                         bg=GREEN if primary else CARD,
                         fg="#102017" if primary else TEXT,
                         activebackground="#67bd8f" if primary else "#29392f",
                         activeforeground="#102017" if primary else TEXT,
                         highlightthickness=1, highlightbackground=LINE,
                         font=("Segoe UI", 9), padx=16, pady=8, cursor="hand2")

    def browse():
        current = path_var.get()
        selected = filedialog.askdirectory(
            parent=root,
            title="Pilih folder published di SALAK",
            initialdir=current if Path(current).is_dir() else None,
            mustexist=True,
        )
        if not selected:
            return
        try:
            target = existing_published_folder(selected)
        except ValueError as exc:
            messagebox.showerror("Folder SALAK tidak sesuai", str(exc), parent=root)
            return
        path_var.set(str(target))
        status_var.set("Folder ditemukan. Pilih Simpan lokasi untuk menggunakannya.")
        status.configure(fg=GREEN)

    button(field_row, "Pilih folder…", browse).pack(side="right", padx=(0, 4))

    footer = tk.Frame(shell, bg=DARK)
    footer.pack(fill="x", pady=(14, 0))

    def save():
        try:
            target = existing_published_folder(path_var.get())
            config.update({"mode": "master", "publish_path": str(target), "publish_on_start": True})
            save_config(config, base)
            status_var.set("Lokasi tersimpan. DELIMOLD akan menerbitkan data ke folder ini.")
            status.configure(fg=GREEN)
        except Exception as exc:
            status_var.set("Lokasi belum tersimpan: %s" % exc)
            status.configure(fg="#f1a79b")

    button(footer, "Tutup", root.destroy).pack(side="right", padx=(10, 4))
    button(footer, "Simpan lokasi", save, primary=True).pack(side="right", padx=(4, 0))
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
