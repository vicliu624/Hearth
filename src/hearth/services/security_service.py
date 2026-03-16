from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import re
import secrets
from typing import Any

from hearth.core.config import HearthSettings
from hearth.services.config_service import ConfigService
from hearth.storage.db import Database


BUILTIN_ROLE_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "owner",
        "label": "Owner",
        "description": "Full control over node, security, tokens, and maintenance.",
        "permissions": ["read", "operate", "configure", "security", "tokens", "maintenance"],
    },
    {
        "name": "admin",
        "label": "Admin",
        "description": "Manage node operations, configuration, and observability.",
        "permissions": ["read", "operate", "configure", "maintenance"],
    },
    {
        "name": "operator",
        "label": "Operator",
        "description": "Operate runtime and interfaces without changing security policies.",
        "permissions": ["read", "operate", "maintenance"],
    },
    {
        "name": "viewer",
        "label": "Viewer",
        "description": "Read-only access to dashboards, logs, and audit information.",
        "permissions": ["read"],
    },
    {
        "name": "service_manager",
        "label": "Service Manager",
        "description": "Manage service-style automation and maintenance workflows.",
        "permissions": ["read", "operate", "maintenance", "tokens"],
    },
]

ROLE_INDEX = {item["name"]: item for item in BUILTIN_ROLE_DEFINITIONS}
MANAGEMENT_ROLES = {"owner", "admin", "operator", "service_manager"}
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,48}$")
TOKEN_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,64}$")
ROLE_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,48}$")
KNOWN_PERMISSIONS = {"read", "operate", "configure", "security", "tokens", "maintenance"}


