"""LAN API for native DELIMOLD clients. It is an API only; it serves no web page."""
import http.client
import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from .auth import verify_user


def encode_json(value):
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class CatalogClient:
    def __init__(self, host, port=8765):
        self.host = host
        self.port = int(port)
        self.token = None
        self.user = None

    def request(self, method, path, value=None, authenticated=True):
        headers = {"Content-Type": "application/json; charset=utf-8"}
        if authenticated and self.token:
            headers["Authorization"] = "Bearer " + self.token
        conn = http.client.HTTPConnection(self.host, self.port, timeout=6)
        try:
            conn.request(method, path, body=None if value is None else encode_json(value), headers=headers)
            response = conn.getresponse()
            raw = response.read()
            if response.status >= 400:
                try:
                    message = json.loads(raw.decode("utf-8")).get("error", "Koneksi ditolak")
                except Exception:
                    message = "Koneksi ditolak (HTTP %s)" % response.status
                raise RuntimeError(message)
            return json.loads(raw.decode("utf-8")) if raw else {}
        finally:
            conn.close()

    def login(self, username, password):
        result = self.request("POST", "/api/login", {"username": username, "password": password}, authenticated=False)
        self.token = result["token"]
        self.user = result["user"]
        return self.user

    def catalog(self):
        role = (self.user or {}).get("role")
        scope = "supervisor" if role == "SUPERVISOR" else ("engineer" if role == "ENGINEER" else "viewer")
        return self.request("GET", "/api/catalog?scope=" + scope)

    def save(self, collection, key, value, action="save", reason=""):
        return self.request("POST", "/api/record", {"collection": collection, "key": key,
                                                         "value": value, "action": action, "reason": reason})

    def delete(self, collection, key, reason=""):
        return self.request("POST", "/api/delete", {"collection": collection, "key": key, "reason": reason})

    def import_records(self, collection, items):
        return self.request("POST", "/api/import", {"collection": collection, "records": items})

    def accounts(self):
        return self.request("GET", "/api/accounts")

    def history(self):
        return self.request("GET", "/api/history")

    def save_account(self, payload):
        return self.request("POST", "/api/account", payload)

    def delete_account(self, username):
        return self.request("POST", "/api/account/delete", {"username": username})


