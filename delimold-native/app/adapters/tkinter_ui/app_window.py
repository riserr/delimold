"""Native Tk desktop UI. This module never opens or embeds a browser."""
import socket
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox, simpledialog, ttk
from pathlib import Path
from uuid import uuid4

from app.domain.models import Actor
from .location_settings import configure_master_paths
from .app_window_theme import CARD, DARK, FIELD, GREEN, INK, LINE, MUTED, PALE, WHITE
from .shared_components import build_database_status, build_header, build_sidebar
from .catalog_config import TABS
from .catalog_screen import CatalogScreenMixin
from .record_forms import RecordFormsMixin
from .data_transfer import DataTransferMixin


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





class NativeApp(CatalogScreenMixin, RecordFormsMixin, DataTransferMixin):
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
        self._auto_refresh_id = self.root.after(120000, self.auto_refresh)

    def configure_locations(self):
        # Render the settings page in the existing application window.
        # Stop the old page's timer while its widgets are temporarily removed.
        main_geometry = self.root.geometry()
        if getattr(self, "_auto_refresh_id", None):
            try:
                self.root.after_cancel(self._auto_refresh_id)
            except tk.TclError:
                pass
            self._auto_refresh_id = None
        for child in self.root.winfo_children():
            child.destroy()
        updated = None
        try:
            updated = configure_master_paths(self.root, self.base_dir, dict(self.config), force=True)
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
            if self.root.winfo_exists():
                self.root.minsize(980, 620)
                self.root.geometry(main_geometry)
                self.root.protocol("WM_DELETE_WINDOW", self.close)
                self._build()
                self.refresh()

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









    def auto_refresh(self):
        if self.root.winfo_exists():
            if self.mode == "viewer":
                self.refresh()
            self._auto_refresh_id = self.root.after(120000, self.auto_refresh)

    def close(self):
        try:
            if self.mode == "master":
                self.use_cases.close()
        finally:
            self.root.destroy()