class SecurityService:
    def __init__(self, settings: HearthSettings, database: Database, config_service: ConfigService | None = None) -> None:
        self.settings = settings
        self.database = database
        self.config_service = config_service

    def _role_definitions(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = [
            {
                **item,
                "builtin": True,
                "editable": False,
            }
            for item in BUILTIN_ROLE_DEFINITIONS
        ]
        for item in self.settings.roles:
            payload = item.model_dump(mode="json")
            name = str(payload.get("name") or "").strip().lower().replace(" ", "_")
            if not name or name in ROLE_INDEX:
                continue
            permissions = sorted({permission.strip().lower() for permission in payload.get("permissions") or [] if permission.strip()})
            rows.append(
                {
                    "name": name,
                    "label": payload.get("label") or name.replace("_", " ").title(),
                    "description": payload.get("description") or "",
                    "permissions": permissions,
                    "builtin": False,
                    "editable": True,
                }
            )
        return sorted(rows, key=lambda item: (not item["builtin"], item["name"]))

    def _role_index(self) -> dict[str, dict[str, Any]]:
        return {item["name"]: item for item in self._role_definitions()}

    def _normalize_permissions(self, permissions: list[str] | None) -> list[str]:
        normalized = sorted({str(permission).strip().lower() for permission in permissions or [] if str(permission).strip()})
        invalid = [permission for permission in normalized if permission not in KNOWN_PERMISSIONS]
        if invalid:
            raise ValueError(f"unknown permissions: {', '.join(invalid)}")
        if not normalized:
            raise ValueError("at least one permission is required")
        return normalized

    def _save_custom_roles(self, roles: list[dict[str, Any]], *, source: str, summary: str, payload: dict[str, Any]) -> None:
        if self.config_service is None:
            raise ValueError("config service is not available for role management")
        settings_payload = self.settings.model_dump(mode="json", exclude={"config_path"}, exclude_none=True)
        settings_payload["roles"] = roles
        result = self.config_service.save(settings_payload)
        if not result.get("saved"):
            raise ValueError("failed to save role configuration")
        self.database.record_event(source, summary, source="security_service", payload=payload)

    def normalize_role(self, value: str | None) -> str:
        role = (value or "viewer").strip().lower().replace(" ", "_")
        return role if role in self._role_index() else "viewer"

    def role_permissions(self, role: str | None) -> set[str]:
        normalized_role = self.normalize_role(role)
        definition = self._role_index().get(normalized_role, self._role_index()["viewer"])
        return set(definition.get("permissions", []))

    def list_roles(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._role_definitions()]

    def get_role(self, role_name: str) -> dict[str, Any] | None:
        return self._role_index().get(self.normalize_role(role_name))

    def create_role(
        self,
        *,
        name: str,
        label: str | None = None,
        description: str | None = None,
        permissions: list[str] | None = None,
    ) -> dict[str, Any]:
        candidate = str(name or "").strip().lower().replace(" ", "_")
        if not ROLE_NAME_PATTERN.match(candidate):
            raise ValueError("role name must be 3-48 chars using letters, numbers, dot, dash, or underscore")
        if candidate in ROLE_INDEX or candidate in {role["name"] for role in self.list_roles()}:
            raise ValueError("role already exists")
        role = {
            "name": candidate,
            "label": (label or candidate.replace("_", " ").title()).strip(),
            "description": (description or "").strip(),
            "permissions": self._normalize_permissions(permissions),
        }
        custom_roles = [item.model_dump(mode="json") for item in self.settings.roles]
        custom_roles.append(role)
        self._save_custom_roles(
            custom_roles,
            source="security.role_created",
            summary=f"role {candidate} created",
            payload={"role": role},
        )
        created = self.get_role(candidate)
        if created is None:
            raise ValueError("created role could not be loaded")
        return created

    def update_role(
        self,
        role_name: str,
        *,
        label: str | None = None,
        description: str | None = None,
        permissions: list[str] | None = None,
    ) -> dict[str, Any]:
        normalized_name = self.normalize_role(role_name)
        if normalized_name in ROLE_INDEX:
            raise ValueError("built-in roles cannot be modified")
        custom_roles = [item.model_dump(mode="json") for item in self.settings.roles]
        updated = None
        for item in custom_roles:
            candidate = str(item.get("name") or "").strip().lower().replace(" ", "_")
            if candidate != normalized_name:
                continue
            if label is not None:
                item["label"] = label.strip() or normalized_name.replace("_", " ").title()
            if description is not None:
                item["description"] = description.strip()
            if permissions is not None:
                item["permissions"] = self._normalize_permissions(permissions)
            updated = item
            break
        if updated is None:
            raise ValueError("role not found")
        self._save_custom_roles(
            custom_roles,
            source="security.role_updated",
            summary=f"role {normalized_name} updated",
            payload={"role": updated},
        )
        refreshed = self.get_role(normalized_name)
        if refreshed is None:
            raise ValueError("updated role could not be loaded")
        return refreshed

    def delete_role(self, role_name: str) -> dict[str, Any]:
        normalized_name = self.normalize_role(role_name)
        if normalized_name in ROLE_INDEX:
            raise ValueError("built-in roles cannot be deleted")
        custom_roles = [item.model_dump(mode="json") for item in self.settings.roles]
        remaining = [
            item
            for item in custom_roles
            if str(item.get("name") or "").strip().lower().replace(" ", "_") != normalized_name
        ]
        if len(remaining) == len(custom_roles):
            raise ValueError("role not found")
        in_use = [user["username"] for user in self.list_users() if str(user.get("role") or "viewer") == normalized_name]
        in_use.extend(
            token["token_name"] for token in self.list_api_tokens() if str(token.get("role") or "viewer") == normalized_name
        )
        if in_use:
            raise ValueError("role is still in use by users or tokens")
        self._save_custom_roles(
            remaining,
            source="security.role_deleted",
            summary=f"role {normalized_name} deleted",
            payload={"role_name": normalized_name},
        )
        return {"deleted": True, "role_name": normalized_name}

    def list_users(self) -> list[dict[str, Any]]:
        token_counts: dict[str, int] = {}
        for token in self.database.list_api_tokens():
            owner_username = token.get("owner_username")
            if owner_username:
                token_counts[owner_username] = token_counts.get(owner_username, 0) + 1

        users = self.database.list_users()
        for user in users:
            user["builtin"] = False
            user["token_count"] = token_counts.get(user["username"], 0)

        builtin = {
            "username": "admin",
            "display_name": "Built-in Admin",
            "role": "owner",
            "enabled": True,
            "created_at": None,
            "updated_at": None,
            "last_login_at": None,
            "builtin": True,
            "token_count": 1,
        }
        return [builtin, *users]

    def get_user(self, username: str) -> dict[str, Any] | None:
        if username == "admin":
            return next((item for item in self.list_users() if item["username"] == "admin"), None)
        user = self.database.get_user(username)
        if user is None:
            return None
        user["builtin"] = False
        return user

    def create_user(self, *, username: str, display_name: str | None = None, role: str = "viewer") -> dict[str, Any]:
        candidate = username.strip()
        if candidate == "admin":
            raise ValueError("admin is reserved")
        if not USERNAME_PATTERN.match(candidate):
            raise ValueError("username must be 3-48 chars using letters, numbers, dot, dash, or underscore")
        user = self.database.upsert_user(
            username=candidate,
            display_name=(display_name or "").strip() or None,
            role=self.normalize_role(role),
            enabled=True,
        )
        self.database.record_event(
            "security.user_created",
            f"user {candidate} created",
            source="security_service",
            payload={"username": candidate, "role": user["role"]},
        )
        user["builtin"] = False
        return user

    def set_user_enabled(self, username: str, enabled: bool) -> dict[str, Any]:
        if username == "admin":
            raise ValueError("built-in admin cannot be disabled")
        user = self.database.set_user_enabled(username, enabled)
        if user is None:
            raise ValueError("user not found")
        self.database.record_event(
            "security.user_updated",
            f"user {username} {'enabled' if enabled else 'disabled'}",
            source="security_service",
            payload={"username": username, "enabled": enabled},
        )
        user["builtin"] = False
        return user

    def set_user_role(self, username: str, role: str) -> dict[str, Any]:
        if username == "admin":
            raise ValueError("built-in admin role cannot be changed")
        existing = self.database.get_user(username)
        if existing is None:
            raise ValueError("user not found")
        user = self.database.upsert_user(
            username=username,
            display_name=existing.get("display_name"),
            role=self.normalize_role(role),
            enabled=bool(existing.get("enabled", True)),
        )
        self.database.record_event(
            "security.user_updated",
            f"user {username} role changed",
            source="security_service",
            payload={"username": username, "role": user["role"]},
        )
        user["builtin"] = False
        return user

    def list_api_tokens(self) -> list[dict[str, Any]]:
        builtin_secret = self.settings.security.admin_token.strip()
        builtin = {
            "token_name": "admin-token",
            "token_hint": f"...{builtin_secret[-4:]}" if builtin_secret else "-",
            "owner_username": "admin",
            "role": "owner",
            "scopes": ["*"],
            "enabled": bool(builtin_secret),
            "created_at": None,
            "last_used_at": None,
            "expires_at": None,
            "builtin": True,
        }
        tokens = self.database.list_api_tokens()
        for token in tokens:
            token["builtin"] = False
        return [builtin, *tokens]

    def create_api_token(
        self,
        *,
        token_name: str,
        owner_username: str | None,
        role: str,
        scopes: list[str] | None = None,
        expires_in_days: int | None = None,
    ) -> dict[str, Any]:
        candidate = token_name.strip()
        if not TOKEN_NAME_PATTERN.match(candidate):
            raise ValueError("token name must be 3-64 chars using letters, numbers, dot, dash, or underscore")
        owner = (owner_username or "").strip() or None
        if owner and owner != "admin" and self.database.get_user(owner) is None:
            raise ValueError("owner user not found")
        normalized_role = self.normalize_role(role)
        normalized_scopes = [scope.strip() for scope in (scopes or []) if scope.strip()]
        secret = f"htk_{secrets.token_urlsafe(24)}"
        token_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        expires_at = None
        if expires_in_days and expires_in_days > 0:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
        token = self.database.create_api_token(
            token_name=candidate,
            token_hash=token_hash,
            token_hint=f"...{secret[-4:]}",
            owner_username=owner,
            role=normalized_role,
            scopes=normalized_scopes,
            expires_at=expires_at,
        )
        token["token"] = secret
        token["builtin"] = False
        self.database.record_event(
            "security.token_created",
            f"api token {candidate} created",
            source="security_service",
            payload={"token_name": candidate, "owner_username": owner, "role": normalized_role},
        )
        return token

    def set_api_token_enabled(self, token_name: str, enabled: bool) -> dict[str, Any]:
        token = self.database.set_api_token_enabled(token_name, enabled)
        if token is None:
            raise ValueError("token not found")
        token["builtin"] = False
        self.database.record_event(
            "security.token_updated",
            f"api token {token_name} {'enabled' if enabled else 'disabled'}",
            source="security_service",
            payload={"token_name": token_name, "enabled": enabled},
        )
        return token

    def authenticate_token(self, token: str) -> dict[str, Any] | None:
        candidate = token.strip()
        configured = self.settings.security.admin_token.strip()
        if configured and secrets.compare_digest(candidate, configured):
            return {
                "subject": "admin",
                "source": "settings",
                "role": "owner",
                "scopes": ["*"],
                "token_name": "admin-token",
            }

        token_hash = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        stored = self.database.get_api_token_by_hash(token_hash)
        if stored is None or not stored.get("enabled"):
            return None

        expires_at = stored.get("expires_at")
        if expires_at:
            try:
                deadline = datetime.fromisoformat(expires_at)
            except ValueError:
                deadline = None
            if deadline is not None:
                if deadline.tzinfo is None:
                    deadline = deadline.replace(tzinfo=timezone.utc)
                if deadline.astimezone(timezone.utc) <= datetime.now(timezone.utc):
                    return None

        owner_username = stored.get("owner_username")
        if owner_username and owner_username != "admin":
            user = self.database.get_user(owner_username)
            if user is None or not user.get("enabled"):
                return None
            self.database.touch_user_login(owner_username)

        self.database.touch_api_token(stored["token_name"])
        return {
            "subject": owner_username or stored["token_name"],
            "source": "database",
            "role": self.normalize_role(str(stored.get("role") or "viewer")),
            "scopes": list(stored.get("scopes") or []),
            "token_name": stored["token_name"],
        }

    def principal_has_permission(self, principal: dict[str, Any] | None, permission: str) -> bool:
        if not principal:
            return False

        normalized_permission = (permission or "read").strip().lower()
        role_permissions = self.role_permissions(str(principal.get("role") or "viewer"))
        if "*" not in role_permissions and normalized_permission not in role_permissions:
            return False

        scopes = [str(scope).strip().lower() for scope in principal.get("scopes") or [] if str(scope).strip()]
        if not scopes or "*" in scopes:
            return True
        return normalized_permission in scopes

    def has_management_access(self, principal: dict[str, Any] | None) -> bool:
        return self.principal_has_permission(principal, "operate")