class CatalogApi:
    def __init__(self, store, host="0.0.0.0", port=8765, publish_path=None):
        self.store = store
        self.host = host
        self.port = int(port)
        self.publish_path = publish_path
        self.sessions = {}
        self.server = None
        self.thread = None

    def start(self):
        api = self

        class Handler(BaseHTTPRequestHandler):
            server_version = "DELIMOLD-Native/1"

            def log_message(self, fmt, *args):
                return

            def send_json(self, status, value):
                raw = encode_json(value)
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(raw)

            def body(self):
                length = int(self.headers.get("Content-Length", "0"))
                if length > 20_000_000:
                    raise ValueError("Permintaan terlalu besar")
                raw = self.rfile.read(length)
                return json.loads(raw.decode("utf-8")) if raw else {}

            def user(self):
                value = self.headers.get("Authorization", "")
                token = value[7:] if value.startswith("Bearer ") else ""
                return api.sessions.get(token)

            def do_GET(self):
                split = urlsplit(self.path)
                path = split.path
                if path == "/api/status":
                    self.send_json(200, {"ok": True, "revision": api.store.snapshot()["revision"]})
                    return
                user = self.user()
                if not user:
                    self.send_json(401, {"error": "Silakan login ulang"})
                    return
                if path == "/api/catalog":
                    scope = (split.query.split("=", 1)[1] if "=" in split.query else "viewer")
                    self.send_json(200, api.store.snapshot(include_private=(user["role"] == "SUPERVISOR" and scope == "supervisor"),
                                                           include_projects=user["role"] in ("SUPERVISOR", "ENGINEER")))
                    return
                if path == "/api/accounts":
                    if user["role"] != "SUPERVISOR":
                        self.send_json(403, {"error": "Management akun hanya untuk Supervisor"})
                        return
                    self.send_json(200, api.store.list_users())
                    return
                if path == "/api/history":
                    self.send_json(200, api.store.audit_rows())
                    return
                self.send_json(404, {"error": "Alamat API tidak dikenal"})

            def do_POST(self):
                path = urlsplit(self.path).path
                try:
                    payload = self.body()
                except Exception as exc:
                    self.send_json(400, {"error": str(exc)})
                    return
                if path == "/api/login":
                    user = verify_user(api.store, payload.get("username", ""), payload.get("password", ""))
                    if not user:
                        self.send_json(401, {"error": "Nama akun atau password salah"})
                        return
                    token = secrets.token_urlsafe(24)
                    api.sessions[token] = user
                    self.send_json(200, {"token": token, "user": user})
                    return
                user = self.user()
                if not user:
                    self.send_json(401, {"error": "Silakan login ulang"})
                    return
                if user["role"] not in ("SUPERVISOR", "ENGINEER"):
                    self.send_json(403, {"error": "Akun ini hanya dapat melihat data"})
                    return
                try:
                    if path in ("/api/account", "/api/account/delete"):
                        if user["role"] != "SUPERVISOR":
                            self.send_json(403, {"error": "Management akun hanya untuk Supervisor"})
                            return
                        if path == "/api/account":
                            from .auth import create_user
                            username = payload.get("username", "").strip()
                            with api.store.lock:
                                current = api.store.connection.execute("SELECT username FROM users WHERE username=?", (username,)).fetchone()
                            if payload.get("password"):
                                create_user(api.store, username, payload.get("display_name", username), payload.get("role", "ENGINEER"), payload["password"])
                            elif current:
                                with api.store.lock:
                                    with api.store.connection:
                                        api.store.connection.execute("UPDATE users SET display_name=?,role=?,enabled=? WHERE username=?",
                                            (payload.get("display_name", username), payload.get("role", "ENGINEER"), int(bool(payload.get("enabled", True))), username))
                            else:
                                raise ValueError("Password wajib diisi untuk akun baru")
                            self.send_json(200, {"ok": True})
                            return
                        target = payload.get("username", "")
                        if target == user["username"]:
                            raise ValueError("Akun yang sedang dipakai tidak dapat dihapus")
                        with api.store.lock:
                            count = api.store.connection.execute("SELECT COUNT(*) FROM users WHERE role='SUPERVISOR' AND enabled=1").fetchone()[0]
                            victim = api.store.connection.execute("SELECT role,enabled FROM users WHERE username=?", (target,)).fetchone()
                        if victim and victim["role"] == "SUPERVISOR" and victim["enabled"] and count <= 1:
                            raise ValueError("Supervisor aktif terakhir tidak dapat dihapus")
                        api.store.delete_user(target)
                        self.send_json(200, {"ok": True})
                        return
                    if path == "/api/record":
                        if payload.get("collection") not in ("molds", "patterns", "containers", "stickers", "pattern_art", "purchases", "projects"):
                            raise ValueError("Koleksi ini tidak dapat diubah lewat API")
                        if payload.get("collection") == "purchases" and user["role"] != "SUPERVISOR":
                            self.send_json(403, {"error": "Data pembelian hanya untuk Supervisor"})
                            return
                        api.store.save_record(payload["collection"], payload["key"], payload["value"],
                                              user["username"], self.client_address[0], payload.get("action", "save"), payload.get("reason", ""))
                        if payload.get("collection") in ("molds", "patterns", "containers", "stickers", "pattern_art") and api.publish_path:
                            api.store.publish(api.publish_path)
                        result = {"ok": True, "revision": api.store.snapshot()["revision"]}
                    elif path == "/api/import":
                        collection = payload.get("collection")
                        if collection not in ("molds", "patterns", "containers", "stickers", "pattern_art", "projects", "purchases"):
                            raise ValueError("Koleksi ini tidak dapat diimpor lewat API")
                        if collection == "purchases" and user["role"] != "SUPERVISOR":
                            self.send_json(403, {"error": "Data pembelian hanya untuk Supervisor"})
                            return
                        records = payload.get("records", [])
                        if len(records) > 10000:
                            raise ValueError("Maksimal 10.000 baris per proses impor")
                        api.store.save_records(collection, [(item["key"], item["value"]) for item in records],
                                              user["username"], self.client_address[0], "import")
                        if collection in ("molds", "patterns", "containers", "stickers", "pattern_art") and api.publish_path:
                            api.store.publish(api.publish_path)
                        result = {"ok": True, "count": len(records), "revision": api.store.snapshot()["revision"]}
                    elif path == "/api/delete":
                        if user["role"] != "SUPERVISOR":
                            self.send_json(403, {"error": "Hanya Supervisor yang dapat menghapus data"})
                            return
                        api.store.delete_record(payload["collection"], payload["key"], user["username"],
                                                self.client_address[0], payload.get("reason", ""))
                        if payload.get("collection") in ("molds", "patterns", "containers", "stickers", "pattern_art") and api.publish_path:
                            api.store.publish(api.publish_path)
                        result = {"ok": True, "revision": api.store.snapshot()["revision"]}
                    elif path == "/api/publish":
                        if user["role"] != "SUPERVISOR":
                            self.send_json(403, {"error": "Publikasi hanya dapat dilakukan Supervisor"})
                            return
                        if not api.publish_path:
                            raise ValueError("Folder publikasi Salak belum diatur")
                        result = api.store.publish(api.publish_path)
                        result["ok"] = True
                    else:
                        self.send_json(404, {"error": "Alamat API tidak dikenal"})
                        return
                except Exception as exc:
                    self.send_json(400, {"error": str(exc)})
                    return
                self.send_json(200, result)

        self.server = ThreadingHTTPServer((self.host, self.port), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, name="DelimoldApi", daemon=True)
        self.thread.start()
        return self

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

