"""SQLite implementation of the application repository port."""
import json
import os
import sqlite3
import threading
import time
from pathlib import Path

from app.application.ports import CatalogRepository
from app.domain.errors import StorageError


COLLECTIONS = ("molds", "patterns", "containers", "stickers", "pattern_art",
               "purchases", "projects", "accounts", "events", "deleted")


class SQLiteCatalogRepository(CatalogRepository):
    @staticmethod
    def migrate_database(source_path, target_path):
        """Copy a live SQLite database safely, including committed WAL changes."""
        source = Path(source_path)
        target = Path(target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(target.name + ".migrating")
        source_connection = None
        target_connection = None
        try:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            source_connection = sqlite3.connect(str(source), timeout=20)
            target_connection = sqlite3.connect(str(temporary), timeout=20)
            source_connection.backup(target_connection)
            target_connection.close()
            target_connection = None
            source_connection.close()
            source_connection = None
            os.replace(str(temporary), str(target))
        except (OSError, sqlite3.Error) as exc:
            try:
                temporary.unlink()
            except OSError:
                pass
            raise StorageError("Database lama tidak dapat dipindahkan ke folder DATABASE.") from exc
        finally:
            if source_connection is not None:
                source_connection.close()
            if target_connection is not None:
                target_connection.close()

    def __init__(self, database_path):
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        try:
            self.connection = sqlite3.connect(str(self.path), timeout=20, check_same_thread=False)
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA foreign_keys=ON")
            self._schema()
        except sqlite3.Error as exc:
            raise StorageError("Database DELIMOLD tidak dapat dibuka.") from exc

    def _schema(self):
        with self.connection:
            self.connection.execute("""CREATE TABLE IF NOT EXISTS records (
                collection TEXT NOT NULL, record_key TEXT NOT NULL, payload TEXT NOT NULL,
                PRIMARY KEY(collection, record_key))""")
            self.connection.execute("""CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
            self.connection.execute("""CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, username TEXT,
                computer TEXT, action TEXT NOT NULL, collection TEXT, record_key TEXT,
                reason TEXT, detail TEXT)""")
            self.connection.execute("""CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, display_name TEXT NOT NULL, role TEXT NOT NULL,
                salt TEXT NOT NULL, password_hash TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1)""")
            self.connection.execute("""CREATE TABLE IF NOT EXISTS record_search (
                collection TEXT NOT NULL, record_key TEXT NOT NULL, search_text TEXT NOT NULL,
                PRIMARY KEY(collection, record_key))""")
            self.connection.execute("""CREATE TABLE IF NOT EXISTS record_fields (
                collection TEXT NOT NULL, record_key TEXT NOT NULL, field TEXT NOT NULL, value TEXT NOT NULL,
                PRIMARY KEY(collection, record_key, field, value))""")
            self.connection.execute("CREATE INDEX IF NOT EXISTS idx_record_fields_lookup ON record_fields(collection, field, value)")
            initial = (("revision", "1"), ("schema_version", "1"),
                       ("updated_at", time.strftime("%Y-%m-%dT%H:%M:%S")),
                       ("publish_required_revision", "0"), ("published_revision", "0"))
            for key, value in initial:
                self.connection.execute("INSERT OR IGNORE INTO meta(key,value) VALUES(?,?)", (key, value))
            missing = self.connection.execute(
                "SELECT r.collection,r.record_key,r.payload FROM records r "
                "LEFT JOIN record_search s ON s.collection=r.collection AND s.record_key=r.record_key "
                "WHERE s.record_key IS NULL").fetchall()
            for row in missing:
                try:
                    self._index_record(row["collection"], row["record_key"], json.loads(row["payload"]))
                except (TypeError, ValueError):
                    continue

    def close(self):
        try:
            self.connection.close()
        except sqlite3.Error as exc:
            raise StorageError("Database DELIMOLD gagal ditutup.") from exc

    def is_empty(self):
        with self.lock:
            try:
                row = self.connection.execute("SELECT COUNT(*) AS n FROM records").fetchone()
                return row["n"] == 0
            except sqlite3.Error as exc:
                raise StorageError("Status database tidak dapat dibaca.") from exc

    def user_count(self):
        with self.lock:
            try:
                return int(self.connection.execute("SELECT COUNT(*) FROM users").fetchone()[0])
            except sqlite3.Error as exc:
                raise StorageError("Daftar akun tidak dapat dibaca.") from exc

    def import_catalog(self, catalog, publish_required=False):
        collections = catalog.get("collections", {})
        with self.lock:
            try:
                with self.connection:
                    for name in COLLECTIONS:
                        rows = collections.get(name, {})
                        if isinstance(rows, list):
                            rows = {str(i): row for i, row in enumerate(rows)}
                        if not isinstance(rows, dict):
                            continue
                        for key, value in rows.items():
                            self.connection.execute(
                                "INSERT OR IGNORE INTO records(collection,record_key,payload) VALUES(?,?,?)",
                                (name, str(key), json.dumps(value, ensure_ascii=False, separators=(",", ":"))))
                            self._index_record(name, str(key), value)
                    revision = str(catalog.get("revision", 1))
                    updated_at = str(catalog.get("updatedAt") or time.strftime("%Y-%m-%dT%H:%M:%S"))
                    self._set_meta("revision", revision)
                    self._set_meta("updated_at", updated_at)
                    if publish_required:
                        self._set_meta("publish_required_revision", revision)
            except sqlite3.Error as exc:
                raise StorageError("Seed katalog tidak dapat dimuat ke database.") from exc

    def get_collection(self, collection):
        return self.get_collections((collection,)).get(collection, {})

    def get_collections(self, collections):
        result = {}
        with self.lock:
            try:
                for collection in collections:
                    rows = self.connection.execute(
                        "SELECT record_key,payload FROM records WHERE collection=? ORDER BY record_key",
                        (collection,)).fetchall()
                    result[collection] = {row["record_key"]: json.loads(row["payload"]) for row in rows}
                return result
            except (sqlite3.Error, ValueError) as exc:
                raise StorageError("Data katalog tidak dapat dibaca.") from exc

    def list_records_page(self, collection, offset, limit, search="", filters=None):
        clauses, params = self._record_where(collection, search, filters)
        sql = ("SELECT r.record_key,r.payload FROM records r "
               "JOIN record_search s ON s.collection=r.collection AND s.record_key=r.record_key WHERE " +
               " AND ".join(clauses) + " ORDER BY r.record_key LIMIT ? OFFSET ?")
        try:
            with self.lock:
                rows = self.connection.execute(sql, params + [int(limit), int(offset)]).fetchall()
                return {row["record_key"]: json.loads(row["payload"]) for row in rows}
        except (sqlite3.Error, ValueError) as exc:
            raise StorageError("Halaman data tidak dapat dibaca.") from exc

    def record_stats(self, collection, unique_field, search="", filters=None):
        clauses, params = self._record_where(collection, search, filters)
        where = " AND ".join(clauses)
        base = (" FROM records r JOIN record_search s ON s.collection=r.collection "
                "AND s.record_key=r.record_key WHERE " + where)
        try:
            with self.lock:
                total = int(self.connection.execute("SELECT COUNT(*)" + base, params).fetchone()[0])
                unique = int(self.connection.execute(
                    "SELECT COUNT(DISTINCT uf.value) FROM records r "
                    "JOIN record_search s ON s.collection=r.collection AND s.record_key=r.record_key "
                    "JOIN record_fields uf ON uf.collection=r.collection AND uf.record_key=r.record_key "
                    "AND uf.field=? WHERE " + where,
                    [unique_field] + params).fetchone()[0])
                if collection == "purchases":
                    submitted = self._count_field_values(collection, "status", ("Diajukan",), clauses, params)
                    received = self._count_field_values(collection, "status", ("Diterima",), clauses, params)
                    active, inactive = submitted, received
                else:
                    active = self._count_field_values(collection, "status", ("active", "aktif"), clauses, params, case_insensitive=True)
                    active += self._count_records_without_field(collection, "status", clauses, params)
                    inactive = max(total - active, 0)
                return {"total": total, "unique": unique, "active": active, "inactive": inactive}
        except sqlite3.Error as exc:
            raise StorageError("Ringkasan data tidak dapat dihitung.") from exc

    def record_filter_values(self, collection, field):
        try:
            with self.lock:
                rows = self.connection.execute(
                    "SELECT DISTINCT value FROM record_fields WHERE collection=? AND field=? ORDER BY lower(value),value",
                    (collection, field)).fetchall()
                return [row[0] for row in rows]
        except sqlite3.Error as exc:
            raise StorageError("Pilihan filter tidak dapat dimuat.") from exc

    def _count_field_values(self, collection, field, values, clauses, params, case_insensitive=False):
        if not values:
            return 0
        comparison = "lower(f.value) IN (%s)" if case_insensitive else "f.value IN (%s)"
        selected = tuple(value.lower() for value in values) if case_insensitive else tuple(values)
        placeholders = ",".join("?" for _ in selected)
        sql = ("SELECT COUNT(*) FROM records r JOIN record_search s ON s.collection=r.collection "
               "AND s.record_key=r.record_key WHERE " + " AND ".join(clauses) +
               " AND EXISTS (SELECT 1 FROM record_fields f WHERE f.collection=r.collection "
               "AND f.record_key=r.record_key AND f.field=? AND " + comparison % placeholders + ")")
        return int(self.connection.execute(sql, list(params) + [field] + list(selected)).fetchone()[0])

    def _count_records_without_field(self, collection, field, clauses, params):
        sql = ("SELECT COUNT(*) FROM records r JOIN record_search s ON s.collection=r.collection "
               "AND s.record_key=r.record_key WHERE " + " AND ".join(clauses) +
               " AND NOT EXISTS (SELECT 1 FROM record_fields f WHERE f.collection=r.collection "
               "AND f.record_key=r.record_key AND f.field=?)")
        return int(self.connection.execute(sql, list(params) + [field]).fetchone()[0])

    @staticmethod
    def _record_where(collection, search, filters):
        clauses = ["r.collection=?"]
        params = [collection]
        if search:
            escaped = str(search).lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            search_pattern = "%%%s%%" % escaped
            clauses.append("s.search_text LIKE ? ESCAPE '\\'")
            params.append(search_pattern)
            if collection == "molds":
                clauses[-1] = ("(" + clauses[-1] +
                    " OR EXISTS (SELECT 1 FROM record_fields link JOIN record_fields related "
                    "ON related.collection='patterns' AND related.record_key=link.value AND related.field='code' "
                    "WHERE link.collection=r.collection AND link.record_key=r.record_key "
                    "AND link.field='patternId' AND lower(related.value) LIKE ? ESCAPE '\\')"
                    " OR EXISTS (SELECT 1 FROM record_fields link JOIN record_fields related "
                    "ON related.collection='containers' AND related.record_key=link.value AND related.field='code' "
                    "WHERE link.collection=r.collection AND link.record_key=r.record_key "
                    "AND link.field='containerId' AND lower(related.value) LIKE ? ESCAPE '\\'))")
                params.extend((search_pattern, search_pattern))
        for field, value in (filters or {}).items():
            if not field or value is None or str(value) == "":
                continue
            if field == "status" and str(value).lower() == "active":
                clauses.append("EXISTS (SELECT 1 FROM record_fields f WHERE f.collection=r.collection "
                               "AND f.record_key=r.record_key AND f.field=? AND lower(f.value) IN ('active','aktif'))")
                params.append(field)
            elif field == "status" and str(value).lower() == "inactive":
                clauses.append("EXISTS (SELECT 1 FROM record_fields f WHERE f.collection=r.collection "
                               "AND f.record_key=r.record_key AND f.field=? AND lower(f.value) IN ('inactive','nonaktif'))")
                params.append(field)
            else:
                clauses.append("EXISTS (SELECT 1 FROM record_fields f WHERE f.collection=r.collection "
                               "AND f.record_key=r.record_key AND f.field=? AND lower(f.value)=lower(?))")
                params.extend((field, str(value)))
        return clauses, params

    def catalog_metadata(self):
        with self.lock:
            try:
                values = dict(self.connection.execute(
                    "SELECT key,value FROM meta WHERE key IN ('revision','updated_at')").fetchall())
                return {"revision": int(values.get("revision", "1")),
                        "updated_at": values.get("updated_at", "")}
            except (sqlite3.Error, ValueError) as exc:
                raise StorageError("Informasi revisi katalog tidak dapat dibaca.") from exc

    def save_record(self, collection, key, value, actor, computer, action, reason, publish_required):
        self._ensure_collection(collection)
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self.lock:
            try:
                with self.connection:
                    payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                    self.connection.execute(
                        "INSERT OR REPLACE INTO records(collection,record_key,payload) VALUES(?,?,?)",
                        (collection, str(key), payload))
                    self._index_record(collection, str(key), value)
                    revision = self._increment_revision(now)
                    self._write_audit(now, actor, computer, action, collection, key, reason)
                    if publish_required:
                        self._set_meta("publish_required_revision", str(revision))
                return revision
            except sqlite3.Error as exc:
                raise StorageError("Data gagal disimpan ke database.") from exc

    def save_records(self, collection, items, actor, computer, action, publish_required):
        self._ensure_collection(collection)
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self.lock:
            try:
                with self.connection:
                    for key, value in items:
                        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
                        self.connection.execute(
                            "INSERT OR REPLACE INTO records(collection,record_key,payload) VALUES(?,?,?)",
                            (collection, str(key), payload))
                        self._index_record(collection, str(key), value)
                        self._write_audit(now, actor, computer, action, collection, key, "")
                    revision = self._increment_revision(now) if items else self._current_revision()
                    if items and publish_required:
                        self._set_meta("publish_required_revision", str(revision))
                return revision
            except sqlite3.Error as exc:
                raise StorageError("Data impor gagal disimpan ke database.") from exc

    def delete_record(self, collection, key, actor, computer, reason, publish_required):
        self._ensure_collection(collection)
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self.lock:
            try:
                with self.connection:
                    cursor = self.connection.execute(
                        "DELETE FROM records WHERE collection=? AND record_key=?", (collection, str(key)))
                    if not cursor.rowcount:
                        return self._current_revision()
                    self.connection.execute("DELETE FROM record_search WHERE collection=? AND record_key=?", (collection, str(key)))
                    self.connection.execute("DELETE FROM record_fields WHERE collection=? AND record_key=?", (collection, str(key)))
                    revision = self._increment_revision(now)
                    self._write_audit(now, actor, computer, "delete", collection, key, reason)
                    if publish_required:
                        self._set_meta("publish_required_revision", str(revision))
                return revision
            except sqlite3.Error as exc:
                raise StorageError("Data gagal dihapus dari database.") from exc

    def pending_publish_revision(self):
        with self.lock:
            try:
                values = dict(self.connection.execute(
                    "SELECT key,value FROM meta WHERE key IN ('publish_required_revision','published_revision')").fetchall())
                required = int(values.get("publish_required_revision", "0"))
                published = int(values.get("published_revision", "0"))
                return required if required > published else 0
            except (sqlite3.Error, ValueError) as exc:
                raise StorageError("Status publikasi tidak dapat dibaca.") from exc

    def mark_published(self, revision):
        with self.lock:
            try:
                with self.connection:
                    self._set_meta("published_revision", str(revision))
            except sqlite3.Error as exc:
                raise StorageError("Status publikasi tidak dapat diperbarui.") from exc

    def audit_rows(self, limit=200):
        with self.lock:
            try:
                rows = self.connection.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
                return [dict(row) for row in rows]
            except sqlite3.Error as exc:
                raise StorageError("Riwayat perubahan tidak dapat dibaca.") from exc

    def list_users(self):
        with self.lock:
            try:
                rows = self.connection.execute(
                    "SELECT username,display_name,role,enabled FROM users ORDER BY username").fetchall()
                return {row["username"]: dict(row) for row in rows}
            except sqlite3.Error as exc:
                raise StorageError("Daftar akun tidak dapat dibaca.") from exc

    def get_user_credentials(self, username):
        with self.lock:
            try:
                row = self.connection.execute(
                    "SELECT username,display_name,role,salt,password_hash FROM users WHERE username=? AND enabled=1",
                    (username,)).fetchone()
                return dict(row) if row else None
            except sqlite3.Error as exc:
                raise StorageError("Akun tidak dapat diperiksa.") from exc

    def create_user(self, username, display_name, role, salt, password_hash):
        try:
            with self.lock, self.connection:
                self.connection.execute(
                    "INSERT INTO users(username,display_name,role,salt,password_hash,enabled) VALUES(?,?,?,?,?,1)",
                    (username, display_name, role, salt, password_hash))
        except sqlite3.IntegrityError as exc:
            raise StorageError("Nama akun sudah digunakan.") from exc
        except sqlite3.Error as exc:
            raise StorageError("Akun gagal disimpan.") from exc

    def update_user(self, username, display_name, role, enabled=None, salt=None, password_hash=None):
        updates = ["display_name=?", "role=?"]
        values = [display_name, role]
        if enabled is not None:
            updates.append("enabled=?")
            values.append(int(bool(enabled)))
        if salt is not None and password_hash is not None:
            updates.extend(("salt=?", "password_hash=?"))
            values.extend((salt, password_hash))
        values.append(username)
        try:
            with self.lock, self.connection:
                cursor = self.connection.execute("UPDATE users SET %s WHERE username=?" % ",".join(updates), values)
                return bool(cursor.rowcount)
        except sqlite3.Error as exc:
            raise StorageError("Akun gagal diperbarui.") from exc

    def delete_user(self, username):
        try:
            with self.lock, self.connection:
                cursor = self.connection.execute("DELETE FROM users WHERE username=?", (username,))
                return bool(cursor.rowcount)
        except sqlite3.Error as exc:
            raise StorageError("Akun gagal dihapus.") from exc

    def enabled_supervisor_count(self):
        with self.lock:
            try:
                return int(self.connection.execute(
                    "SELECT COUNT(*) FROM users WHERE role='SUPERVISOR' AND enabled=1").fetchone()[0])
            except sqlite3.Error as exc:
                raise StorageError("Jumlah Supervisor aktif tidak dapat dibaca.") from exc

    def _index_record(self, collection, key, value):
        self.connection.execute("DELETE FROM record_search WHERE collection=? AND record_key=?", (collection, str(key)))
        self.connection.execute("DELETE FROM record_fields WHERE collection=? AND record_key=?", (collection, str(key)))
        parts = []
        scalar_fields = []
        if isinstance(value, dict):
            for field, field_value in value.items():
                if field_value is None:
                    continue
                if isinstance(field_value, (str, int, float, bool)):
                    scalar = str(field_value).lower() if isinstance(field_value, bool) else str(field_value).strip()
                    if scalar:
                        scalar_fields.append((str(field), scalar))
                parts.extend(self._search_parts(field_value))
        else:
            parts.extend(self._search_parts(value))
        search_text = " ".join(parts).lower()
        self.connection.execute(
            "INSERT OR REPLACE INTO record_search(collection,record_key,search_text) VALUES(?,?,?)",
            (collection, str(key), search_text))
        for field, field_value in set(scalar_fields):
            self.connection.execute(
                "INSERT OR IGNORE INTO record_fields(collection,record_key,field,value) VALUES(?,?,?,?)",
                (collection, str(key), field, field_value))

    @classmethod
    def _search_parts(cls, value):
        if isinstance(value, dict):
            parts = []
            for key, item in value.items():
                parts.append(str(key))
                parts.extend(cls._search_parts(item))
            return parts
        if isinstance(value, (list, tuple)):
            parts = []
            for item in value:
                parts.extend(cls._search_parts(item))
            return parts
        return [] if value is None else [str(value)]

    def _increment_revision(self, updated_at):
        self.connection.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
        self._set_meta("updated_at", updated_at)
        return self._current_revision()

    def _current_revision(self):
        return int(self.connection.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0])

    def _set_meta(self, key, value):
        self.connection.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, value))

    def _write_audit(self, at, username, computer, action, collection, key, reason):
        self.connection.execute(
            "INSERT INTO audit(at,username,computer,action,collection,record_key,reason,detail) VALUES(?,?,?,?,?,?,?,?)",
            (at, username, computer, action, collection, str(key), reason, ""))

    @staticmethod
    def _ensure_collection(collection):
        if collection not in COLLECTIONS:
            raise ValueError("Koleksi tidak dikenal")
