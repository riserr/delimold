"""Native Tk desktop UI. This module never opens or embeds a browser."""
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from pathlib import Path

from .app_window_theme import CARD, DARK, FIELD, GREEN, INK, LINE, MUTED, WHITE
from .shared_components import RoundedPanel, RoundedScrollbar, build_database_status, build_header, build_sidebar
from .catalog_screen import CatalogScreenMixin
from .record_forms import RecordFormsMixin
from .data_transfer import DataTransferMixin
from .authentication import AuthenticationMixin
from .navigation import NavigationMixin
from .record_actions import RecordActionsMixin


class RoundedToolbarButton(tk.Canvas):
    """Canvas-backed toolbar button matching checkpoint v12's rounded shape."""
    def __init__(self, parent, text, command, primary=False):
        self.label = text
        self.command = command
        self.primary = primary
        self.enabled = True
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
        if not self.enabled:
            fill = "#26322b"
            border = LINE
            text_color = MUTED
        else:
            border = self.border
            text_color = self.label_color
        self._rounded_rect(0, 0, self.width - 1, self.height - 1, 5, border, "border")
        self._rounded_rect(1, 1, self.width - 2, self.height - 2, 4, fill, "surface")
        self.create_text(self.width // 2, self.height // 2, text=self.label, fill=text_color,
                         font=self.font, tags="label")

    def _invoke(self, _event=None):
        if self.enabled:
            self.command()

    def configure(self, cnf=None, **kwargs):
        state = kwargs.pop("state", None)
        if state is not None:
            self.enabled = state != "disabled"
            self._draw(self.normal_fill if self.enabled else "#26322b")
        if kwargs:
            super().configure(cnf, **kwargs)

    config = configure

    def cget(self, key):
        if key == "text":
            return self.label
        return super().cget(key)





