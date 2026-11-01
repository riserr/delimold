"""Password helpers; no password is stored in plain text."""
import base64
import hashlib
import hmac
import os


def hash_password(password, salt=None):
    if not (4 <= len(password) <= 12):
        raise ValueError("Password harus 4–12 karakter")
    salt = salt or os.urandom(16)
    return (base64.b64encode(salt).decode("ascii"), derive_password(password, salt))


def derive_password(password, salt):
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return base64.b64encode(digest).decode("ascii")


def create_user(store, username, display_name, role, password):
    username = username.strip()
    if not username or role not in ("SUPERVISOR", "ENGINEER", "VIEWER"):
        raise ValueError("Nama akun atau peran tidak valid")
    salt, digest = hash_password(password)
    with store.lock:
        with store.connection:
            store.connection.execute("INSERT OR REPLACE INTO users(username,display_name,role,salt,password_hash,enabled) VALUES(?,?,?,?,?,1)",
                                     (username, display_name.strip() or username, role, salt, digest))


def verify_user(store, username, password):
    with store.lock:
        row = store.connection.execute("SELECT * FROM users WHERE username=? AND enabled=1", (username.strip(),)).fetchone()
    if not row:
        return None
    salt = base64.b64decode(row["salt"])
    digest = derive_password(password, salt)
    if not hmac.compare_digest(digest, row["password_hash"]):
        return None
    return {"username": row["username"], "display_name": row["display_name"], "role": row["role"]}

