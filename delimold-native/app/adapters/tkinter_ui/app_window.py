"""Native Tk desktop UI. This module never opens or embeds a browser."""
import json
import re
import socket
import tkinter as tk
import tkinter.font as tkfont
import time
from tkinter import filedialog, messagebox, simpledialog, ttk
from pathlib import Path
from uuid import uuid4

from app.domain.models import Actor
from .location_settings import configure_master_paths
from .app_window_theme import CARD, DARK, FIELD, GREEN, INK, LINE, MUTED, PALE, WHITE
from .shared_components import build_database_status, build_header, build_sidebar


class RoundedToolbarButton(tk.Canvas):
    """Canvas-backed toolbar button matching checkpoint v12's rounded shape."""
    def __init__(self, parent, text, command, primary=False):
        self.label = text
        self.command = command
        self.primary = primary
        self.font = tkfont.Font(parent, family="Segoe UI", size=8)
        self.label_color = "#102017" if primary else INK
        self.normal_fill = GREEN if primary else WHITE
        self.hover_fill = self.normal_fill if primary else "#29392f"
        self.border = self.normal_fill if primary else LINE
        self.width = self.font.measure(text) + 26
        self.height = self.font.metrics("linespace") + 16
        super().__init__(parent, width=self.width, height=self.height, bd=0, highlightthickness=0,
                         relief="flat", bg=parent.cget("bg"), takefocus=True, cursor="hand2")
        self._draw(self.normal_fill)
        self.bind("<Enter>", lambda _event: self._draw(self.hover_fill))
        self.bind("<Leave>", lambda _event: self._draw(self.normal_fill))
        self.bind("<Button-1>", self._invoke)
        self.bind("<Return>", self._invoke)
        self.bind("<space>", self._invoke)

    def _rounded_rect(self, x1, y1, x2, y2, radius, fill, tags):
        r = radius
        self.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline=fill, tags=tags)
        self.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline=fill, tags=tags)
        for x, y in ((x1, y1), (x2 - 2 * r, y1), (x1, y2 - 2 * r), (x2 - 2 * r, y2 - 2 * r)):
            self.create_oval(x, y, x + 2 * r, y + 2 * r, fill=fill, outline=fill, tags=tags)

    def _draw(self, fill):
        self.delete("all")
        self._rounded_rect(0, 0, self.width - 1, self.height - 1, 5, self.border, "border")
        self._rounded_rect(1, 1, self.width - 2, self.height - 2, 4, fill, "surface")
        self.create_text(self.width // 2, self.height // 2, text=self.label, fill=self.label_color,
                         font=self.font, tags="label")

    def _invoke(self, _event=None):
        self.command()

    def cget(self, key):
        if key == "text":
            return self.label
        return super().cget(key)

TABS = {
    "molds": "Data Cetakan",
    "containers": "Data Container",
    "patterns": "Data Pattern",
    "stickers": "Data Sticker",
    "projects": "Development Project",
    "purchases": "Pembelian Mold",
    "accounts": "Management Akun",
    "history": "Riwayat perubahan",
}

FIELDS = {
    "molds": [("spec", "Kode spek"), ("category", "Kategori"), ("size", "Size cetakan"), ("serial", "Nomor cetakan"),
              ("patternId", "Pattern *"), ("containerId", "Container"), ("spacer", "Spacer (mm)"),
              ("cure", "Tipe masak"), ("mtype", "Tipe cetakan"), ("role", "Ukuran"),
              ("mainId", "Acuan Main / Sharing"), ("owner", "Pemilik"),
              ("bladder", "Bladder"), ("brands", "Merek (pisahkan koma)"), ("status", "Status"), ("statusReason", "Alasan status"), ("note", "Catatan")],
    "containers": [("code", "Kode container"), ("serial", "Nomor container"), ("od", "OD sector (mm)"),
                   ("sw", "SW sector (mm)"), ("spacers", "Spacer (JSON)"), ("status", "Status")],
    "patterns": [("code", "Kode pattern"), ("name", "Nama pattern"), ("land", "Land ratio"),
                 ("status", "Status")],
    "stickers": [("name", "Nama sticker"), ("status", "Status")],
    "projects": [("projectId", "ID project"), ("name", "Nama project"), ("spec", "Kode spek"),
                 ("description", "Deskripsi"), ("moldNumbers", "Nomor cetakan"), ("status", "Status"),
                 ("designStart", "Mulai desain"), ("designEnd", "Selesai desain"),
                 ("layoutStart", "Mulai layout"), ("layoutEnd", "Selesai layout"),
                 ("markingStart", "Mulai marking"), ("markingEnd", "Selesai marking"),
                 ("targetDays", "Target pengerjaan (hari)")],
    "purchases": [("date", "Tanggal pembelian *"), ("poReceivedDate", "PO diterima (YYYY-MM-DD)"),
                   ("spec", "Kode spek *"), ("size", "Size ban *"), ("pattern", "Kode pattern"),
                   ("moldNumber", "Nomor mold"), ("quantity", "Jumlah mold *"), ("supplier", "Supplier"),
                   ("currency", "Mata uang *"), ("price", "Harga satuan *"), ("status", "Status"),
                   ("note", "Keterangan")],
}

FILTER_FIELDS = {
    "molds": (("spec", "Kode spek"), ("size", "Size cetakan"), ("patternId", "Pattern"),
              ("cure", "Tipe masak"), ("mtype", "Tipe cetakan"), ("owner", "Pemilik"), ("status", "Status")),
    "containers": (("code", "Kode container"), ("serial", "Nomor container"), ("status", "Status")),
    "patterns": (("code", "Kode pattern"), ("name", "Nama pattern"), ("status", "Status")),
    "stickers": (("name", "Nama sticker"), ("status", "Status")),
    "projects": (("spec", "Kode spek"), ("name", "Nama project"), ("status", "Status")),
    "purchases": (("spec", "Kode spek"), ("supplier", "Supplier"), ("status", "Status")),
    "accounts": (("role", "Peran"), ("enabled", "Status akun")),
    "history": (("action", "Aktivitas"), ("collection", "Jenis data")),
}


