"""Verify UI errors are mapped consistently and unexpected details stay hidden."""
import unittest

from app.adapters.tkinter_ui.error_presenter import present_error
from app.domain.errors import StorageError, ValidationError


class ErrorPresenterTests(unittest.TestCase):
    def test_application_errors_keep_their_user_facing_message(self):
        self.assertEqual("Password harus 4–12 karakter.",
                         present_error(ValidationError("Password harus 4–12 karakter.")))
        self.assertEqual("Database DELIMOLD tidak dapat dibuka.",
                         present_error(StorageError("Database DELIMOLD tidak dapat dibuka.")))

    def test_validation_and_filesystem_errors_are_mapped(self):
        self.assertEqual("Tanggal harus YYYY-MM-DD.", present_error(ValueError("Tanggal harus YYYY-MM-DD.")))
        self.assertEqual("File atau folder tidak dapat diakses. Periksa lokasi dan koneksi jaringan.",
                         present_error(OSError("secret internal path")))

    def test_unexpected_exception_details_are_not_exposed(self):
        message = present_error(RuntimeError("secret connection string"))
        self.assertNotIn("secret connection string", message)
        self.assertEqual("Terjadi kesalahan tak terduga. Silakan coba kembali.", message)


if __name__ == "__main__":
    unittest.main()
