"""Tkinter record_forms for the DELIMOLD desktop adapter."""
import json
import tkinter as tk
import time
from tkinter import ttk

from app.application.dto import RecordSaveRequest, UserSaveRequest
from app.domain.validation import validate_status_transition
from .error_presenter import present_error
from .app_window_theme import CARD, INK, LINE, MUTED, PALE, WHITE
from .catalog_config import FIELDS, TABS


class RecordFormsMixin:
    def _record_form(self, key, record):
        if not self._can_write():
            return
        title = ("Edit " if key else "Tambah ") + TABS[self.collection]
        dlg = tk.Toplevel(self.root); dlg.title(title); dlg.transient(self.root); dlg.grab_set()
        dlg.overrideredirect(True); dlg.configure(bg=WHITE)
        dlg.geometry("600x700")
        dlg.minsize(540, 520)
        shell = tk.Frame(dlg, bg=WHITE, highlightbackground=LINE, highlightthickness=1)
        shell.pack(fill="both", expand=True)
        titlebar = tk.Frame(shell, bg=CARD, height=40)
        titlebar.pack(fill="x"); titlebar.pack_propagate(False)
        tk.Label(titlebar, text=title, bg=CARD, fg=INK, font=("Segoe UI", 10), anchor="w").pack(side="left", fill="both", expand=True, padx=13)
        tk.Button(titlebar, text="×", command=dlg.destroy, bg=CARD, fg=MUTED,
                  activebackground=PALE, activeforeground=INK, bd=0, relief="flat",
                  highlightthickness=0, font=("Segoe UI", 16), width=3, cursor="hand2").pack(side="right", fill="y")
        drag = {"x": 0, "y": 0}
        def start_drag(event):
            drag["x"], drag["y"] = event.x_root - dlg.winfo_x(), event.y_root - dlg.winfo_y()
        def move_dialog(event):
            dlg.geometry("+%d+%d" % (event.x_root - drag["x"], event.y_root - drag["y"]))
        titlebar.bind("<ButtonPress-1>", start_drag)
        titlebar.bind("<B1-Motion>", move_dialog)
        for child in titlebar.winfo_children():
            child.bind("<ButtonPress-1>", start_drag)
            child.bind("<B1-Motion>", move_dialog)
        outer = tk.Frame(shell, bg=WHITE, padx=18, pady=12); outer.pack(fill="both", expand=True)
        form_host = ttk.Frame(outer); form_host.pack(fill="both", expand=True, pady=(0, 8))
        canvas = tk.Canvas(form_host, highlightthickness=0, bd=0, bg=WHITE)
        scrollbar = ttk.Scrollbar(form_host, orient="vertical", command=canvas.yview)
        form = ttk.Frame(canvas)
        form_window = canvas.create_window((0, 0), window=form, anchor="nw")
        form.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(form_window, width=event.width))
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind("<MouseWheel>", lambda event: canvas.yview_scroll(int(-event.delta / 120), "units"))
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
                if self.collection == "molds":
                    if record:
                        validate_status_transition(
                            record.get("status"), value.get("status"),
                            value.get("statusReason"), record.get("statusReason"))
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
                self.use_cases.save_record(RecordSaveRequest(
                    self.account, self.collection, record_key, value,
                    "edit" if key else "create"))
                dlg.destroy(); self.refresh()
            except Exception as exc:
                error.set(present_error(exc))
        ttk.Button(buttons, text="Simpan", command=save).pack(side="right")

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
                self.use_cases.save_user(UserSaveRequest(
                    self.account, name, display, role, password,
                    enabled=(record or {}).get("enabled", True), existing=bool(username)))
                dlg.destroy(); self.refresh()
            except Exception as exc: error.set(present_error(exc))
        ttk.Button(actions, text="Simpan", command=save).pack(side="left", padx=5)
        dlg.update_idletasks()
        x = self.root.winfo_rootx() + max(0, (self.root.winfo_width() - dlg.winfo_width()) // 2)
        y = self.root.winfo_rooty() + max(0, (self.root.winfo_height() - dlg.winfo_height()) // 2)
        dlg.geometry("+%d+%d" % (x, y))
        dlg.bind("<Escape>", lambda _event: dlg.destroy())
        dlg.wait_window()
