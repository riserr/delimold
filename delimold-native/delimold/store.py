"""SQLite catalog storage and v12 catalog migration for DELIMOLD Native."""
import json
import os
import re
import shutil
import sqlite3
import threading
import time
from pathlib import Path


COLLECTIONS = ("molds", "patterns", "containers", "stickers", "pattern_art",
               "purchases", "projects", "accounts", "events", "deleted")
PUBLIC_COLLECTIONS = ("molds", "patterns", "containers", "stickers", "pattern_art")


def read_catalog_js(path):
    raw = Path(path).read_text(encoding="utf-8-sig").strip()
    prefix = "window.DELIMOLD_DATA="
    if not raw.startswith(prefix):
        raise ValueError("Format catalog.js tidak dikenali")
    return json.loads(raw[len(prefix):].rstrip(";"))


def write_json_atomic(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(str(temp), str(path))


class CatalogStore:
    def __init__(self, database_path):
        self.path = Path(database_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path), timeout=20, check_same_thread=False)
        self.lock = threading.RLock()
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self._schema()

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
            self.connection.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('revision','1')")
            self.connection.execute("INSERT OR IGNORE INTO meta(key,value) VALUES('schema_version','1')")

    def close(self):
        self.connection.close()

    def is_empty(self):
        with self.lock:
            row = self.connection.execute("SELECT COUNT(*) AS n FROM records").fetchone()
            return row["n"] == 0

    def import_catalog(self, catalog, replace=False):
        collections = catalog.get("collections", {})
        with self.lock:
            with self.connection:
                if replace:
                    self.connection.execute("DELETE FROM records")
                for name in COLLECTIONS:
                    rows = collections.get(name, {})
                    if isinstance(rows, list):
                        rows = {str(i): row for i, row in enumerate(rows)}
                    if not isinstance(rows, dict):
                        continue
                    for key, value in rows.items():
                        self.connection.execute(
                            "INSERT OR REPLACE INTO records(collection,record_key,payload) VALUES(?,?,?)",
                            (name, str(key), json.dumps(value, ensure_ascii=False, separators=(",", ":"))))
                for key, value in (("revision", str(catalog.get("revision", 1))),
                                   ("updated_at", str(catalog.get("updatedAt", "")))):
                    self.connection.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)", (key, value))

    def seed_from_js(self, path):
        if not self.is_empty():
            return False
        self.import_catalog(read_catalog_js(path))
        return True

    def get_collection(self, collection):
        with self.lock:
            rows = self.connection.execute(
                "SELECT record_key,payload FROM records WHERE collection=? ORDER BY record_key", (collection,)).fetchall()
            return {row["record_key"]: json.loads(row["payload"]) for row in rows}

    def snapshot(self, include_private=False, include_projects=False):
        names = list(PUBLIC_COLLECTIONS)
        if include_private:
            names.extend(("purchases", "projects"))
        elif include_projects:
            names.append("projects")
        with self.lock:
            collections = {name: self.get_collection(name) for name in names}
            revision = self.connection.execute("SELECT value FROM meta WHERE key='revision'").fetchone()[0]
            return {"schemaVersion": 2, "revision": int(revision), "updatedAt": time.strftime("%Y-%m-%dT%H:%M:%S"),
                    "collections": collections, "events": [], "deleted": []}

    def save_record(self, collection, key, value, username="", computer="", action="save", reason=""):
        if collection not in COLLECTIONS:
            raise ValueError("Koleksi tidak dikenal")
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self.lock:
            with self.connection:
                self.connection.execute("INSERT OR REPLACE INTO records(collection,record_key,payload) VALUES(?,?,?)",
                                        (collection, str(key), json.dumps(value, ensure_ascii=False, separators=(",", ":"))))
                self.connection.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
                self.connection.execute("INSERT INTO audit(at,username,computer,action,collection,record_key,reason,detail) VALUES(?,?,?,?,?,?,?,?)",
                                        (now, username, computer, action, collection, str(key), reason, ""))

    def save_records(self, collection, items, username="", computer="", action="import"):
        if collection not in COLLECTIONS:
            raise ValueError("Koleksi tidak dikenal")
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self.lock:
            with self.connection:
                for key, value in items:
                    self.connection.execute("INSERT OR REPLACE INTO records(collection,record_key,payload) VALUES(?,?,?)",
                                            (collection, str(key), json.dumps(value, ensure_ascii=False, separators=(",", ":"))))
                    self.connection.execute("INSERT INTO audit(at,username,computer,action,collection,record_key,reason,detail) VALUES(?,?,?,?,?,?,?,?)",
                                            (now, username, computer, action, collection, str(key), "", ""))
                if items:
                    self.connection.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")

    def delete_record(self, collection, key, username="", computer="", reason=""):
        with self.lock:
            with self.connection:
                self.connection.execute("DELETE FROM records WHERE collection=? AND record_key=?", (collection, str(key)))
                self.connection.execute("UPDATE meta SET value=CAST(value AS INTEGER)+1 WHERE key='revision'")
                self.connection.execute("INSERT INTO audit(at,username,computer,action,collection,record_key,reason,detail) VALUES(?,?,?,?,?,?,?,?)",
                                        (time.strftime("%Y-%m-%dT%H:%M:%S"), username, computer, "delete", collection, str(key), reason, ""))

    def publish(self, path):
        # Published snapshots intentionally exclude projects and purchases.
        with self.lock:
            snapshot = self.snapshot(include_private=False, include_projects=False)
            root = Path(path)
            root.mkdir(parents=True, exist_ok=True)
            write_json_atomic(root / "catalog.json", snapshot)
            revision = {"revision": snapshot["revision"], "updatedAt": snapshot["updatedAt"], "file": "catalog.json"}
            write_json_atomic(root / "current.json", revision)
            return revision

    def count(self, collection):
        with self.lock:
            row = self.connection.execute("SELECT COUNT(*) AS n FROM records WHERE collection=?", (collection,)).fetchone()
            return int(row["n"])

    def audit_rows(self, limit=200):
        with self.lock:
            rows = self.connection.execute("SELECT * FROM audit ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(row) for row in rows]

    def list_users(self):
        with self.lock:
            rows = self.connection.execute("SELECT username,display_name,role,enabled FROM users ORDER BY username").fetchall()
            return {row["username"]: dict(row) for row in rows}

    def delete_user(self, username):
        with self.lock:
            with self.connection:
                self.connection.execute("DELETE FROM users WHERE username=?", (username,))

