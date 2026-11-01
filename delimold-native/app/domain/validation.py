"""Business invariants that must hold regardless of the UI or adapter."""
import re
from datetime import datetime

from .errors import ValidationError
from .permissions import PUBLIC_COLLECTIONS


EDITABLE_COLLECTIONS = frozenset(PUBLIC_COLLECTIONS + ("projects", "purchases"))
RECORD_ACTIONS = frozenset(("create", "edit", "status", "import"))
USER_ROLES = frozenset(("SUPERVISOR", "ENGINEER", "VIEWER"))


def validate_record(collection, key, value, action):
    """Validate record invariants; request/capability checks stay in application."""
    if collection not in EDITABLE_COLLECTIONS:
        raise ValidationError("Koleksi tidak dikenal atau tidak dapat diubah.")
    if action not in RECORD_ACTIONS:
        raise ValidationError("Jenis perubahan data tidak valid.")
    if not str(key or "").strip() or not isinstance(value, dict):
        raise ValidationError("Data tidak lengkap atau formatnya tidak valid.")
    value = dict(value)

    if action == "status" and not str(value.get("statusReason", "")).strip():
        raise ValidationError("Alasan perubahan status wajib diisi.")

    if collection == "molds":
        missing = [label for field, label in (
            ("spec", "kode spek"), ("size", "size"), ("patternId", "pattern"),
            ("serial", "nomor cetakan"), ("cure", "tipe masak"),
        ) if not str(value.get(field, "")).strip()]
        if missing:
            raise ValidationError("Wajib diisi: %s" % ", ".join(missing))

    if collection == "purchases":
        if not _is_date(value.get("date")):
            raise ValidationError("Tanggal pembelian harus YYYY-MM-DD")
        received = value.get("poReceivedDate")
        if received and not _is_date(received):
            raise ValidationError("Tanggal PO diterima harus YYYY-MM-DD atau kosong")
        if not value.get("spec") or not value.get("size"):
            raise ValidationError("Kode spek dan size ban wajib diisi")
        try:
            quantity = int(value.get("quantity", 0))
            price_text = str(value.get("price", ""))
            price = float(price_text)
        except (TypeError, ValueError):
            raise ValidationError("Jumlah mold dan harga satuan harus berupa angka")
        if quantity < 1 or price < 0 or not re.match(r"^\d+(\.\d{1,2})?$", price_text):
            raise ValidationError("Jumlah mold minimal 1 dan harga maksimal dua angka desimal")
        if value.get("currency") not in ("USD", "RMB", "IDR"):
            raise ValidationError("Pilih mata uang USD, RMB, atau IDR")
        value["quantity"] = quantity
    return value


def validate_user(username, role, password, password_required=False):
    """Validate account identity, role, and the application's password rule."""
    if not str(username or "").strip() or role not in USER_ROLES:
        raise ValidationError("Nama akun atau peran tidak valid.")
    if password_required and not password:
        raise ValidationError("Password wajib diisi untuk akun baru.")
    if password and not (4 <= len(password) <= 12):
        raise ValidationError("Password harus 4–12 karakter.")


def validate_status_transition(previous_status, updated_status, reason, previous_reason=""):
    """Require a new explanation whenever a mold status actually changes."""
    if (str(previous_status or "active") != str(updated_status or "active") and
            (not str(reason or "").strip() or
             str(reason).strip() == str(previous_reason or "").strip())):
        raise ValidationError("Isi alasan baru untuk perubahan status cetakan")


def _is_date(value):
    try:
        parsed = datetime.strptime(str(value), "%Y-%m-%d")
        return parsed.strftime("%Y-%m-%d") == str(value)
    except (TypeError, ValueError):
        return False
