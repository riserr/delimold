"""Tkinter data_transfer for the DELIMOLD desktop adapter."""
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .app_window_theme import INK, MUTED
from .catalog_config import FIELDS, TABS


class DataTransferMixin:
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
