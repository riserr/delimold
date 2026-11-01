"""Account authentication, setup, and administration workflows."""
import base64
import hashlib
import hmac
import os
from typing import Dict, Tuple

from app.application.dto import (AuditEntry, AuditQuery, AuthenticationRequest,
                                InitialSupervisorRequest, UserDeleteRequest,
                                UserEnabledRequest, UserSaveRequest, UserSummary)
from app.application.ports import CatalogRepository
from app.domain.errors import AuthenticationFailed, DataNotFound, ValidationError
from app.domain.models import Actor
from app.domain.permissions import can_manage_accounts, require_access
from app.domain.validation import validate_user


class AccountUseCases:
    def __init__(self, repository: CatalogRepository):
        self._repository = repository

    def needs_initial_setup(self) -> bool:
        return self._repository.user_count() == 0

    def authenticate(self, request: AuthenticationRequest) -> Actor:
        credential = self._repository.get_user_credentials(request.username.strip())
        if not credential:
            raise AuthenticationFailed("Nama akun atau password salah.")
        salt = base64.b64decode(credential["salt"])
        digest = hashlib.pbkdf2_hmac("sha256", request.password.encode("utf-8"), salt, 120000)
        if not hmac.compare_digest(base64.b64encode(digest).decode("ascii"), credential["password_hash"]):
            raise AuthenticationFailed("Nama akun atau password salah.")
        return Actor(credential["username"], credential["display_name"], credential["role"], request.computer)

    def setup_initial_supervisor(self, request: InitialSupervisorRequest) -> None:
        username = request.username.strip()
        validate_user(username, "SUPERVISOR", request.password, password_required=True)
        if self._repository.user_count():
            raise ValidationError("Supervisor awal sudah dibuat.")
        salt, password_hash = self._hash_password(request.password)
        self._repository.create_user(username, request.display_name.strip() or username,
                                     "SUPERVISOR", salt, password_hash)

    def save_user(self, request: UserSaveRequest) -> None:
        can_manage_accounts(request.actor)
        username = request.username.strip()
        validate_user(username, request.role, request.password,
                      password_required=not request.existing)
        if not request.existing:
            salt, password_hash = self._hash_password(request.password)
            self._repository.create_user(username, request.display_name.strip() or username,
                                         request.role, salt, password_hash)
            return
        if request.password:
            salt, password_hash = self._hash_password(request.password)
            self._repository.update_user(username, request.display_name.strip() or username,
                                         request.role, enabled=request.enabled,
                                         salt=salt, password_hash=password_hash)
        else:
            self._repository.update_user(username, request.display_name.strip() or username,
                                         request.role, enabled=request.enabled)

    def set_user_enabled(self, request: UserEnabledRequest) -> None:
        can_manage_accounts(request.actor)
        target = self._repository.list_users().get(request.username)
        if not target:
            raise DataNotFound("Akun tidak ditemukan.")
        if target.get("role") == "SUPERVISOR" and target.get("enabled") and not request.enabled:
            if self._repository.enabled_supervisor_count() <= 1:
                raise ValidationError("Supervisor aktif terakhir tidak dapat dinonaktifkan.")
        self._repository.update_user(request.username, target.get("display_name", request.username),
                                     target.get("role", "ENGINEER"), enabled=request.enabled)

    def user_count(self) -> int:
        return self._repository.user_count()

    def delete_user(self, request: UserDeleteRequest) -> None:
        can_manage_accounts(request.actor)
        if request.username == request.actor.username:
            raise ValidationError("Akun yang sedang dipakai tidak dapat dihapus.")
        target = self._repository.list_users().get(request.username)
        if not target:
            raise DataNotFound("Akun tidak ditemukan.")
        if target.get("role") == "SUPERVISOR" and target.get("enabled") and self._repository.enabled_supervisor_count() <= 1:
            raise ValidationError("Supervisor aktif terakhir tidak dapat dihapus.")
        self._repository.delete_user(request.username)

    def list_users(self, actor: Actor) -> Dict[str, UserSummary]:
        can_manage_accounts(actor)
        return {username: UserSummary(
            username=row.get("username", username), display_name=row.get("display_name", username),
            role=row.get("role", "VIEWER"), enabled=bool(row.get("enabled", False)))
                for username, row in self._repository.list_users().items()}

    def audit_rows(self, actor: Actor, query: AuditQuery = AuditQuery()) -> Tuple[AuditEntry, ...]:
        require_access(actor, "read", "history")
        return tuple(AuditEntry(
            id=int(row.get("id", 0)), at=str(row.get("at", "")),
            action=str(row.get("action", "")), collection=str(row.get("collection", "")),
            record_key=str(row.get("record_key", "")), username=str(row.get("username", "")),
            computer=str(row.get("computer", "")), reason=str(row.get("reason", "")),
            detail=str(row.get("detail", "")))
            for row in self._repository.audit_rows(query.limit))

    @staticmethod
    def _hash_password(password: str) -> Tuple[str, str]:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
        return base64.b64encode(salt).decode("ascii"), base64.b64encode(digest).decode("ascii")
