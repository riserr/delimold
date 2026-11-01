"""Unit tests for business invariants owned by the domain layer."""
import unittest

from app.domain.errors import ValidationError
from app.domain.validation import (validate_record, validate_status_transition,
                                   validate_user)


class DomainValidationTests(unittest.TestCase):
    def test_mold_requires_its_business_identifiers(self):
        with self.assertRaisesRegex(ValidationError, "pattern"):
            validate_record("molds", "MD-1", {"spec": "MD-1", "size": "245/45R18"}, "create")

    def test_valid_mold_and_status_reason_are_accepted(self):
        value = {"spec": "MD-1", "size": "245/45R18", "patternId": "KU-1",
                 "serial": "01", "cure": "press"}
        self.assertEqual(value, validate_record("molds", "MD-1", value, "create"))
        with self.assertRaisesRegex(ValidationError, "Alasan"):
            validate_record("molds", "MD-1", dict(value, status="inactive"), "status")

    def test_purchase_validation_checks_calendar_date_and_normalizes_quantity(self):
        value = {"spec": "MD-1", "size": "245/45R18", "date": "2026-11-01",
                 "quantity": "2", "price": "125.50", "currency": "USD"}
        result = validate_record("purchases", "PO-1", value, "create")
        self.assertEqual(2, result["quantity"])
        with self.assertRaisesRegex(ValidationError, "Tanggal pembelian"):
            validate_record("purchases", "PO-1", dict(value, date="2026-02-30"), "create")

    def test_user_identity_role_and_password_are_domain_invariants(self):
        validate_user("sup", "SUPERVISOR", "1234", password_required=True)
        with self.assertRaisesRegex(ValidationError, "peran"):
            validate_user("sup", "ROOT", "1234", password_required=True)
        with self.assertRaisesRegex(ValidationError, "4–12"):
            validate_user("sup", "SUPERVISOR", "123", password_required=True)

    def test_status_change_requires_a_new_reason(self):
        validate_status_transition("active", "inactive", "Nonaktif untuk perbaikan", "")
        with self.assertRaisesRegex(ValidationError, "alasan baru"):
            validate_status_transition("active", "inactive", "Sebelumnya", "Sebelumnya")


if __name__ == "__main__":
    unittest.main()
