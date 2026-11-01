"""Translate application and infrastructure failures into safe UI messages."""
from app.domain.errors import AppError


def present_error(error, fallback="Terjadi kesalahan tak terduga. Silakan coba kembali."):
    """Return a user-facing message without exposing unexpected exception details."""
    if isinstance(error, AppError):
        return str(error) or fallback
    if isinstance(error, ValueError):
        return str(error) or "Data yang dimasukkan tidak valid."
    if isinstance(error, FileNotFoundError):
        return "File atau folder yang dipilih tidak ditemukan."
    if isinstance(error, PermissionError):
        return "Akses ke file atau folder ditolak. Periksa hak aksesnya."
    if isinstance(error, OSError):
        return "File atau folder tidak dapat diakses. Periksa lokasi dan koneksi jaringan."
    return fallback