class RoundedSelector(tk.Canvas):
    """Rounded selector for compact pagination choices."""

    def __init__(self, parent, variable, values, command, width=60, height=31):
        self.variable = variable
        self.values = values
        self.command = command
        self.width = width
        self.height = height
        super().__init__(parent, width=width, height=height, bd=0,
                         highlightthickness=0, relief="flat",
                         bg=parent.cget("bg"), cursor="hand2")
        self.bind("<Button-1>", self._open_menu)
        self.bind("<Configure>", lambda _event: self._draw())
        self._draw()

    def _draw(self):
        self.delete("all")
        width = max(self.winfo_width(), self.width)
        height = max(self.winfo_height(), self.height)
        RoundedToolbarButton._rounded_rect(self, 1, 1, width-2, height-2, 7, LINE, "border")
        RoundedToolbarButton._rounded_rect(self, 2, 2, width-3, height-3, 6, FIELD, "surface")
        self.create_text(10, height // 2, text=self.variable.get(), anchor="w",
                         fill=INK, font=("Segoe UI", 8))
        self.create_polygon(width-15, height//2-2, width-9, height//2-2,
                            width-12, height//2+2, fill=INK, outline=INK)

    def _open_menu(self, _event=None):
        menu = tk.Menu(self, tearoff=0, bg=WHITE, fg=INK,
                       activebackground=PALE, activeforeground=INK,
                       borderwidth=1, relief="solid")
        for value in self.values:
            menu.add_command(label=value, command=lambda item=value: self._select(item))
        try:
            menu.tk_popup(self.winfo_rootx(), self.winfo_rooty() + self.winfo_height())
        finally:
            menu.grab_release()

    def _select(self, value):
        self.variable.set(value)
        self._draw()
        self.command()


class NativeApp(AuthenticationMixin, NavigationMixin, RecordActionsMixin,
                CatalogScreenMixin, RecordFormsMixin, DataTransferMixin):
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
        self._publish_retry_active = False
        self._closing = False
        self.location_status_label = None
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
        style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
        style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=INK,
                        rowheight=29, bordercolor=LINE, lightcolor=LINE, darkcolor=LINE,
                        borderwidth=0, relief="flat", font=("Segoe UI", 9))
        style.configure("Treeview.Heading", background=WHITE, foreground=MUTED,
                        bordercolor=LINE, lightcolor=LINE, darkcolor=LINE, borderwidth=0,
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
        self.content_host = tk.Frame(self.main, bg=DARK)
        self.content_host.pack(fill="both", expand=True)
        self._show_catalog_page()



    def _render_catalog_content(self):
        content = tk.Frame(self.content_host, bg=DARK)
        content.pack(fill="both", expand=True, padx=20, pady=15)
        tk.Label(content, text="MOLD MANAGEMENT   ·   DESKTOP PORTABLE", bg=DARK, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        self.title_label = tk.Label(content, text="Data Cetakan", bg=DARK, fg=INK, font=("Segoe UI", 22, "normal"))
        self.title_label.pack(anchor="w", pady=(3, 1))
        tk.Label(content, text="Kelola dan telusuri data cetakan dalam satu tempat.", bg=DARK, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w")
        _status_frame, self.connection_label = build_database_status(content, self.mode)
        self.stats_frame = tk.Frame(content, bg=DARK)
        self.stats_frame.pack(fill="x", pady=(0, 12))
        self._make_stats()
        panel = RoundedPanel(content, fill=WHITE, border=LINE, radius=8)
        panel.pack(fill="both", expand=True)
        surface = panel.content
        head = tk.Frame(surface, bg=WHITE); head.pack(fill="x", padx=14, pady=(12, 8))
        tk.Frame(surface, bg=LINE, height=1).pack(fill="x")
        self.list_label = tk.Label(head, text="Daftar cetakan", bg=WHITE, fg=INK, font=("Segoe UI", 10, "bold"))
        self.list_label.pack(anchor="w")
        tk.Label(head, text="Ekspor dan cetak mengikuti pencarian serta filter yang aktif.", bg=WHITE, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(3, 0))
        self.actions = tk.Frame(surface, bg=WHITE)
        self.actions.pack(fill="x", padx=10, pady=7)
        self.toolbar_buttons = {}
        self._action_button("＋ Tambah", self.add_record, primary=True)
        self._action_button("↑ Impor Excel", self.import_excel)
        self._action_button("↓ Ekspor Excel", self.export_excel)
        self._action_button("▣ Cetak PDF", self.print_pdf)
        self.readonly_label = tk.Label(self.actions, text="Akses baca-saja", bg="#493c27", fg="#f3d59b", padx=8, pady=5, font=("Segoe UI", 8))
        if self.mode == "viewer" or self.account.role == "VIEWER":
            self._set_readonly()
        tk.Frame(surface, bg=LINE, height=1).pack(fill="x")
        self.filters = tk.Frame(surface, bg=WHITE)
        self.filters.pack(fill="x", padx=10, pady=9)
        search_row = tk.Frame(self.filters, bg=WHITE)
        search_row.pack(fill="x", pady=(0, 7))
        ttk.Entry(search_row, textvariable=self.search_var).pack(side="left", fill="x", expand=True, padx=(0, 7))
        self.search_var.trace_add("write", lambda *_: self._schedule_filter_refresh())
        ttk.Button(search_row, text="Reset filter", command=self.reset_filters).pack(side="right")
        self.filter_fields_frame = tk.Frame(self.filters, bg=WHITE)
        self.filter_fields_frame.pack(fill="x")
        self._build_filters()
        tk.Frame(surface, bg=LINE, height=1).pack(fill="x")
        actions_bottom = tk.Frame(surface, bg=WHITE)
        actions_bottom.pack(side="bottom", fill="x", padx=10, pady=(4, 7))
        tk.Frame(actions_bottom, bg=LINE, height=1).pack(fill="x", pady=(0, 5))
        self.row_action_buttons = []
        if self.mode != "viewer" and self.account.role != "VIEWER":
            b = RoundedToolbarButton(actions_bottom, "Edit", self.edit_record)
            b.pack(side="left", padx=(0, 6), pady=2); self.row_action_buttons.append(b)
            self.toggle_button = RoundedToolbarButton(actions_bottom, "Aktif / Nonaktif", self.toggle_status)
            self.toggle_button.pack(side="left", padx=6, pady=2); self.row_action_buttons.append(self.toggle_button)
            if self.account.role == "SUPERVISOR":
                b = RoundedToolbarButton(actions_bottom, "Hapus", self.delete_record)
                b.pack(side="left", padx=6, pady=2); self.row_action_buttons.append(b)
        self.row_count = tk.Label(actions_bottom, textvariable=self.status_text, bg=WHITE, fg=MUTED, font=("Segoe UI", 8))
        self.row_count.pack(side="left", padx=9)
        ttk.Label(actions_bottom, text="Baris per halaman").pack(side="right", padx=(6, 0))
        self.page_box = RoundedSelector(actions_bottom, self.page_var,
                                        ("25", "50", "100", "Semua"), self._change_page_size)
        self.page_box.pack(side="right", padx=(0, 2))
        self.next_page_button = RoundedToolbarButton(actions_bottom, "Berikutnya ›", self.next_page)
        self.next_page_button.pack(side="right", padx=(6, 0), pady=2)
        self.page_label = ttk.Label(actions_bottom, text="Halaman 1")
        self.page_label.pack(side="right", padx=6)
        self.previous_page_button = RoundedToolbarButton(actions_bottom, "‹ Sebelumnya", self.previous_page)
        self.previous_page_button.pack(side="right", padx=(0, 6), pady=2)

        tablebox = tk.Frame(surface, bg=WHITE)
        tablebox.pack(fill="both", expand=True)
        horizontal_scroll = RoundedScrollbar(
            tablebox, lambda *args: self.tree.xview(*args), orient="horizontal")
        horizontal_scroll.pack(side="bottom", fill="x", padx=(5, 20), pady=(0, 3))
        table_area = tk.Frame(tablebox, bg=WHITE)
        table_area.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table_area, show="headings", selectmode="browse", height=5)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll = RoundedScrollbar(table_area, self.tree.yview)
        scroll.pack(side="right", fill="y", padx=(2, 5), pady=3)
        self.tree.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal_scroll.set)
        self.tree.bind("<Double-1>", lambda _e: self.edit_record())
        self._schedule_auto_refresh()

    def _schedule_auto_refresh(self):
        scheduled = getattr(self, "_auto_refresh_id", None)
        if scheduled:
            try:
                self.root.after_cancel(scheduled)
            except tk.TclError:
                pass
        if not self._closing:
            self._auto_refresh_id = self.root.after(120000, self.auto_refresh)


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








































    def auto_refresh(self):
        if not self._closing and self.root.winfo_exists():
            if self.mode == "viewer":
                if getattr(self, "current_view", "catalog") == "catalog":
                    self.refresh()
            else:
                self._retry_pending_publication()
            self._schedule_auto_refresh()

    def _retry_pending_publication(self):
        if self._publish_retry_active or self._closing:
            return
        self._publish_retry_active = True

        def publish():
            published = False
            try:
                published = self.use_cases.publish_pending()
            except Exception:
                # The revision remains pending in SQLite and will be retried
                # at the next scheduled pass.
                pass
            try:
                self.root.after(0, lambda: self._publication_retry_finished(published))
            except tk.TclError:
                pass

        threading.Thread(target=publish, name="DELIMOLD-SALAK-retry", daemon=True).start()

    def _publication_retry_finished(self, published):
        self._publish_retry_active = False
        if self._closing:
            return
        if published and self.location_status_label is not None:
            try:
                self.location_status_label.configure(
                    fg=GREEN, text="Snapshot SALAK berhasil diperbarui otomatis.")
            except tk.TclError:
                self.location_status_label = None

    def close(self):
        self._closing = True
        try:
            if self.mode == "master":
                self.use_cases.close()
        finally:
            self.root.destroy()

