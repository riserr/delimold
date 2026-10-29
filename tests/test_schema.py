import sqlite3
import unittest
from pathlib import Path

SCHEMAS = Path(__file__).resolve().parents[1] / 'database' / 'schema'


def database(name):
    connection = sqlite3.connect(':memory:')
    connection.executescript((SCHEMAS / (name + '.sql')).read_text())
    return connection


class SchemaTests(unittest.TestCase):
    def test_all_schemas_initialize(self):
        for name in ('operational', 'private', 'identity', 'viewer'):
            with self.subTest(name=name), database(name) as db:
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
                self.assertEqual(db.execute('PRAGMA foreign_keys').fetchone()[0], 1)

    def operational(self):
        db = database('operational')
        self.addCleanup(db.close)
        db.execute("INSERT INTO patterns(id,code,name) VALUES ('p','KU-257','Pattern')")
        db.execute("INSERT INTO mold_specs(id,spec_code,tire_size,pattern_id) VALUES ('s','SPEC-1','29x2.25','p')")
        return db

    def test_foreign_keys_codes_and_unique_mold_numbers(self):
        db = self.operational()
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO patterns(id,code,name) VALUES ('q','ku-257','Duplicate')")
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO mold_units(id,spec_id,mold_number) VALUES ('x','missing','01')")
        db.execute("INSERT INTO mold_units(id,spec_id,mold_number) VALUES ('u','s','01')")
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO mold_units(id,spec_id,mold_number) VALUES ('v','s','01')")
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("DELETE FROM mold_specs WHERE id='s'")

    def test_sharing_requires_valid_main_and_protects_main(self):
        db = self.operational()
        db.execute("INSERT INTO mold_units(id,spec_id,mold_number,mold_type,segmented_role) VALUES ('m','s','01','SEGMENTED','MAIN')")
        db.execute("INSERT INTO mold_units(id,spec_id,mold_number,mold_type,segmented_role,main_unit_id) VALUES ('c','s','02','SEGMENTED','SHARING','m')")
        for sql in [
            "UPDATE mold_units SET archived_at='2026-10-29T00:00:00Z' WHERE id='m'",
            "UPDATE mold_units SET segmented_role=NULL WHERE id='m'",
            "UPDATE mold_units SET main_unit_id='c' WHERE id='c'",
            "UPDATE mold_units SET segmented_role=NULL WHERE id='c'",
            "UPDATE mold_units SET mold_type=NULL WHERE id='m'",
        ]:
            with self.subTest(sql=sql), self.assertRaises(sqlite3.IntegrityError):
                db.execute(sql)

    def test_spacer_must_belong_to_model_and_airbag_no_bladder(self):
        db = self.operational()
        db.execute("INSERT INTO container_models(id,code,model) VALUES ('a','A','A'),('b','B','B')")
        db.execute("INSERT INTO container_spacers(id,container_model_id,thickness_mm) VALUES ('sp','a',1)")
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO mold_units(id,spec_id,mold_number,container_model_id,spacer_id) VALUES ('u','s','01','b','sp')")
        with self.assertRaises(sqlite3.IntegrityError):
            db.execute("INSERT INTO mold_units(id,spec_id,mold_number,curing_type,bladder) VALUES ('u','s','01','AIRBAG','B1')")

    def test_outbox_rollback_with_business_change(self):
        db = self.operational()
        db.commit()
        db.execute("UPDATE patterns SET name='Changed',revision=revision+1 WHERE id='p' AND revision=1")
        db.execute("INSERT INTO publication_outbox(publication_id,source_updated_at) VALUES ('pub1','2026-10-29T00:00:00Z')")
        db.rollback()
        self.assertEqual(db.execute("SELECT name,revision FROM patterns WHERE id='p'").fetchone(), ('Pattern', 1))
        self.assertEqual(db.execute('SELECT count(*) FROM publication_outbox').fetchone()[0], 0)

    def test_roles_no_default_users_or_private_engineer_permission(self):
        with database('identity') as db:
            self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT count(*) FROM role_permissions WHERE role_id='engineer' AND permission_id LIKE 'private.%'").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT permission_id FROM role_permissions WHERE role_id='viewer' ORDER BY permission_id").fetchall(), [('operational.export',), ('operational.read',)])

    def test_private_money_and_po_integrity(self):
        with database('private') as db:
            db.execute("INSERT INTO suppliers(id,supplier_code,name) VALUES ('s','SUP-1','Test supplier')")
            db.execute("INSERT INTO purchase_orders(id,po_number,supplier_id,order_date,currency_code) VALUES ('po','PO-1','s','2026-10-29','USD')")
            sql = "INSERT INTO purchase_order_items(id,po_id,line_number,transaction_type,description_snapshot,quantity,unit_price_scaled) VALUES ('i','po',1,'PURCHASE','Test',1,?)"
            for price in (-1, 12.34):
                with self.assertRaises(sqlite3.IntegrityError): db.execute(sql, (price,))
            db.execute(sql, (12345,))
            self.assertEqual(db.execute('SELECT unit_price_scaled FROM purchase_order_items').fetchone()[0], 12345)

    def test_viewer_matches_explicit_projection_and_excludes_internal_data(self):
        with database('operational') as source, database('viewer') as target:
            tables = {row[0] for row in target.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            expected = {'categories','patterns','stickers','container_models','container_spacers','container_units','mold_specs','mold_units','mold_brands'}
            self.assertEqual(tables, expected | {'publication_meta'})
            for table in expected:
                published = {row[1] for row in source.execute('PRAGMA table_info(publish_' + table + ')')}
                stored = {row[1] for row in target.execute('PRAGMA table_info(' + table + ')')}
                self.assertEqual(published, stored)
                self.assertFalse({'created_by','updated_by','password_hash','unit_price_scaled'} & stored)
            self.assertEqual(target.execute('SELECT count(*) FROM publication_meta').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
