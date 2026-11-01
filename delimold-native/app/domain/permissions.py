"""Role and collection access rules; independent from UI and storage."""
from .errors import PermissionDenied


PUBLIC_COLLECTIONS = ("molds", "patterns", "containers", "stickers", "pattern_art")
ENGINEER_COLLECTIONS = PUBLIC_COLLECTIONS + ("projects",)
SUPERVISOR_COLLECTIONS = ENGINEER_COLLECTIONS + ("purchases", "accounts", "history")


def require_access(actor, action, collection):
    role = actor.role if hasattr(actor, "role") else actor.get("role", "VIEWER")
    if role == "SUPERVISOR":
        return
    if action == "read":
        allowed = PUBLIC_COLLECTIONS if role == "VIEWER" else ENGINEER_COLLECTIONS
        if collection in allowed:
            return
    elif action in ("create", "edit", "delete", "status", "import"):
        if role == "ENGINEER" and collection in ENGINEER_COLLECTIONS:
            return
    raise PermissionDenied("Peran %s tidak diizinkan untuk %s %s." % (role, action, collection))


def can_manage_accounts(actor):
    role = actor.role if hasattr(actor, "role") else actor.get("role", "VIEWER")
    if role != "SUPERVISOR":
        raise PermissionDenied("Management akun hanya dapat diakses Supervisor.")
