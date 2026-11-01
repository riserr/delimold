"""Tkinter catalog_screen for the DELIMOLD desktop adapter."""
import json
import tkinter as tk
from tkinter import messagebox, ttk

from app.application.dto import CatalogPageQuery, FilterOptionsQuery, SnapshotReadRequest
from .error_presenter import present_error
from .app_window_theme import CARD, GREEN, LINE, MUTED, WHITE
from .shared_components import RoundedField, RoundedPanel
from .catalog_config import FILTER_FIELDS


class CatalogScreenMixin:
    def _fetch_catalog(self):
        if self.mode == "master":
            return self.use_cases.catalog(self.account).as_dict()
        return self.use_cases.published_catalog(
            SnapshotReadRequest(self.config["snapshot_path"])).as_dict()

    def _selected_filters(self):
        filters = {}
        for field, variable in self.filter_vars.items():
            label = variable.get()
            if label and label != "Semua":
                filters[field] = self.filter_query_maps.get(field, {}).get(label, label)
        return filters

    def _change_page_size(self):
        self.page_index = 0
        self.refresh()

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

    def previous_page(self):
        if self.page_index > 0:
            self.page_index -= 1
            self.refresh()

    def _make_stats(self):
        self.stat_values = []
        for i in range(4):
            frame = RoundedPanel(self.stats_frame, fill=CARD, border=LINE, radius=7, padx=12, pady=8)
            frame.pack(side="left", fill="x", expand=True, padx=(0 if i == 0 else 8, 0))
            label = tk.Label(frame.content, text=("Total", "Kode unik", "Aktif", "Nonaktif")[i], bg=CARD, fg=MUTED, font=("Segoe UI", 9))
            label.pack(anchor="w")
            value = tk.Label(frame.content, text="—", bg=CARD, fg=GREEN, font=("Segoe UI", 21))
            value.pack(anchor="w", pady=(3, 0))
            self.stat_values.append((label, value))

    def _selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Pilih data", "Pilih satu baris terlebih dahulu.", parent=self.root)
            return None
        key = selection[0]
        return key, self.rows.get(key) if isinstance(self.rows, dict) else None

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

    def refresh(self):
        try:
            if self.mode == "master" and self.collection not in ("accounts", "history"):
                page_size = str(self.page_var.get() or "50")
                limit = 2147483647 if page_size == "Semua" else int(page_size)
                offset = self.page_index * limit
                page_data = self.use_cases.catalog_page(self.account, CatalogPageQuery(
                    self.collection, offset, limit,
                    self.search_var.get().strip(), self._selected_filters()))
                self.rows = page_data.rows
                self.catalog = {"collections": {self.collection: self.rows}}
                self.catalog["collections"].update(page_data.lookups)
                self._page_stats = page_data.stats
                self.page_total = self._page_stats["total"]
                max_page = max((self.page_total - 1) // limit, 0)
                self.page_index = min(self.page_index, max_page)
                if offset != self.page_index * limit:
                    return self.refresh()
            elif self.collection == "accounts":
                self.rows = {name: user.as_dict()
                             for name, user in self.use_cases.list_users(self.account).items()}
            elif self.collection == "history":
                history = self.use_cases.audit_rows(self.account)
                self.rows = {str(row.id or i): row.as_dict() for i, row in enumerate(history)}
            else:
                self.catalog = self._fetch_catalog()
                self.rows = self.catalog.get("collections", {}).get(self.collection, {})
            self.connection_label.configure(text="Salinan baca-saja · publikasi SALAK" if self.mode == "viewer" else ("Data utama · TENDERLOIN" if self.mode == "master" else "Terhubung · TENDERLOIN"))
            self._update_stats()
            self.refresh_table()
        except Exception as exc:
            message = present_error(exc, "Data DELIMOLD tidak dapat dimuat.")
            self.status_text.set("Gagal memuat data: %s" % message)
            messagebox.showerror("Koneksi DELIMOLD", message, parent=self.root)

    @staticmethod
    def _status(value):
        return "Aktif" if str(value or "active").lower() in ("active", "aktif") else "Nonaktif"

    def _column_titles(self):
        return {"molds": ("KODE SPEK", "SIZE CETAKAN", "PATTERN", "NO. CETAKAN", "TIPE MASAK", "TIPE CETAKAN", "STATUS", "CONTAINER"),
                "containers": ("KODE CONTAINER", "NO.", "OD SECTOR", "SW SECTOR", "SPACER", "STATUS"),
                "patterns": ("KODE PATTERN", "NAMA", "LAND", "STATUS"),
                "stickers": ("NAMA STICKER", "STATUS"),
                "projects": ("KODE SPEK", "PROJECT", "ID PROJECT", "STATUS", "TARGET HARI"),
                "purchases": ("TANGGAL", "KODE SPEK", "SIZE", "PATTERN", "NO. MOLD", "JUMLAH", "SUPPLIER", "MATA UANG", "HARGA SATUAN", "STATUS"),
                "accounts": ("NAMA AKUN", "NAMA TAMPILAN", "PERAN", "AKTIF"),
                "history": ("WAKTU", "AKSI", "DATA", "ID", "AKUN", "KOMPUTER", "ALASAN")} [self.collection]

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

    def _schedule_filter_refresh(self):
        if self._search_after_id is not None:
            try:
                self.root.after_cancel(self._search_after_id)
            except tk.TclError:
                pass
        self._search_after_id = self.root.after(250, self._filter_changed)

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
            self.tree.column(col, width=150, minwidth=110, stretch=False, anchor="w")
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

    def _filter_changed(self):
        if self._search_after_id is not None:
            try:
                self.root.after_cancel(self._search_after_id)
            except tk.TclError:
                pass
            self._search_after_id = None
        self.page_index = 0
        self.refresh()

    def reset_filters(self):
        self.search_var.set("")
        for variable in self.filter_vars.values():
            variable.set("Semua")
        self._filter_changed()

    def _update_filter_choices(self):
        self.filter_query_maps = {}
        records = self.rows if isinstance(self.rows, dict) else {str(i): row for i, row in enumerate(self.rows)}
        for field, box in self.filter_boxes.items():
            if self.mode == "master" and self.collection not in ("accounts", "history"):
                options = self.use_cases.filter_options(
                    self.account, FilterOptionsQuery(self.collection, field))
                mapping = {option.label: option.value for option in options}
                self.filter_query_maps[field] = mapping
                values = sorted(mapping, key=lambda value: value.lower())
            else:
                values = sorted({self._filter_value(field, row) for row in records.values()
                                 if isinstance(row, dict) and self._filter_value(field, row)})
                self.filter_query_maps[field] = {value: value for value in values}
            box.configure(values=("Semua",) + tuple(values))
            if self.filter_vars[field].get() not in ("Semua",) + tuple(values):
                self.filter_vars[field].set("Semua")

    def next_page(self):
        if (self.page_index + 1) * int(self.page_var.get()) < self.page_total:
            self.page_index += 1
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
            rounded = RoundedField(cell, ttk.Combobox, textvariable=variable,
                                   state="readonly", style="Rounded.TCombobox")
            rounded.pack(fill="x")
            box = rounded.control
            box.bind("<<ComboboxSelected>>", lambda _event: self._filter_changed())
            self.filter_vars[field] = variable
            self.filter_boxes[field] = box
        self._update_filter_choices()