class NativeApp:
    def __init__(self, root, config, use_cases, base_dir=None):
        self.root = root
        self.config = config
        self.use_cases = use_cases
        self.base_dir = Path(base_dir or Path.cwd())
        self.mode = config.get("mode", "master")
        self.account = None
        self.collection = "molds"
        self.catalog = {"collections": {}}
        self.rows = []
        self.filtered = []
        self.search_var = tk.StringVar()
        self.filter_vars = {}
        self.filter_boxes = {}
        self.page_var = tk.StringVar(value="50")
        self.page_index = 0
        self.page_total = 0
        self._page_stats = None
        self.filter_query_maps = {}
        self._search_after_id = None
        self.status_text = tk.StringVar(value="Memuat data…")
        self._style()
        self.root.title("DELIMOLD · Data Cetakan Ban")
        self.root.geometry("1280x800")
        self.root.minsize(980, 620)
        self.root.configure(bg=DARK)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self._login()
        if self.account is None and self.mode != "viewer":
            self.root.after(0, self.close)
            return
        self._build()
        self.refresh()

    def _style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=INK,
                        rowheight=29, bordercolor=LINE, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=WHITE, foreground=MUTED,
                        font=("Segoe UI", 8, "bold"), relief="flat", padding=(7, 8))
        style.map("Treeview", background=[("selected", "#355640")] , foreground=[("selected", INK)])
        style.configure("TCombobox", padding=6, fieldbackground=FIELD, background=WHITE, foreground=INK, arrowcolor=INK, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        style.map("TCombobox", fieldbackground=[("readonly", FIELD)], foreground=[("readonly", INK)], selectbackground=[("readonly", FIELD)], selectforeground=[("readonly", INK)])
        style.configure("TEntry", padding=7, fieldbackground=FIELD, foreground=INK, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE)
        style.configure("TFrame", background=WHITE)
        style.configure("TLabel", background=WHITE, foreground=INK)
        style.configure("TButton", background=WHITE, foreground=INK, bordercolor=LINE, padding=(9, 5))
        style.map("TButton", background=[("active", "#29392f"), ("pressed", "#29392f")], foreground=[("disabled", MUTED)])
        style.configure("Vertical.TScrollbar", background=WHITE, troughcolor=DARK, bordercolor=LINE, arrowcolor=MUTED)

    def _login(self):
        if self.mode == "viewer":
            self.account = Actor("viewer", "Viewer SALAK", "VIEWER")
            return
        if self.use_cases.needs_initial_setup():
            self._setup_supervisor()
        if self.root.winfo_exists():
            self._local_login()

    def _setup_supervisor(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Setup Supervisor · DELIMOLD")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        box = ttk.Frame(dlg, padding=22)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text="Buat akun Supervisor", font=("Segoe UI", 15, "bold"), foreground=INK).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))
        ttk.Label(box, text="Akun pertama disimpan pada database lokal.", foreground=MUTED).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 14))
        fields = {}
        for row, label in enumerate(("Nama akun", "Nama tampilan", "Password (4–12 karakter)", "Ulangi password"), 2):
            ttk.Label(box, text=label).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=5)
            entry = ttk.Entry(box, width=34, show="•" if "Password" in label or "Ulangi" in label else "")
            entry.grid(row=row, column=1, sticky="ew", pady=5)
            fields[label] = entry
        error = tk.StringVar()
        ttk.Label(box, textvariable=error, foreground="#a34739").grid(row=6, column=0, columnspan=2, sticky="w", pady=5)
        def submit():
            username = fields["Nama akun"].get().strip()
            display = fields["Nama tampilan"].get().strip()
            pw = fields["Password (4–12 karakter)"].get()
            again = fields["Ulangi password"].get()
            try:
                if pw != again:
                    raise ValueError("Password belum sama")
                self.use_cases.setup_initial_supervisor(username, display, pw)
                dlg.destroy()
            except Exception as exc:
                error.set(str(exc))
        ttk.Button(box, text="Buat akun", command=submit).grid(row=7, column=1, sticky="e", pady=(9, 0))
        dlg.protocol("WM_DELETE_WINDOW", self.root.destroy)
        dlg.wait_window()

    def _local_login(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Login DELIMOLD")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        box = ttk.Frame(dlg, padding=22)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text="DELI MOLD", font=("Segoe UI", 17, "bold"), foreground=GREEN).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(box, text="Masuk ke data utama TENDERLOIN", foreground=MUTED).grid(row=1, column=0, columnspan=2, sticky="w", pady=(3, 16))
        ttk.Label(box, text="Nama akun").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=5)
        username = ttk.Entry(box, width=32)
        username.grid(row=2, column=1, pady=5)
        ttk.Label(box, text="Password").grid(row=3, column=0, sticky="w", padx=(0, 12), pady=5)
        password = ttk.Entry(box, width=32, show="•")
        password.grid(row=3, column=1, pady=5)
        error = tk.StringVar()
        ttk.Label(box, textvariable=error, foreground="#a34739").grid(row=4, column=0, columnspan=2, sticky="w", pady=5)
        def submit(event=None):
            try:
                self.account = self.use_cases.authenticate(username.get(), password.get(), socket.gethostname())
                dlg.destroy()
            except Exception as exc:
                error.set(str(exc))
                password.delete(0, "end")
                password.focus_set()
        ttk.Button(box, text="Masuk", command=submit).grid(row=5, column=1, sticky="e", pady=(8, 0))
        password.bind("<Return>", submit)
        dlg.protocol("WM_DELETE_WINDOW", self.root.destroy)
        dlg.wait_window()

    def _build(self):
        self.root.title("DELIMOLD · Data Cetakan Ban")
        shell = tk.Frame(self.root, bg=DARK)
        shell.pack(fill="both", expand=True)
        self.sidebar, self.nav_buttons = build_sidebar(shell, self.account.role, self.mode,
                                                       self.collection, self.select_collection,
                                                       self.configure_locations)
        self.main = tk.Frame(shell, bg=DARK)
        self.main.pack(side="left", fill="both", expand=True)
        self.header, self.crumb_label = build_header(self.main, self.account.role, self.mode)
        content = tk.Frame(self.main, bg=DARK)
        content.pack(fill="both", expand=True, padx=20, pady=15)
        tk.Label(content, text="MOLD MANAGEMENT   ·   DESKTOP PORTABLE", bg=DARK, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        self.title_label = tk.Label(content, text="Data Cetakan", bg=DARK, fg=INK, font=("Segoe UI", 20, "normal"))
        self.title_label.pack(anchor="w", pady=(3, 1))
        tk.Label(content, text="Kelola dan telusuri data cetakan dalam satu tempat.", bg=DARK, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        _status_frame, self.connection_label = build_database_status(content, self.mode)
        self.stats_frame = tk.Frame(content, bg=DARK)
        self.stats_frame.pack(fill="x", pady=(0, 12))
        self._make_stats()
        panel = tk.Frame(content, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
        panel.pack(fill="both", expand=True)
        head = tk.Frame(panel, bg=WHITE); head.pack(fill="x", padx=14, pady=(12, 8))
        self.list_label = tk.Label(head, text="Daftar cetakan", bg=WHITE, fg=INK, font=("Segoe UI", 10, "bold"))
        self.list_label.pack(anchor="w")
        tk.Label(head, text="Ekspor dan cetak mengikuti pencarian serta filter yang aktif.", bg=WHITE, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(3, 0))
        self.actions = tk.Frame(panel, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
        self.actions.pack(fill="x")
        self.toolbar_buttons = {}
        self._action_button("＋ Tambah", self.add_record, primary=True)
        self._action_button("↑ Impor Excel", self.import_excel)
        self._action_button("↓ Ekspor Excel", self.export_excel)
        self._action_button("▣ Cetak PDF", self.print_pdf)
        self.readonly_label = tk.Label(self.actions, text="Akses baca-saja", bg="#493c27", fg="#f3d59b", padx=8, pady=5, font=("Segoe UI", 8))
        if self.mode == "viewer" or self.account.role == "VIEWER":
            self._set_readonly()
        self.filters = tk.Frame(panel, bg=WHITE)
        self.filters.pack(fill="x", padx=11, pady=9)
        search_row = tk.Frame(self.filters, bg=WHITE)
        search_row.pack(fill="x", pady=(0, 7))
        ttk.Entry(search_row, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=(0, 7))
        self.search_var.trace_add("write", lambda *_: self._schedule_filter_refresh())
        ttk.Button(search_row, text="Reset filter", command=self.reset_filters).pack(side="right")
        self.filter_fields_frame = tk.Frame(self.filters, bg=WHITE)
        self.filter_fields_frame.pack(fill="x")
        self._build_filters()
        tablebox = tk.Frame(panel, bg=WHITE); tablebox.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tablebox, show="headings", selectmode="browse")
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(tablebox, orient="vertical", command=self.tree.yview); scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<Double-1>", lambda _e: self.edit_record())
        actions_bottom = tk.Frame(panel, bg=WHITE); actions_bottom.pack(fill="x", padx=10, pady=7)
        self.row_action_buttons = []
        if self.mode != "viewer" and self.account.role != "VIEWER":
            b = ttk.Button(actions_bottom, text="Edit", command=self.edit_record); b.pack(side="left", padx=(0, 6)); self.row_action_buttons.append(b)
            self.toggle_button = ttk.Button(actions_bottom, text="Aktif / Nonaktif", command=self.toggle_status); self.toggle_button.pack(side="left", padx=6); self.row_action_buttons.append(self.toggle_button)
            if self.account.role == "SUPERVISOR":
                b = ttk.Button(actions_bottom, text="Hapus", command=self.delete_record); b.pack(side="left", padx=6); self.row_action_buttons.append(b)
        self.row_count = tk.Label(actions_bottom, textvariable=self.status_text, bg=WHITE, fg=MUTED, font=("Segoe UI", 8))
        self.row_count.pack(side="left", padx=9)
        ttk.Label(actions_bottom, text="Baris per halaman").pack(side="right", padx=(6, 0))
        self.page_box = ttk.Combobox(actions_bottom, textvariable=self.page_var, state="readonly", width=7,
                                     values=("25", "50", "100"))
        self.page_box.pack(side="right"); self.page_box.bind("<<ComboboxSelected>>", lambda _e: self._change_page_size())
        self.next_page_button = ttk.Button(actions_bottom, text="Berikutnya ›", command=self.next_page)
        self.next_page_button.pack(side="right", padx=(6, 0))
        self.page_label = ttk.Label(actions_bottom, text="Halaman 1")
        self.page_label.pack(side="right", padx=6)
        self.previous_page_button = ttk.Button(actions_bottom, text="‹ Sebelumnya", command=self.previous_page)
        self.previous_page_button.pack(side="right", padx=(0, 6))
        self.root.after(120000, self.auto_refresh)

    def configure_locations(self):
        dialog = tk.Toplevel(self.root)
        dialog.withdraw()
        updated = None
        try:
            updated = configure_master_paths(dialog, self.base_dir, dict(self.config), force=True)
            if updated:
                self.config.update(updated)
                publish_path = Path(updated["publish_path"])
                self.use_cases.set_publish_path(publish_path)
                self.use_cases.publish_pending(force=True)
                messagebox.showinfo("Lokasi tersimpan",
                                    "Lokasi publikasi SALAK sudah aktif. Perubahan lokasi database berlaku setelah DELIMOLD dibuka kembali.",
                                    parent=self.root)
        except Exception as exc:
            messagebox.showerror("Pengaturan lokasi", str(exc), parent=self.root)
        finally:
            try:
                if dialog.winfo_exists():
                    dialog.destroy()
            except tk.TclError:
                pass

    def _action_button(self, text, command, primary=False):
        if self.mode == "viewer" or (self.account and self.account.role == "VIEWER"):
            if text.startswith("＋") or "Impor" in text:
                return
        if self.collection == "history" and (text.startswith("＋") or "Impor" in text):
            return
        if self.collection == "purchases" and self.account.role != "SUPERVISOR" and (text.startswith("＋") or "Impor" in text):
            return
        button = RoundedToolbarButton(self.actions, text, command, primary=primary)
        button.pack(side="left", padx=(9 if text.startswith("＋") else 0, 6), pady=7)
        key = "add" if text.startswith("＋") else ("import" if "Impor" in text else ("export" if "Ekspor" in text else "print"))
        self.toolbar_buttons[key] = button

    def _set_readonly(self):
        for child in self.actions.winfo_children():
            if "Tambah" in str(child.cget("text")) or "Impor" in str(child.cget("text")):
                child.pack_forget()
        self.readonly_label.pack(side="right", padx=9)

    def _make_stats(self):
        self.stat_values = []
        for i in range(4):
            frame = tk.Frame(self.stats_frame, bg=CARD, highlightbackground=LINE, highlightthickness=1, padx=12, pady=8)
            frame.pack(side="left", fill="x", expand=True, padx=(0 if i == 0 else 8, 0))
            label = tk.Label(frame, text=("Total", "Kode unik", "Aktif", "Nonaktif")[i], bg=CARD, fg=MUTED, font=("Segoe UI", 8))
            label.pack(anchor="w")
            value = tk.Label(frame, text="—", bg=CARD, fg=GREEN, font=("Segoe UI", 18))
            value.pack(anchor="w", pady=(3, 0))
            self.stat_values.append((label, value))

    def select_collection(self, collection):
        self.collection = collection
        self.page_index = 0
        self._page_stats = None
        for key, button in self.nav_buttons.items():
            button.configure(bg=PALE if key == collection else WHITE, fg=INK if key == collection else MUTED)
        self.title_label.configure(text=TABS[collection])
        self.crumb_label.configure(text="DELIMOLD · " + TABS[collection])
        self.list_label.configure(text="Daftar " + TABS[collection].lower())
        for button in getattr(self, "row_action_buttons", []):
            disabled = collection == "history" or (button is getattr(self, "toggle_button", None) and collection == "purchases")
            button.configure(state="disabled" if disabled else "normal")
        self._update_toolbar()
        self._build_filters()
        self.refresh()

    def _build_filters(self):
        for child in self.filter_fields_frame.winfo_children():
            child.destroy()
        self.filter_vars = {}
        self.filter_boxes = {}
        fields = FILTER_FIELDS.get(self.collection, ())
        for index, (field, label) in enumerate(fields):
            cell = tk.Frame(self.filter_fields_frame, bg=WHITE)
            cell.grid(row=index // 4, column=index % 4, sticky="ew", padx=(0, 8), pady=(0, 4))
            self.filter_fields_frame.grid_columnconfigure(index % 4, weight=1)
            tk.Label(cell, text=label, bg=WHITE, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
            variable = tk.StringVar(value="Semua")
            box = ttk.Combobox(cell, textvariable=variable, state="readonly")
            box.pack(fill="x")
            box.bind("<<ComboboxSelected>>", lambda _event: self._filter_changed())
            self.filter_vars[field] = variable
            self.filter_boxes[field] = box
        self._update_filter_choices()

    def _filter_value(self, field, row):
        value = row.get(field, "")
        if field == "patternId" and self.collection == "molds":
            patterns = self.catalog.get("collections", {}).get("patterns", {})
            pattern = patterns.get(str(value), {})
            if not pattern:
                pattern = next((item for item in patterns.values() if item.get("code") == value), {})
            value = pattern.get("code", value)
        if field == "status":
            if self.collection == "purchases":
                return str(value or "").strip()
            return self._status(value)
        if field == "enabled":
            return "Aktif" if value else "Nonaktif"
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return str(value or "").strip()

    def _update_filter_choices(self):
        self.filter_query_maps = {}
        records = self.rows if isinstance(self.rows, dict) else {str(i): row for i, row in enumerate(self.rows)}
        for field, box in self.filter_boxes.items():
            if self.mode == "master" and self.collection not in ("accounts", "history"):
                options = self.use_cases.filter_options(self.account, self.collection, field)
                mapping = {label: value for label, value in options}
                self.filter_query_maps[field] = mapping
                values = sorted(mapping, key=lambda value: value.lower())
            else:
                values = sorted({self._filter_value(field, row) for row in records.values()
                                 if isinstance(row, dict) and self._filter_value(field, row)})
                self.filter_query_maps[field] = {value: value for value in values}
            box.configure(values=("Semua",) + tuple(values))
            if self.filter_vars[field].get() not in ("Semua",) + tuple(values):
                self.filter_vars[field].set("Semua")

    def _selected_filters(self):
        filters = {}
        for field, variable in self.filter_vars.items():
            label = variable.get()
            if label and label != "Semua":
                filters[field] = self.filter_query_maps.get(field, {}).get(label, label)
        return filters

    def _filter_changed(self):
        if self._search_after_id is not None:
            try:
                self.root.after_cancel(self._search_after_id)
            except tk.TclError:
                pass
            self._search_after_id = None
        self.page_index = 0
        self.refresh()

    def _schedule_filter_refresh(self):
        if self._search_after_id is not None:
            try:
                self.root.after_cancel(self._search_after_id)
            except tk.TclError:
                pass
        self._search_after_id = self.root.after(250, self._filter_changed)

    def _change_page_size(self):
        self.page_index = 0
        self.refresh()

    def next_page(self):
        if (self.page_index + 1) * int(self.page_var.get()) < self.page_total:
            self.page_index += 1
            self.refresh()

    def previous_page(self):
        if self.page_index > 0:
            self.page_index -= 1
            self.refresh()

    def _update_toolbar(self):
        can_edit = self.mode != "viewer" and self.account.role != "VIEWER" and self.collection != "history"
        if self.collection == "purchases" and self.account.role != "SUPERVISOR":
            can_edit = False
        # Re-pack every visible action in one fixed order. Buttons can be hidden
        # and restored when the user changes collections; relying on Tk's old
        # pack order made restored actions jump to the end of the toolbar.
        for button in self.toolbar_buttons.values():
            button.pack_forget()
        for key in ("add", "import", "export", "print"):
            button = self.toolbar_buttons.get(key)
            if button is None:
                continue
            allowed = can_edit if key in ("add", "import") else True
            if allowed:
                button.pack(side="left", padx=(9 if key == "add" else 0, 6), pady=7)

    def _fetch_catalog(self):
        if self.mode == "master":
            return self.use_cases.catalog(self.account)
        return self.use_cases.published_catalog(self.config["snapshot_path"])

    def refresh(self):
        try:
            if self.mode == "master" and self.collection not in ("accounts", "history"):
                limit = int(self.page_var.get() or "50")
                offset = self.page_index * limit
                page_data = self.use_cases.catalog_page(
                    self.account, self.collection, offset, limit,
                    self.search_var.get().strip(), self._selected_filters())
                self.rows = page_data["rows"]
                self.catalog = {"collections": {self.collection: self.rows}}
                self.catalog["collections"].update(page_data["lookups"])
                self._page_stats = page_data["stats"]
                self.page_total = self._page_stats["total"]
                max_page = max((self.page_total - 1) // limit, 0)
                self.page_index = min(self.page_index, max_page)
                if offset != self.page_index * limit:
                    return self.refresh()
            elif self.collection == "accounts":
                self.rows = self.use_cases.list_users(self.account)
            elif self.collection == "history":
                history = self.use_cases.audit_rows(self.account)
                self.rows = {str(row.get("id", i)): row for i, row in enumerate(history)}
            else:
                self.catalog = self._fetch_catalog()
                self.rows = self.catalog.get("collections", {}).get(self.collection, {})
            self.connection_label.configure(text="Salinan baca-saja · publikasi SALAK" if self.mode == "viewer" else ("Data utama · TENDERLOIN" if self.mode == "master" else "Terhubung · TENDERLOIN"))
            self._update_stats()
            self.refresh_table()
        except Exception as exc:
            self.status_text.set("Gagal memuat data: %s" % exc)
            messagebox.showerror("Koneksi DELIMOLD", "Data tidak dapat dimuat.\n\n%s" % exc, parent=self.root)

    def _update_stats(self):
        if self._page_stats and self.mode == "master" and self.collection not in ("accounts", "history"):
            labels = {"molds": ("Daftar cetakan", "Kode spesifikasi", "Cetakan aktif", "Nonaktif"),
                      "containers": ("Total container", "Kode container", "Aktif", "Nonaktif"),
                      "patterns": ("Total pattern", "Kode pattern", "Aktif", "Nonaktif"),
                      "stickers": ("Total sticker", "Nama sticker", "Aktif", "Nonaktif"),
                      "projects": ("Total project", "Kode spek", "Aktif", "Nonaktif"),
                      "purchases": ("Total pembelian", "Kode spek", "Diajukan", "Diterima")}.get(self.collection)
            values = (self._page_stats["total"], self._page_stats["unique"],
                      self._page_stats["active"], self._page_stats["inactive"])
            for (label, value), name, number in zip(self.stat_values, labels, values):
                label.configure(text=name); value.configure(text=str(number))
            return
        records = list(self.rows.values()) if isinstance(self.rows, dict) else list(self.rows)
        status_values = [str(item.get("status", "active")).lower() for item in records if isinstance(item, dict)]
        active = sum(1 for status in status_values if status in ("active", "aktif"))
        inactive = len(status_values) - active
        if self.collection == "molds":
            unique = len(set(str(row.get("spec", "")) for row in records if isinstance(row, dict)))
            labels = ("Daftar cetakan", "Kode spesifikasi", "Cetakan aktif", "Nonaktif")
        elif self.collection == "containers":
            unique = len(set(str(row.get("code", "")) for row in records if isinstance(row, dict)))
            labels = ("Total container", "Kode container", "Aktif", "Nonaktif")
        elif self.collection == "patterns":
            unique = len(set(str(row.get("code", "")) for row in records if isinstance(row, dict)))
            labels = ("Total pattern", "Kode pattern", "Aktif", "Nonaktif")
        elif self.collection == "stickers":
            unique = len(set(str(row.get("name", "")) for row in records if isinstance(row, dict)))
            labels = ("Total sticker", "Nama sticker", "Aktif", "Nonaktif")
        elif self.collection == "projects":
            unique = len(set(str(row.get("spec", "")) for row in records if isinstance(row, dict)))
            labels = ("Total project", "Kode spek", "Aktif", "Nonaktif")
        elif self.collection == "purchases":
            unique = len(set(str(row.get("spec", "")) for row in records if isinstance(row, dict)))
            active = sum(1 for row in records if isinstance(row, dict) and row.get("status") == "Diajukan")
            inactive = sum(1 for row in records if isinstance(row, dict) and row.get("status") == "Diterima")
            labels = ("Total pembelian", "Kode spek", "Diajukan", "Diterima")
        elif self.collection == "accounts":
            unique = len(set(str(row.get("role", "")) for row in records if isinstance(row, dict)))
            active = sum(1 for row in records if isinstance(row, dict) and row.get("enabled"))
            inactive = len(records) - active
            labels = ("Total akun", "Peran", "Aktif", "Nonaktif")
        else:
            unique = len(set(str(row.get("collection", "")) for row in records if isinstance(row, dict)))
            active = sum(1 for row in records if isinstance(row, dict) and row.get("action") == "create")
            inactive = sum(1 for row in records if isinstance(row, dict) and row.get("action") in ("edit", "delete"))
            labels = ("Total perubahan", "Jenis data", "Dibuat", "Diedit / hapus")
        values = (len(records), unique, active, inactive)
        for (label, value), name, number in zip(self.stat_values, labels, values):
            label.configure(text=name); value.configure(text=str(number))

    def refresh_table(self):
        if not hasattr(self, "tree"):
            return
        records = self.rows if isinstance(self.rows, dict) else {str(i): value for i, value in enumerate(self.rows)}
        database_paged = self.mode == "master" and self.collection not in ("accounts", "history")
        if database_paged:
            mapped = [(key, row, self._display_values(key, row)) for key, row in records.items()
                      if isinstance(row, dict)]
            self.filtered = mapped
            limit = int(self.page_var.get() or "50")
            page = mapped
            total = self.page_total
            offset = self.page_index * limit
        else:
            self._update_filter_choices()
            mapped = []
            for key, row in records.items():
                if not isinstance(row, dict):
                    continue
                values = self._display_values(key, row)
                haystack = " ".join(str(v) for v in values).lower()
                query = self.search_var.get().strip().lower()
                if query and query not in haystack:
                    continue
                if any(variable.get() != "Semua" and self._filter_value(field, row) != variable.get()
                       for field, variable in self.filter_vars.items()):
                    continue
                mapped.append((key, row, values))
            self.filtered = mapped
            limit = int(self.page_var.get() or "50")
            total = len(mapped)
            self.page_total = total
            offset = self.page_index * limit
            page = mapped[offset:offset + limit]
        columns = self._columns()
        self.tree.configure(columns=columns)
        for col, title in zip(columns, self._column_titles()):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=120, minwidth=75, stretch=True, anchor="w")
        self.tree.delete(*self.tree.get_children())
        for key, row, values in page:
            self.tree.insert("", "end", iid=str(key), values=values)
        first = offset + 1 if total else 0
        last = offset + len(page)
        self.status_text.set("Menampilkan %s–%s dari %s data" % (first, last, total))
        pages = max((total + limit - 1) // limit, 1)
        self.page_label.configure(text="Halaman %s dari %s" % (self.page_index + 1, pages))
        self.previous_page_button.configure(state="normal" if self.page_index > 0 else "disabled")
        self.next_page_button.configure(state="normal" if self.page_index + 1 < pages else "disabled")

    def _columns(self):
        return {"molds": ("code", "size", "pattern", "serial", "cure", "mtype", "status", "container"),
                "containers": ("code", "serial", "od", "sw", "spacers", "status"),
                "patterns": ("code", "name", "land", "status"),
                "stickers": ("name", "status"),
                "projects": ("spec", "name", "projectId", "status", "targetDays"),
                "purchases": ("date", "spec", "size", "pattern", "moldNumber", "quantity", "supplier", "currency", "price", "status"),
                "accounts": ("username", "display_name", "role", "enabled"),
                "history": ("at", "action", "collection", "record_key", "username", "computer", "reason")} [self.collection]

    def _column_titles(self):
        return {"molds": ("KODE SPEK", "SIZE CETAKAN", "PATTERN", "NO. CETAKAN", "TIPE MASAK", "TIPE CETAKAN", "STATUS", "CONTAINER"),
                "containers": ("KODE CONTAINER", "NO.", "OD SECTOR", "SW SECTOR", "SPACER", "STATUS"),
                "patterns": ("KODE PATTERN", "NAMA", "LAND", "STATUS"),
                "stickers": ("NAMA STICKER", "STATUS"),
                "projects": ("KODE SPEK", "PROJECT", "ID PROJECT", "STATUS", "TARGET HARI"),
                "purchases": ("TANGGAL", "KODE SPEK", "SIZE", "PATTERN", "NO. MOLD", "JUMLAH", "SUPPLIER", "MATA UANG", "HARGA SATUAN", "STATUS"),
                "accounts": ("NAMA AKUN", "NAMA TAMPILAN", "PERAN", "AKTIF"),
                "history": ("WAKTU", "AKSI", "DATA", "ID", "AKUN", "KOMPUTER", "ALASAN")} [self.collection]

    def _display_values(self, key, row):
        if self.collection == "molds":
            patterns = self.catalog.get("collections", {}).get("patterns", {})
            containers = self.catalog.get("collections", {}).get("containers", {})
            pattern = patterns.get(str(row.get("patternId", "")), {})
            if not pattern:
                pattern = next((item for item in patterns.values() if item.get("code") == row.get("patternId")), {})
            container = containers.get(str(row.get("containerId", "")), {})
            if not container:
                container = next((item for item in containers.values() if item.get("code") == row.get("containerId")), {})
            return (row.get("spec", ""), row.get("size", ""), pattern.get("code", row.get("patternId", "")), row.get("serial", ""),
                    row.get("cure", ""), row.get("mtype", ""), self._status(row.get("status")), container.get("code", row.get("containerId", "")))
        if self.collection == "containers":
            return (row.get("code", ""), row.get("serial", ""), row.get("od", ""), row.get("sw", ""), json.dumps(row.get("spacers", []), ensure_ascii=False), self._status(row.get("status")))
        if self.collection == "patterns":
            return (row.get("code", ""), row.get("name", ""), row.get("land", ""), self._status(row.get("status")))
        if self.collection == "stickers":
            return (row.get("name", ""), self._status(row.get("status")))
        if self.collection == "projects":
            return (row.get("spec", ""), row.get("name", ""), row.get("projectId", key), self._status(row.get("status")), row.get("targetDays", ""))
        if self.collection == "purchases":
            return tuple(row.get(col, "") for col in self._columns())
        if self.collection == "accounts":
            return (key, row.get("display_name", ""), row.get("role", ""), "Aktif" if row.get("enabled") else "Nonaktif")
        if self.collection == "history":
            return tuple(row.get(col, "") for col in self._columns())
        return (row.get("code", key), row.get("name", ""), self._status(row.get("status")))

    @staticmethod
    def _status(value):
        return "Aktif" if str(value or "active").lower() in ("active", "aktif") else "Nonaktif"

    def reset_filters(self):
        self.search_var.set("")
        for variable in self.filter_vars.values():
            variable.set("Semua")
        self._filter_changed()

    def _selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Pilih data", "Pilih satu baris terlebih dahulu.", parent=self.root)
            return None
        key = selection[0]
        return key, self.rows.get(key) if isinstance(self.rows, dict) else None

    def add_record(self):
        if self.collection == "accounts":
            self._account_form(None, None)
            return
        self._record_form(None, None)

    def edit_record(self):
        selected = self._selected()
        if selected:
            if self.collection == "accounts":
                self._account_form(selected[0], selected[1])
            elif self.collection != "history":
                self._record_form(selected[0], selected[1])

    def _account_form(self, username, record):
        if self.account.role != "SUPERVISOR":
            return
        dlg = tk.Toplevel(self.root); dlg.title("Tambah akun" if username is None else "Edit akun"); dlg.transient(self.root); dlg.grab_set(); dlg.resizable(False, False)
        box = ttk.Frame(dlg, padding=20); box.pack(fill="both", expand=True)
        ttk.Label(box, text="Tambah akun" if username is None else "Edit akun", font=("Segoe UI", 15, "bold"), foreground=INK).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))
        labels = ("Nama akun", "Nama tampilan", "Peran", "Password baru (4–12 karakter; kosong = tetap)")
        values = [username or "", (record or {}).get("display_name", ""), (record or {}).get("role", "ENGINEER"), ""]
        widgets = []
        for i, label in enumerate(labels):
            ttk.Label(box, text=label).grid(row=i+1, column=0, sticky="w", padx=(0, 12), pady=6)
            if i == 2:
                widget = ttk.Combobox(box, values=("SUPERVISOR", "ENGINEER", "VIEWER"), state="readonly", width=35)
                widget.set(values[i])
            else:
                widget = ttk.Entry(box, width=38, show="•" if i == 3 else "")
                widget.insert(0, values[i])
                if i == 0 and username:
                    widget.configure(state="readonly")
            widget.grid(row=i+1, column=1, sticky="ew", pady=6); widgets.append(widget)
        error = tk.StringVar(); ttk.Label(box, textvariable=error, foreground="#a34739").grid(row=5, column=0, columnspan=2, sticky="w")
        actions = ttk.Frame(box); actions.grid(row=6, column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(actions, text="Batal", command=dlg.destroy).pack(side="left", padx=5)
        def save():
            name = widgets[0].get().strip(); display = widgets[1].get().strip() or name; role = widgets[2].get(); password = widgets[3].get()
            try:
                if not name: raise ValueError("Nama akun wajib diisi")
                self.use_cases.save_user(self.account, name, display, role, password,
                                         enabled=(record or {}).get("enabled", True),
                                         existing=bool(username))
                dlg.destroy(); self.refresh()
            except Exception as exc: error.set(str(exc))
        ttk.Button(actions, text="Simpan", command=save).pack(side="left", padx=5)
        dlg.wait_window()

    def _record_form(self, key, record):
        if not self._can_write():
            return
        dlg = tk.Toplevel(self.root); dlg.title(("Edit " if key else "Tambah ") + TABS[self.collection]); dlg.transient(self.root); dlg.grab_set()
        dlg.geometry("560x640")
        outer = ttk.Frame(dlg, padding=18); outer.pack(fill="both", expand=True)
        ttk.Label(outer, text=("Edit " if key else "Tambah ") + TABS[self.collection], font=("Segoe UI", 15, "bold"), foreground=INK).pack(anchor="w")
        form = ttk.Frame(outer); form.pack(fill="both", expand=True, pady=12)
        entries = {}
        choice_maps = {}
        defaults = {}
        if not record and self.collection == "purchases":
            defaults = {"date": time.strftime("%Y-%m-%d"), "quantity": 1, "currency": "USD", "status": "Diajukan"}
        elif not record and self.collection == "molds":
            defaults = {"serial": "01", "mtype": "2piece", "role": "main", "status": "active"}

        def mold_choices(field, current):
            catalog = self.catalog.get("collections", {})
            if field == "patternId":
                source = catalog.get("patterns", {})
                result = {"Pilih pattern": ""}
                for item_key, item in source.items():
                    label = "%s · %s" % (item.get("code", item_key), item.get("name", ""))
                    result[label] = item_key
                return result
            if field == "containerId":
                source = catalog.get("containers", {})
                result = {"Pilih container": ""}
                for item_key, item in source.items():
                    label = "%s · No. %s · OD/SW %s/%s" % (item.get("code", item_key), item.get("serial", ""), item.get("od", ""), item.get("sw", ""))
                    result[label] = item_key
                return result
            if field == "mainId":
                source = catalog.get("molds", {})
                result = {"Pilih main size": ""}
                for item_key, item in source.items():
                    if item_key != key and item.get("mtype") == "segmented" and item.get("role") in ("main", "sharing"):
                        label = "%s/%s · %s" % (item.get("spec", ""), item.get("serial", ""), item.get("size", ""))
                        result[label] = item_key
                return result
            if field == "spacer":
                result = {"Tanpa spacer": ""}
                container_id = (record or {}).get("containerId", "")
                container = catalog.get("containers", {}).get(str(container_id), {})
                for spacer in container.get("spacers", []) or []:
                    size = spacer.get("size", "")
                    result["%s mm · OD sector %s" % (size, spacer.get("od", ""))] = str(size)
                return result
            options = {"cure": (("Pilih tipe masak", ""), ("BOM", "BOM"), ("Airbag", "Airbag")),
                       "mtype": (("2 Piece", "2piece"), ("Segmented", "segmented")),
                       "role": (("Main size", "main"), ("Sharing size", "sharing")),
                       "status": (("Aktif", "active"), ("Nonaktif (tidak bisa dipakai)", "inactive"))}
            return {label: value for label, value in options.get(field, ())}

        for index, (field, label) in enumerate(FIELDS.get(self.collection, [])):
            ttk.Label(form, text=label).grid(row=index, column=0, sticky="nw", padx=(0, 10), pady=5)
            if self.collection == "molds" and field in ("patternId", "containerId", "spacer", "cure", "mtype", "role", "mainId", "status"):
                current = (record or {}).get(field, defaults.get(field, ""))
                mapping = mold_choices(field, current)
                labels = list(mapping)
                widget = ttk.Combobox(form, width=46, state="readonly", values=labels)
                widget.grid(row=index, column=1, sticky="ew", pady=4)
                selected = next((name for name, choice in mapping.items() if str(choice) == str(current)), "")
                if not selected and field == "status": selected = "Aktif"
                if not selected and field == "mtype" and not record: selected = "2 Piece"
                if not selected and field == "role" and not record: selected = "Main size"
                if not selected and field == "spacer": selected = "Tanpa spacer"
                if not selected and field == "mainId": selected = "Pilih main size"
                if selected: widget.set(selected)
                choice_maps[field] = mapping
            elif self.collection == "purchases" and field == "currency":
                widget = ttk.Combobox(form, width=46, state="readonly", values=("USD", "RMB", "IDR"))
                widget.grid(row=index, column=1, sticky="ew", pady=4)
                widget.set((record or {}).get(field, defaults.get(field, "USD")))
            elif self.collection == "purchases" and field == "status":
                widget = ttk.Combobox(form, width=46, state="readonly", values=("Diajukan", "Dipesan", "Proses Pembuatan", "Selesai", "Diterima"))
                widget.grid(row=index, column=1, sticky="ew", pady=4)
                widget.set((record or {}).get(field, defaults.get(field, "Diajukan")))
            elif field in ("note", "spacers"):
                widget = tk.Text(form, height=3 if field == "note" else 2, width=44, font=("Segoe UI", 9), wrap="word")
                widget.grid(row=index, column=1, sticky="ew", pady=4)
                value = (record or {}).get(field, defaults.get(field, "active" if field == "status" else ""))
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                widget.insert("1.0", value)
            else:
                widget = ttk.Entry(form, width=48)
                widget.grid(row=index, column=1, sticky="ew", pady=4)
                value = (record or {}).get(field, defaults.get(field, "active" if field == "status" else ""))
                if field == "brands" and isinstance(value, list):
                    value = ", ".join(str(item.get("brand", "")) for item in value if isinstance(item, dict))
                elif isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False)
                widget.insert(0, str(value))
            entries[field] = widget
        if self.collection == "molds" and "containerId" in entries and "spacer" in entries:
            def refresh_spacer_choices(_event=None):
                container_key = choice_maps["containerId"].get(entries["containerId"].get(), "")
                container = self.catalog.get("collections", {}).get("containers", {}).get(str(container_key), {})
                spacer_map = {"Tanpa spacer": ""}
                for spacer in container.get("spacers", []) or []:
                    size = spacer.get("size", "")
                    spacer_map["%s mm · OD sector %s" % (size, spacer.get("od", ""))] = str(size)
                previous = choice_maps.get("spacer", {}).get(entries["spacer"].get(), "")
                choice_maps["spacer"] = spacer_map
                entries["spacer"].configure(values=list(spacer_map))
                selected = next((name for name, size in spacer_map.items() if str(size) == str(previous)), "Tanpa spacer")
                entries["spacer"].set(selected)
            entries["containerId"].bind("<<ComboboxSelected>>", refresh_spacer_choices, add="+")
        form.columnconfigure(1, weight=1)
        error = tk.StringVar()
        ttk.Label(outer, textvariable=error, foreground="#a34739").pack(anchor="w")
        buttons = ttk.Frame(outer); buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Batal", command=dlg.destroy).pack(side="right", padx=(7, 0))
        def save():
            try:
                value = {}
                for field, widget in entries.items():
                    content = widget.get("1.0", "end-1c") if isinstance(widget, tk.Text) else widget.get()
                    if field == "spacers" and content.strip():
                        content = json.loads(content)
                    elif field == "brands":
                        old = [dict(item) for item in (record or {}).get("brands", []) if isinstance(item, dict)]
                        updated = []
                        for name in content.split(","):
                            name = name.strip()
                            if not name: continue
                            match = next((item for item in old if str(item.get("brand", "")).strip().lower() == name.lower()), None)
                            if match:
                                old.remove(match); match["brand"] = name; updated.append(match)
                            else:
                                updated.append(dict(brand=name, insert="", stickerId=""))
                        content = updated
                    elif field in ("land", "od", "sw") and content.strip():
                        try: content = float(content)
                        except ValueError: pass
                    if field in choice_maps:
                        content = choice_maps[field].get(content, content)
                    if self.collection == "molds" and field == "spacer" and content not in ("", None):
                        content = float(content) if "." in str(content) else int(content)
                    value[field] = content
                if self.collection == "purchases":
                    if not re.match(r"^\d{4}-\d\d-\d\d$", str(value.get("date", ""))):
                        raise ValueError("Tanggal pembelian harus YYYY-MM-DD")
                    if value.get("poReceivedDate") and not re.match(r"^\d{4}-\d\d-\d\d$", str(value["poReceivedDate"])):
                        raise ValueError("Tanggal PO diterima harus YYYY-MM-DD atau kosong")
                    if not value.get("spec") or not value.get("size"):
                        raise ValueError("Kode spek dan size ban wajib diisi")
                    try:
                        quantity = int(value.get("quantity", 0))
                        price = float(value.get("price", ""))
                    except (TypeError, ValueError):
                        raise ValueError("Jumlah mold dan harga satuan harus berupa angka")
                    if quantity < 1 or price < 0 or not re.match(r"^\d+(\.\d{1,2})?$", str(value.get("price", ""))):
                        raise ValueError("Jumlah mold minimal 1 dan harga maksimal dua angka desimal")
                    if value.get("currency") not in ("USD", "RMB", "IDR"):
                        raise ValueError("Pilih mata uang USD, RMB, atau IDR")
                    value["quantity"] = quantity
                if self.collection == "molds":
                    missing = [label for field, label in (("spec", "kode spek"), ("size", "size"),
                              ("patternId", "pattern"), ("serial", "nomor cetakan"), ("cure", "tipe masak")) if not value.get(field)]
                    if missing:
                        raise ValueError("Wajib diisi: %s" % ", ".join(missing))
                    if record and str(value.get("status", "active")) != str(record.get("status", "active")):
                        reason = str(value.get("statusReason", "")).strip()
                        old_reason = str(record.get("statusReason", "")).strip()
                        if not reason or reason == old_reason:
                            raise ValueError("Isi alasan baru untuk perubahan status cetakan")
                # Keep v12 fields this form does not edit (for example mold
                # sharing links, container IDs, and print metadata).
                value = dict(record or {}, **value)
                if self.collection == "molds":
                    value.setdefault("brands", record.get("brands", []) if record else [])
                    value.setdefault("statusReason", "")
                value.setdefault("status", "active")
                record_key = key or self._new_record_key(value)
                if self.collection == "purchases":
                    value.setdefault("id", record_key)
                self.use_cases.save_record(self.account, self.collection, record_key, value,
                                           "edit" if key else "create")
                dlg.destroy(); self.refresh()
            except Exception as exc:
                error.set(str(exc))
        ttk.Button(buttons, text="Simpan", command=save).pack(side="right")

    def toggle_status(self):
        selected = self._selected()
        if not selected or not self._can_write():
            return
        key, row = selected
        if self.collection == "accounts":
            enabled = not bool(row.get("enabled"))
            try:
                self.use_cases.set_user_enabled(self.account, key, enabled)
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Status akun gagal diubah", str(exc), parent=self.root)
            return
        current = str(row.get("status", "active")).lower()
        new_status = "inactive" if current in ("active", "aktif") else "active"
        reason = simpledialog.askstring("Alasan perubahan status", "Masukkan alasan %s:" % ("menonaktifkan" if new_status == "inactive" else "mengaktifkan"), parent=self.root)
        if reason is None:
            return
        if not reason.strip():
            messagebox.showwarning("Alasan wajib", "Masukkan alasan perubahan status.", parent=self.root)
            return
        value = dict(row); value["status"] = new_status; value["statusReason"] = reason.strip()
        self._save(value, key, "status", reason.strip())

    def delete_record(self):
        selected = self._selected()
        if not selected or self.account.role != "SUPERVISOR":
            return
        key, row = selected
        if self.collection == "accounts":
            if key == self.account.username:
                messagebox.showwarning("Tidak dapat menghapus", "Akun yang sedang dipakai tidak dapat dihapus.", parent=self.root); return
            if not messagebox.askyesno("Hapus akun", "Hapus akun %s?" % key, parent=self.root): return
            try:
                self.use_cases.delete_user(self.account, key)
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Akun gagal dihapus", str(exc), parent=self.root)
            return
        if not messagebox.askyesno("Konfirmasi hapus", "Hapus data ini? Tindakan ini dicatat di riwayat.", parent=self.root):
            return
        try:
            self.use_cases.delete_record(self.account, self.collection, key, "hapus oleh Supervisor")
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Data gagal dihapus", str(exc), parent=self.root)

    def _save(self, value, key, action, reason=""):
        try:
            self.use_cases.save_record(self.account, self.collection, key, value, action, reason)
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Gagal menyimpan", str(exc), parent=self.root)

    def _new_record_key(self, value):
        if self.collection == "patterns" and value.get("code"):
            return str(value["code"])
        if self.collection == "containers" and value.get("code"):
            return "%s-%s" % (value.get("code"), value.get("serial", "01"))
        return "%s_%s" % (self.collection[:1], uuid4().hex[:20])

    def _can_write(self):
        if self.mode == "viewer" or self.account.role == "VIEWER":
            messagebox.showinfo("Baca-saja", "Akun ini hanya dapat melihat data.", parent=self.root)
            return False
        if self.collection == "purchases" and self.account.role != "SUPERVISOR":
            messagebox.showinfo("Akses terbatas", "Data pembelian hanya dapat diakses Supervisor.", parent=self.root)
            return False
        if self.collection == "history":
            return False
        return True

    def import_excel(self):
        if not self._can_write():
            return
        dlg = tk.Toplevel(self.root); dlg.title("Impor Excel DELIMOLD"); dlg.transient(self.root); dlg.grab_set(); dlg.resizable(False, False)
        box = ttk.Frame(dlg, padding=18); box.pack(fill="both", expand=True)
        ttk.Label(box, text="Impor / Template Excel", font=("Segoe UI", 14, "bold"), foreground=INK).pack(anchor="w")
        ttk.Label(box, text="Buat template sesuai tab yang terbuka, atau pilih workbook untuk diperiksa.", foreground=MUTED).pack(anchor="w", pady=(5, 14))
        ttk.Button(box, text="Simpan Template Excel", command=lambda: (dlg.destroy(), self._save_template())).pack(fill="x", pady=4)
        ttk.Button(box, text="Pilih Excel untuk Diimpor", command=lambda: (dlg.destroy(), self._open_import_file())).pack(fill="x", pady=4)
        ttk.Button(box, text="Batal", command=dlg.destroy).pack(anchor="e", pady=(10, 0))

    def _save_template(self):
        path = filedialog.asksaveasfilename(parent=self.root, title="Simpan template DELIMOLD", defaultextension=".xlsx",
                                            initialfile="Template-DELIMOLD-%s.xlsx" % self.collection,
                                            filetypes=(("Workbook Excel", "*.xlsx"),))
        if not path: return
        try:
            self.use_cases.write_excel_template(self.account, self.collection, path,
                                                 [label for _, label in FIELDS.get(self.collection, [])])
            messagebox.showinfo("Template tersimpan", "Isi baris data di bawah judul kolom, lalu impor kembali.", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Gagal membuat template", str(exc), parent=self.root)

    def _open_import_file(self):
        path = filedialog.askopenfilename(parent=self.root, title="Pilih workbook Excel DELIMOLD", filetypes=(("Workbook Excel", "*.xlsx"),))
        if not path: return
        try:
            values = self.use_cases.read_excel_rows(self.account, self.collection, path)
            if len(values) < 2:
                messagebox.showwarning("Template kosong", "Workbook belum berisi baris data.", parent=self.root); return
            aliases = {field.lower(): field for field, _label in FIELDS.get(self.collection, [])}
            aliases.update({label.lower(): field for field, label in FIELDS.get(self.collection, [])})
            aliases.update({"kode spek": "spec", "nomor cetakan": "serial", "size cetakan": "size",
                            "tipe cetakan": "mtype", "tipe masak": "cure", "kode pattern": "code",
                            "kode container": "code", "kode sticker": "code", "nomor container": "serial",
                            "kategori": "category", "merek": "brands", "main / sharing": "role",
                            "tanggal": "date", "tanggal pembelian": "date", "po diterima": "poReceivedDate",
                            "nomor mold": "moldNumber", "jumlah": "quantity", "mata uang": "currency",
                            "harga satuan": "price"})
            headers = [re.sub(r"\s+", " ", str(value or "").strip().lower()) for value in values[0]]
            mapping = [(i, aliases.get(name)) for i, name in enumerate(headers)]
            mapping = [(i, field) for i, field in mapping if field]
            if not mapping:
                raise ValueError("Judul kolom tidak cocok dengan template DELIMOLD")
            mapped_fields = set(field for _index, field in mapping)
            required = {"molds": ("spec", "size", "serial"), "containers": ("code", "serial"),
                        "patterns": ("code",), "stickers": ("name",),
                        "projects": ("spec", "name"),
                        "purchases": ("date", "spec", "size", "quantity", "currency", "price", "status")}.get(self.collection, ())
            missing = [field for field in required if field not in mapped_fields]
            if missing:
                raise ValueError("Template belum memiliki kolom wajib: %s" % ", ".join(missing))
            records = []
            invalid = []
            for line_no, cells in enumerate(values[1:], 2):
                item = {field: (cells[index] if index < len(cells) else "") for index, field in mapping}
                normalized = {}
                for field, value in item.items():
                    if value is None:
                        normalized[field] = ""
                    elif hasattr(value, "strftime"):
                        normalized[field] = value.strftime("%Y-%m-%d")
                    elif field == "quantity" and isinstance(value, float) and value.is_integer():
                        normalized[field] = str(int(value))
                    else:
                        normalized[field] = str(value).strip()
                item = normalized
                if not any(item.values()): continue
                empty_required = [field for field in required if not item.get(field)]
                if empty_required:
                    invalid.append("Baris %s: kosong %s" % (line_no, ", ".join(empty_required)))
                    continue
                if self.collection == "molds" and item.get("brands"):
                    item["brands"] = [dict(brand=name.strip(), insert="", stickerId="") for name in item["brands"].split(",") if name.strip()]
                item.setdefault("status", "Diajukan" if self.collection == "purchases" else "active")
                if self.collection == "purchases":
                    item.setdefault("currency", "USD")
                    try:
                        item["quantity"] = int(item["quantity"])
                        float(item["price"])
                        if item["quantity"] < 1 or float(item["price"]) < 0:
                            raise ValueError()
                    except (TypeError, ValueError):
                        invalid.append("Baris %s: jumlah mold atau harga satuan tidak valid" % line_no)
                        continue
                    if not re.match(r"^\d{4}-\d\d-\d\d$", item["date"]):
                        invalid.append("Baris %s: tanggal harus YYYY-MM-DD" % line_no)
                        continue
                if item.get("status", "").lower() in ("aktif", "active"): item["status"] = "active"
                elif item.get("status", "").lower() in ("nonaktif", "inactive"): item["status"] = "inactive"
                if self.collection == "molds": item.setdefault("brands", [])
                records.append((line_no, item))
            if invalid:
                raise ValueError("Data wajib belum lengkap:\n%s%s" % ("\n".join(invalid[:12]), "\n…" if len(invalid) > 12 else ""))
            if not records:
                messagebox.showwarning("Tidak ada data", "Tidak ditemukan baris data untuk diimpor.", parent=self.root); return
            self._preview_import(records)
        except Exception as exc:
            messagebox.showerror("Gagal membaca Excel", str(exc), parent=self.root)

    def _preview_import(self, records):
        dlg = tk.Toplevel(self.root); dlg.title("Pratinjau impor Excel"); dlg.transient(self.root); dlg.grab_set(); dlg.geometry("900x520")
        panel = ttk.Frame(dlg, padding=16); panel.pack(fill="both", expand=True)
        ttk.Label(panel, text="Periksa data sebelum impor", font=("Segoe UI", 15, "bold"), foreground=INK).pack(anchor="w")
        ttk.Label(panel, text="%s baris terbaca. Belum ada data yang disimpan." % len(records), foreground=MUTED).pack(anchor="w", pady=(3, 12))
        columns = self._columns(); headings = self._column_titles()
        table = ttk.Treeview(panel, columns=columns, show="headings", height=14)
        for column, heading in zip(columns, headings):
            table.heading(column, text=heading); table.column(column, width=130, minwidth=85, stretch=True)
        table.pack(fill="both", expand=True)
        for line_no, item in records[:200]:
            table.insert("", "end", values=self._import_display(item)[:len(columns)])
        if len(records) > 200:
            ttk.Label(panel, text="Tampilan menampilkan 200 baris pertama; impor mencakup semua baris.", foreground=MUTED).pack(anchor="w", pady=5)
        error = tk.StringVar(); ttk.Label(panel, textvariable=error, foreground="#a34739").pack(anchor="w")
        buttons = ttk.Frame(panel); buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Batal", command=dlg.destroy).pack(side="right", padx=5)
        def commit():
            try:
                batch = [(self._new_record_key(item), item) for _line_no, item in records]
                if self.collection == "purchases":
                    for key, item in batch:
                        item.setdefault("id", key)
                self.use_cases.save_records(self.account, self.collection, batch, "import")
                dlg.destroy(); self.refresh()
                messagebox.showinfo("Impor selesai", "%s baris berhasil ditambahkan." % len(records), parent=self.root)
            except Exception as exc:
                error.set("Impor berhenti: %s" % exc)
        ttk.Button(buttons, text="Impor %s baris" % len(records), command=commit).pack(side="right", padx=5)

    def _import_display(self, item):
        if self.collection == "molds":
            return (item.get("spec", ""), item.get("size", ""), item.get("patternId", ""), item.get("serial", ""), item.get("cure", ""), item.get("mtype", ""), self._status(item.get("status")), item.get("containerId", ""))
        if self.collection == "containers": return tuple(item.get(k, "") for k in ("code", "serial", "od", "sw", "spacers", "status"))
        if self.collection == "patterns": return tuple(item.get(k, "") for k in ("code", "name", "land", "status"))
        if self.collection == "stickers": return tuple(item.get(k, "") for k in ("name", "status"))
        if self.collection == "projects": return tuple(item.get(k, "") for k in ("spec", "name", "projectId", "status", "targetDays"))
        return tuple(item.get(k, "") for k in self._columns())

    def _export_view_rows(self):
        if self.mode != "master" or self.collection in ("accounts", "history"):
            return self.filtered
        result = self.use_cases.catalog_export(self.account, self.collection,
                                               self.search_var.get().strip(), self._selected_filters())
        original_catalog = self.catalog
        self.catalog = {"collections": result["lookups"]}
        try:
            return [(key, row, self._display_values(key, row)) for key, row in result["rows"].items()]
        finally:
            self.catalog = original_catalog

    def export_excel(self):
        path = filedialog.asksaveasfilename(parent=self.root, title="Ekspor hasil saat ini", defaultextension=".xlsx", initialfile="DELIMOLD-%s.xlsx" % self.collection, filetypes=(("Workbook Excel", "*.xlsx"),))
        if not path: return
        try:
            export_rows = self._export_view_rows()
            titles = self._column_titles()
            self.use_cases.export_excel(self.account, self.collection, path, titles,
                                        [values[:len(titles)] for _, _, values in export_rows])
            messagebox.showinfo("Ekspor selesai", "%s baris diekspor sesuai filter aktif." % len(export_rows), parent=self.root)
        except Exception as exc:
            messagebox.showerror("Gagal ekspor Excel", str(exc), parent=self.root)

    def print_pdf(self):
        path = filedialog.asksaveasfilename(parent=self.root, title="Simpan hasil cetak", defaultextension=".pdf", initialfile="DELIMOLD-%s.pdf" % self.collection, filetypes=(("PDF", "*.pdf"),))
        if not path: return
        try:
            export_rows = self._export_view_rows()
            titles = self._column_titles()
            self.use_cases.print_pdf(self.account, self.collection, path,
                                     "DELIMOLD · %s" % TABS[self.collection], titles,
                                     [values[:len(titles)] for _, _, values in export_rows])
            messagebox.showinfo("PDF selesai", "%s baris dicetak sesuai filter aktif." % len(export_rows), parent=self.root)
        except Exception as exc:
            messagebox.showerror("Gagal membuat PDF", str(exc), parent=self.root)

    def auto_refresh(self):
        if self.root.winfo_exists():
            if self.mode == "viewer":
                self.refresh()
            self.root.after(120000, self.auto_refresh)

    def close(self):
        try:
            if self.mode == "master":
                self.use_cases.close()
        finally:
            self.root.destroy()

