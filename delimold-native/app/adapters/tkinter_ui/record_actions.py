"""Record and account actions initiated from the catalog UI."""
from tkinter import messagebox, simpledialog
from uuid import uuid4

from app.application.dto import (RecordDeleteRequest, RecordSaveRequest,
                                 UserDeleteRequest, UserEnabledRequest)
from .error_presenter import present_error

class RecordActionsMixin:

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
                self.use_cases.set_user_enabled(UserEnabledRequest(self.account, key, enabled))
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Status akun gagal diubah", present_error(exc), parent=self.root)
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
                self.use_cases.delete_user(UserDeleteRequest(self.account, key))
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Akun gagal dihapus", present_error(exc), parent=self.root)
            return
        if not messagebox.askyesno("Konfirmasi hapus", "Hapus data ini? Tindakan ini dicatat di riwayat.", parent=self.root):
            return
        try:
            self.use_cases.delete_record(RecordDeleteRequest(
                self.account, self.collection, key, "hapus oleh Supervisor"))
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Data gagal dihapus", present_error(exc), parent=self.root)

    def _save(self, value, key, action, reason=""):
        try:
            self.use_cases.save_record(RecordSaveRequest(
                self.account, self.collection, key, value, action, reason))
            self.refresh()
        except Exception as exc:
            messagebox.showerror("Gagal menyimpan", present_error(exc), parent=self.root)

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

