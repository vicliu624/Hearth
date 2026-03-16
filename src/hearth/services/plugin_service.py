from __future__ import annotations

from datetime import datetime, timezone
import base64
import binascii
import hashlib
import json
from pathlib import Path
from typing import Any
from urllib import request as urllib_request
from urllib.parse import urlparse

from hearth.core.config import HearthSettings
from hearth.crypto.ed25519 import verify as verify_ed25519
from hearth.services.config_service import ConfigService


TRUSTED_PLUGIN_SOURCES = {"builtin", "local", "packaged", "signed"}
SOURCE_SYNC_STATES = {"ready", "idle", "paused", "disabled", "running", "error"}
SOURCE_SIGNATURE_STATES = {"trusted", "verified", "invalid", "missing", "not_required"}

DEFAULT_PLUGIN_SOURCE_CATALOG = {
    "builtin": {
        "label": "Built-in",
        "description": "Plugins bundled with Hearth itself.",
        "index_url": "hearth://builtin",
        "available_plugins": ["metrics_exporter"],
    },
    "local": {
        "label": "Local",
        "description": "Plugins declared directly in the local node configuration.",
        "index_url": "file://local-config",
        "available_plugins": [],
    },
    "community": {
        "label": "Community",
        "description": "Community-maintained plugin catalog for shared extensions and bridges.",
        "index_url": "hearth://community-index",
        "available_plugins": ["matrix_bridge", "mqtt_bridge", "webhook_bridge"],
    },
    "signed": {
        "label": "Signed",
        "description": "Verified packaged plugins from trusted channels.",
        "index_url": "hearth://signed-index",
        "available_plugins": [],
    },
    "experimental": {
        "label": "Experimental",
        "description": "Unstable or preview plugins that may require extra review.",
        "index_url": "hearth://experimental-index",
        "available_plugins": [],
    },
}

DEFAULT_PLUGIN_MANIFESTS: dict[str, list[dict[str, Any]]] = {
    "builtin": [
        {
            "name": "metrics_exporter",
            "version": "1.0.0",
            "type": "observability",
            "description": "Exports Hearth metrics and runtime counters for scraping and dashboards.",
            "permissions": ["read"],
            "depends_on": [],
            "config": {"path": "/metrics"},
        }
    ],
    "community": [
        {
            "name": "matrix_bridge",
            "version": "1.2.0",
            "type": "bridge",
            "description": "Bridge Reticulum events and selected messages into Matrix rooms.",
            "permissions": ["operate", "read"],
            "depends_on": ["metrics_exporter"],
            "config": {"transport": "matrix"},
        },
        {
            "name": "mqtt_bridge",
            "version": "1.1.0",
            "type": "bridge",
            "description": "Publish node telemetry and bridge payloads to MQTT brokers.",
            "permissions": ["operate", "read"],
            "depends_on": ["metrics_exporter"],
            "config": {"transport": "mqtt"},
        },
        {
            "name": "webhook_bridge",
            "version": "1.0.1",
            "type": "bridge",
            "description": "Deliver alerts and selected events to webhook receivers.",
            "permissions": ["operate", "read"],
            "depends_on": [],
            "config": {"transport": "webhook"},
        },
    ],
}


class PluginService:
    def __init__(self, settings: HearthSettings, config_service: ConfigService) -> None:
        self.settings = settings
        self.config_service = config_service

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _source_index_path(self) -> Path:
        return self.settings.data_dir / "plugin-sources-index.json"

    def _plugin_state_path(self) -> Path:
        return self.settings.plugin_state_path

    def _load_plugin_state(self) -> dict[str, Any]:
        path = self._plugin_state_path()
        if not path.exists():
            return {"plugins": {}, "history": []}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"plugins": {}, "history": []}
        if not isinstance(payload, dict):
            return {"plugins": {}, "history": []}
        plugins = payload.get("plugins") if isinstance(payload.get("plugins"), dict) else {}
        history = payload.get("history") if isinstance(payload.get("history"), list) else []
        return {"plugins": plugins, "history": history}

    def _save_plugin_state(self, payload: dict[str, Any]) -> None:
        path = self._plugin_state_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _record_plugin_operation(
        self,
        action: str,
        *,
        plugin_name: str,
        payload: dict[str, Any],
        state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        state = state or self._load_plugin_state()
        history = list(state.get("history") or [])
        history.insert(
            0,
            {
                "action": action,
                "plugin_name": plugin_name,
                "payload": payload,
                "created_at": self._now_iso(),
            },
        )
        state["history"] = history[:100]
        return state

    def _normalize_digest(self, value: Any) -> str | None:
        text = str(value or "").strip().lower()
        if not text:
            return None
        if text.startswith("sha256:"):
            text = text.split(":", 1)[1].strip()
        if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
            return None
        return text

    def _normalize_ed25519_token(self, value: Any, *, expected_size: int) -> str | None:
        text = str(value or "").strip()
        if not text:
            return None
        lowered = text.lower()
        if lowered.startswith("ed25519:"):
            text = text.split(":", 1)[1].strip()
        normalized_hex = text.lower()
        if len(normalized_hex) == expected_size * 2 and all(character in "0123456789abcdef" for character in normalized_hex):
            return normalized_hex
        padded = text + ("=" * (-len(text) % 4))
        try:
            decoded = base64.b64decode(padded, validate=True)
        except (binascii.Error, ValueError):
            return None
        if len(decoded) != expected_size:
            return None
        return decoded.hex()

    def _public_key_value(self, value: Any) -> str | None:
        normalized = self._normalize_ed25519_token(value, expected_size=32)
        if normalized is None:
            return None
        return f"ed25519:{normalized}"

    def _signature_algorithm_value(self, value: Any) -> str | None:
        normalized = str(value or "").strip().lower()
        if normalized in {"ed25519", "sha256"}:
            return normalized
        return None

    def _parse_signature(self, value: Any) -> tuple[str | None, str | None]:
        text = str(value or "").strip()
        if not text:
            return None, None
        algorithm: str | None = None
        raw_value = text
        if ":" in text:
            prefix, suffix = text.split(":", 1)
            candidate = prefix.strip().lower()
            if candidate in {"sha256", "ed25519"}:
                algorithm = candidate
                raw_value = suffix.strip()
        if algorithm == "sha256":
            normalized_digest = self._normalize_digest(raw_value)
            return ("sha256", f"sha256:{normalized_digest}") if normalized_digest else (None, None)
        if algorithm == "ed25519":
            normalized_signature = self._normalize_ed25519_token(raw_value, expected_size=64)
            return ("ed25519", f"ed25519:{normalized_signature}") if normalized_signature else (None, None)
        normalized_digest = self._normalize_digest(text)
        if normalized_digest is not None:
            return "sha256", f"sha256:{normalized_digest}"
        normalized_signature = self._normalize_ed25519_token(text, expected_size=64)
        if normalized_signature is not None:
            return "ed25519", f"ed25519:{normalized_signature}"
        return None, None

    def _signature_value(self, value: Any) -> str | None:
        _, normalized = self._parse_signature(value)
        return normalized

    def _default_source_entries(self) -> dict[str, dict[str, Any]]:
        return {
            name: {
                "source": name,
                "label": payload["label"],
                "description": payload["description"],
                "index_url": payload["index_url"],
                "available_plugins": list(payload.get("available_plugins") or []),
                "trusted_source": name in TRUSTED_PLUGIN_SOURCES,
                "signature_status": "trusted" if name in TRUSTED_PLUGIN_SOURCES else "not_required",
                "last_sync_at": None,
                "sync_state": "idle",
                "sync_error": None,
                "expected_sha256": None,
                "public_key": None,
                "signature": None,
                "signature_algorithm": None,
                "signature_required": False,
                "manifest_sha256": None,
            }
            for name, payload in DEFAULT_PLUGIN_SOURCE_CATALOG.items()
        }

    def _configured_source_entries(self) -> dict[str, dict[str, Any]]:
        entries: dict[str, dict[str, Any]] = {}
        for source in self.settings.plugin_sources:
            source_name = str(source.name).strip()
            if not source_name:
                continue
            trusted_source = bool(source.trusted)
            configured_signature = self._signature_value(source.signature)
            expected_sha256 = self._normalize_digest(source.expected_sha256)
            public_key = self._public_key_value(source.public_key)
            signature_algorithm = self._signature_algorithm_value(source.signature_algorithm)
            if signature_algorithm is None and configured_signature is not None:
                signature_algorithm = configured_signature.split(":", 1)[0]
            if signature_algorithm is None and public_key is not None:
                signature_algorithm = "ed25519"
            signature_required = bool(source.signature_required)
            entries[source_name] = {
                "source": source_name,
                "label": str(source.label or source_name.replace("_", " ").replace("-", " ").title()),
                "description": str(source.description or "Configured plugin source"),
                "index_url": str(source.index_url).strip(),
                "trusted_source": trusted_source,
                "expected_sha256": expected_sha256,
                "public_key": public_key,
                "signature": configured_signature,
                "signature_algorithm": signature_algorithm,
                "signature_required": signature_required,
            }
        return entries

    def _load_source_index(self) -> dict[str, dict[str, Any]]:
        entries = self._default_source_entries()
        index_path = self._source_index_path()
        if index_path.exists():
            try:
                payload = json.loads(index_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                payload = []
            if isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, dict):
                        continue
                    source_name = str(item.get("source") or "").strip()
                    if not source_name:
                        continue
                    bucket = entries.setdefault(source_name, {"source": source_name})
                    bucket.update(item)

        for source_name, item in self._configured_source_entries().items():
            bucket = entries.setdefault(source_name, {"source": source_name})
            bucket.update(item)
        return entries

    def _save_source_index(self, sources: list[dict[str, Any]]) -> None:
        index_path = self._source_index_path()
        index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "source": item["source"],
                "label": item.get("label"),
                "description": item.get("description"),
                "index_url": item.get("index_url"),
                "available_plugins": item.get("available_plugins") or [],
                "trusted_source": bool(item.get("trusted_source")),
                "signature_status": item.get("signature_status") or "not_required",
                "last_sync_at": item.get("last_sync_at"),
                "sync_state": item.get("sync_state") or "idle",
                "sync_error": item.get("sync_error"),
                "expected_sha256": item.get("expected_sha256"),
                "public_key": item.get("public_key"),
                "signature": item.get("signature"),
                "signature_algorithm": item.get("signature_algorithm"),
                "signature_required": bool(item.get("signature_required")),
                "manifest_sha256": item.get("manifest_sha256"),
            }
            for item in sources
        ]
        index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _extract_available_plugins(self, payload: dict[str, Any]) -> list[str]:
        available_plugins = [
            str(item).strip()
            for item in (payload.get("available_plugins") or [])
            if str(item).strip()
        ]
        plugin_entries = payload.get("plugins") or []
        if isinstance(plugin_entries, list):
            for item in plugin_entries:
                if isinstance(item, dict):
                    name = str(item.get("name") or "").strip()
                else:
                    name = str(item).strip()
                if name:
                    available_plugins.append(name)
        return sorted(set(available_plugins))

    def _is_fetchable_source(self, index_url: str) -> bool:
        parsed = urlparse(index_url)
        scheme = parsed.scheme.lower()
        if scheme in {"http", "https"}:
            return True
        if scheme == "file":
            marker = f"{parsed.netloc}{parsed.path}".strip("/").lower()
            return bool(marker and marker != "local-config")
        return not scheme and bool(index_url.strip())

    def _resolve_source_file(self, index_url: str) -> Path:
        parsed = urlparse(index_url)
        scheme = parsed.scheme.lower()
        if scheme == "file":
            raw_path = urllib_request.url2pathname(parsed.path or parsed.netloc)
            if parsed.netloc and parsed.path and not raw_path:
                raw_path = urllib_request.url2pathname(f"{parsed.netloc}{parsed.path}")
            if parsed.netloc and parsed.path and len(raw_path) >= 3 and raw_path.startswith("/") and raw_path[2:3] == ":":
                raw_path = raw_path[1:]
            candidate = Path(raw_path)
        else:
            candidate = Path(index_url)
        if not candidate.is_absolute():
            candidate = self.settings.resolve_path(candidate)
        return candidate

    def _load_source_document(self, index_url: str) -> bytes:
        parsed = urlparse(index_url)
        scheme = parsed.scheme.lower()
        if scheme in {"", "file"}:
            if scheme == "file" and f"{parsed.netloc}{parsed.path}".strip("/").lower() == "local-config":
                return b"{}"
            manifest_path = self._resolve_source_file(index_url)
            return manifest_path.read_bytes()
        if scheme in {"http", "https"}:
            request = urllib_request.Request(index_url, headers={"User-Agent": "Hearth/1.x"})
            with urllib_request.urlopen(request, timeout=5) as response:
                return response.read()
        return b"{}"

    def _parse_source_manifest(self, raw_bytes: bytes) -> dict[str, Any]:
        payload = json.loads(raw_bytes.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("plugin source manifest must be a JSON object")
        return payload

    def _canonical_manifest_bytes(self, payload: dict[str, Any]) -> bytes:
        manifest_payload = dict(payload)
        manifest_payload.pop("signature", None)
        return json.dumps(manifest_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

    def _manifest_sha256(self, payload: dict[str, Any]) -> str:
        return hashlib.sha256(self._canonical_manifest_bytes(payload)).hexdigest()

    def _evaluate_source_trust(
        self,
        row: dict[str, Any],
        manifest: dict[str, Any] | None,
        *,
        source_name: str,
    ) -> tuple[bool, str, str | None, str | None]:
        trusted_source = bool(row.get("trusted_source")) or source_name in TRUSTED_PLUGIN_SOURCES
        expected_sha256 = self._normalize_digest(row.get("expected_sha256"))
        configured_public_key = self._public_key_value(row.get("public_key"))
        configured_signature = self._signature_value(row.get("signature"))
        configured_algorithm = self._signature_algorithm_value(row.get("signature_algorithm"))
        signature_required = bool(row.get("signature_required"))

        if manifest is None:
            if trusted_source:
                return True, "trusted", None, None
            return False, "not_required", None, None

        manifest_sha256 = self._manifest_sha256(manifest)
        manifest_public_key = self._public_key_value(manifest.get("public_key"))
        manifest_signature = self._signature_value(manifest.get("signature"))
        manifest_algorithm = self._signature_algorithm_value(manifest.get("signature_algorithm"))
        signature_token = configured_signature or manifest_signature
        signature_algorithm = configured_algorithm or manifest_algorithm
        if signature_algorithm is None and signature_token is not None:
            signature_algorithm = signature_token.split(":", 1)[0]
        if signature_algorithm is None and configured_public_key is not None:
            signature_algorithm = "ed25519"

        if expected_sha256 and manifest_sha256 != expected_sha256:
            return False, "invalid", manifest_sha256, "manifest digest mismatch"

        if configured_public_key and manifest_public_key and configured_public_key != manifest_public_key:
            return False, "invalid", manifest_sha256, "manifest public key mismatch"

        if signature_token:
            if signature_algorithm == "ed25519":
                public_key_token = configured_public_key or (manifest_public_key if trusted_source else None)
                if public_key_token is None:
                    return False, "invalid", manifest_sha256, "configured public key missing"
                public_key_bytes = bytes.fromhex(public_key_token.split(":", 1)[1])
                signature_bytes = bytes.fromhex(signature_token.split(":", 1)[1])
                if not verify_ed25519(public_key_bytes, self._canonical_manifest_bytes(manifest), signature_bytes):
                    return False, "invalid", manifest_sha256, "manifest signature invalid"
                return True, "verified", manifest_sha256, None
            if signature_algorithm == "sha256":
                if self._normalize_digest(signature_token) != manifest_sha256:
                    return False, "invalid", manifest_sha256, "manifest signature invalid"
                return True, "verified", manifest_sha256, None
            return False, "invalid", manifest_sha256, "unsupported signature algorithm"

        if signature_required:
            return False, "missing", manifest_sha256, "manifest signature missing"

        if expected_sha256:
            return True, "verified", manifest_sha256, None

        if trusted_source:
            return True, "trusted", manifest_sha256, None

        return False, "not_required", manifest_sha256, None

    def _refresh_source_entry(self, source_name: str, cached_row: dict[str, Any], live_row: dict[str, Any], refreshed_at: str) -> dict[str, Any]:
        row = dict(cached_row)
        index_url = str(row.get("index_url") or f"hearth://{source_name}")
        available_plugins = [
            str(item).strip()
            for item in (row.get("available_plugins") or [])
            if str(item).strip()
        ]
        manifest: dict[str, Any] | None = None

        if self._is_fetchable_source(index_url):
            try:
                raw_document = self._load_source_document(index_url)
                manifest = self._parse_source_manifest(raw_document)
                if manifest.get("label"):
                    row["label"] = str(manifest.get("label"))
                if manifest.get("description"):
                    row["description"] = str(manifest.get("description"))
                manifest_signature = self._signature_value(manifest.get("signature"))
                manifest_public_key = self._public_key_value(manifest.get("public_key"))
                manifest_algorithm = self._signature_algorithm_value(manifest.get("signature_algorithm"))
                if manifest_signature and not self._signature_value(row.get("signature")):
                    row["signature"] = manifest_signature
                if manifest_public_key and not self._public_key_value(row.get("public_key")):
                    row["public_key"] = manifest_public_key
                effective_algorithm = self._signature_algorithm_value(row.get("signature_algorithm")) or manifest_algorithm
                if effective_algorithm is None:
                    signature_value = self._signature_value(row.get("signature")) or manifest_signature
                    if signature_value is not None:
                        effective_algorithm = signature_value.split(":", 1)[0]
                    elif self._public_key_value(row.get("public_key")) or manifest_public_key:
                        effective_algorithm = "ed25519"
                row["signature_algorithm"] = effective_algorithm
                manifest_plugins = self._extract_available_plugins(manifest)
                if manifest_plugins:
                    available_plugins = manifest_plugins
            except Exception as exc:
                row["trusted_source"] = False
                row["signature_status"] = "invalid"
                row["manifest_sha256"] = None
                row["sync_state"] = "error"
                row["sync_error"] = str(exc)
                row["last_sync_at"] = refreshed_at
                if not available_plugins and live_row["plugins"]:
                    available_plugins = list(live_row["plugins"])
                row["available_plugins"] = sorted(set(available_plugins))
                return row

        trusted_source, signature_status, manifest_sha256, trust_error = self._evaluate_source_trust(
            row,
            manifest,
            source_name=source_name,
        )
        row["trusted_source"] = trusted_source
        row["signature_status"] = signature_status if signature_status in SOURCE_SIGNATURE_STATES else "not_required"
        row["manifest_sha256"] = manifest_sha256
        row["sync_error"] = trust_error
        row["last_sync_at"] = refreshed_at

        if not available_plugins and live_row["plugins"]:
            available_plugins = list(live_row["plugins"])
        row["available_plugins"] = sorted(set(available_plugins))

        has_content = trusted_source or live_row["plugin_count"] or available_plugins
        row["sync_state"] = "error" if trust_error else ("ready" if has_content else "idle")
        return row

    def _merge_source_entries(self, *, mark_refreshed: bool) -> list[dict[str, Any]]:
        grouped: dict[str, dict[str, Any]] = {}
        for plugin in self.list_plugins():
            source_name = plugin["source"]
            bucket = grouped.setdefault(
                source_name,
                {
                    "plugin_count": 0,
                    "enabled_count": 0,
                    "plugins": [],
                },
            )
            bucket["plugin_count"] += 1
            if plugin["enabled"]:
                bucket["enabled_count"] += 1
            bucket["plugins"].append(plugin["name"])

        cached = self._load_source_index()
        source_names = sorted(set(cached.keys()) | set(grouped.keys()))
        refreshed_at = self._now_iso() if mark_refreshed else None
        rows: list[dict[str, Any]] = []
        for source_name in source_names:
            cached_row = dict(cached.get(source_name) or {"source": source_name})
            live_row = grouped.get(source_name) or {"plugin_count": 0, "enabled_count": 0, "plugins": []}
            if mark_refreshed and refreshed_at is not None:
                cached_row = self._refresh_source_entry(source_name, cached_row, live_row, refreshed_at)

            available_plugins = [
                str(item).strip()
                for item in (cached_row.get("available_plugins") or [])
                if str(item).strip()
            ]
            if not available_plugins and live_row["plugins"]:
                available_plugins = list(live_row["plugins"])

            trusted_source = bool(cached_row.get("trusted_source")) or source_name in TRUSTED_PLUGIN_SOURCES
            sync_state = str(cached_row.get("sync_state") or ("ready" if live_row["plugin_count"] else "idle")).strip().lower()
            if sync_state not in SOURCE_SYNC_STATES:
                sync_state = "ready" if live_row["plugin_count"] else "idle"
            signature_status = str(cached_row.get("signature_status") or ("trusted" if trusted_source else "not_required")).strip().lower()
            if signature_status not in SOURCE_SIGNATURE_STATES:
                signature_status = "trusted" if trusted_source else "not_required"

            rows.append(
                {
                    "source": source_name,
                    "label": str(cached_row.get("label") or source_name.title()),
                    "description": str(cached_row.get("description") or "Plugin source index"),
                    "index_url": str(cached_row.get("index_url") or f"hearth://{source_name}"),
                    "trusted_source": trusted_source,
                    "signature_status": signature_status,
                    "sync_state": sync_state,
                    "plugin_count": int(live_row.get("plugin_count") or 0),
                    "enabled_count": int(live_row.get("enabled_count") or 0),
                    "plugins": sorted(live_row.get("plugins") or []),
                    "available_plugins": sorted(set(available_plugins)),
                    "available_count": len(sorted(set(available_plugins))),
                    "last_sync_at": cached_row.get("last_sync_at"),
                    "sync_error": cached_row.get("sync_error"),
                    "expected_sha256": self._normalize_digest(cached_row.get("expected_sha256")),
                    "public_key": self._public_key_value(cached_row.get("public_key")),
                    "signature": self._signature_value(cached_row.get("signature")),
                    "signature_algorithm": self._signature_algorithm_value(cached_row.get("signature_algorithm")),
                    "signature_required": bool(cached_row.get("signature_required")),
                    "manifest_sha256": self._normalize_digest(cached_row.get("manifest_sha256")),
                }
            )
        return sorted(rows, key=lambda item: (not item["trusted_source"], item["source"]))

    def _default_manifest_plugins(self, source_name: str) -> list[dict[str, Any]]:
        return [dict(item, source=source_name) for item in DEFAULT_PLUGIN_MANIFESTS.get(source_name, [])]

    def _load_source_manifest_plugins(self, source_row: dict[str, Any]) -> list[dict[str, Any]]:
        source_name = str(source_row.get("source") or "").strip()
        index_url = str(source_row.get("index_url") or "").strip()
        if not index_url or not self._is_fetchable_source(index_url):
            return self._default_manifest_plugins(source_name)
        try:
            manifest = self._parse_source_manifest(self._load_source_document(index_url))
        except Exception:
            return self._default_manifest_plugins(source_name)
        plugins = manifest.get("plugins") if isinstance(manifest.get("plugins"), list) else []
        rows: list[dict[str, Any]] = []
        for item in plugins:
            if isinstance(item, dict):
                row = dict(item)
            else:
                row = {"name": str(item).strip()}
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            row.setdefault("source", source_name)
            rows.append(row)
        return rows or self._default_manifest_plugins(source_name)

    def _available_catalog(self, *, refresh_sources: bool = False) -> list[dict[str, Any]]:
        sources = self.refresh_sources()["sources"] if refresh_sources else self.list_sources()
        rows: dict[str, dict[str, Any]] = {}
        for source in sources:
            for item in self._load_source_manifest_plugins(source):
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                row = self._normalize_plugin(
                    {
                        **item,
                        "source": source["source"],
                        "trusted_source": bool(source.get("trusted_source")),
                        "signature_status": source.get("signature_status"),
                        "enabled": False,
                    }
                )
                row["source_label"] = source.get("label")
                row["source_sync_state"] = source.get("sync_state")
                row["signature_status"] = source.get("signature_status")
                row["manifest_sha256"] = source.get("manifest_sha256")
                row["installable"] = bool(source.get("trusted_source") or source.get("signature_status") in {"trusted", "verified"})
                rows[name] = row
        return sorted(rows.values(), key=lambda item: item["name"])

    def _catalog_by_name(self) -> dict[str, dict[str, Any]]:
        return {item["name"]: item for item in self._available_catalog()}

    def _sandbox_boundary(self, payload: dict[str, Any]) -> dict[str, Any]:
        name = str(payload.get("name") or "unknown-plugin")
        permissions = sorted({str(item).strip().lower() for item in payload.get("permissions") or [] if str(item).strip()})
        elevated = any(permission in {"operate", "configure", "maintenance", "security", "tokens"} for permission in permissions)
        root = self.settings.plugin_runtime_dir / name
        return {
            "mode": "elevated" if elevated else "restricted",
            "network_access": bool(payload.get("type") in {"bridge", "service"} or elevated),
            "filesystem_roots": [str(root)],
            "permissions": permissions,
            "writable_state_dir": str(root),
        }

    def _plugin_config_payload(self) -> dict[str, Any]:
        return self.settings.model_dump(mode="json", exclude={"config_path"}, exclude_none=True)

    def _normalize_plugin(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        source = str(normalized.get("source") or "local").strip() or "local"
        enabled = bool(normalized.get("enabled", False))
        permissions = [str(item).strip() for item in (normalized.get("permissions") or []) if str(item).strip()]
        depends_on = [str(item).strip() for item in (normalized.get("depends_on") or []) if str(item).strip()]
        config = normalized.get("config") or {}
        if not isinstance(config, dict):
            config = {"value": config}

        trusted_source = source in TRUSTED_PLUGIN_SOURCES
        sync_state = str(normalized.get("sync_state") or ("ready" if enabled else "idle")).strip().lower()
        if sync_state not in SOURCE_SYNC_STATES - {"error"}:
            sync_state = "ready" if enabled else "idle"

        normalized.setdefault("name", "unknown-plugin")
        normalized["enabled"] = enabled
        normalized.setdefault("version", "0.1.0")
        normalized.setdefault("type", "extension")
        normalized["source"] = source
        normalized.setdefault("compatibility", "hearth-1.x")
        normalized.setdefault("description", "")
        normalized["permissions"] = permissions
        normalized["depends_on"] = depends_on
        normalized["config"] = config
        normalized["trusted_source"] = trusted_source
        normalized["sync_state"] = sync_state
        normalized["diagnostics"] = {
            "load_state": "enabled" if enabled else "disabled",
            "trusted_source": trusted_source,
            "permission_count": len(permissions),
            "dependency_count": len(depends_on),
            "config_keys": sorted(config.keys()),
        }
        normalized.setdefault("sandbox_boundary", self._sandbox_boundary(normalized))
        return normalized

    def list_plugins(self) -> list[dict[str, Any]]:
        state = self._load_plugin_state()
        installed_rows = state.get("plugins") if isinstance(state.get("plugins"), dict) else {}
        plugins: list[dict[str, Any]] = []
        for plugin in self.settings.plugins:
            normalized = self._normalize_plugin(plugin.model_dump(mode="json"))
            runtime_row = installed_rows.get(normalized["name"]) if isinstance(installed_rows, dict) else None
            if isinstance(runtime_row, dict):
                normalized["install_state"] = {
                    "installed_at": runtime_row.get("installed_at"),
                    "updated_at": runtime_row.get("updated_at"),
                    "status": runtime_row.get("status") or "installed",
                    "operation": runtime_row.get("operation"),
                }
                normalized["sandbox_boundary"] = runtime_row.get("sandbox_boundary") or normalized.get("sandbox_boundary")
            else:
                normalized["install_state"] = None
            plugins.append(normalized)
        return plugins

    def list_sources(self) -> list[dict[str, Any]]:
        return self._merge_source_entries(mark_refreshed=False)

    def refresh_sources(self) -> dict[str, Any]:
        sources = self._merge_source_entries(mark_refreshed=True)
        self._save_source_index(sources)
        return {
            "refreshed": True,
            "refreshed_at": self._now_iso(),
            "index_path": str(self._source_index_path()),
            "source_count": len(sources),
            "sources": sources,
        }

    def get_source(self, name: str) -> dict[str, Any] | None:
        return next((item for item in self.list_sources() if item["source"] == name), None)

    def get_plugin(self, name: str) -> dict[str, Any] | None:
        return next((item for item in self.list_plugins() if item["name"] == name), None)

    def set_plugin_enabled(self, name: str, enabled: bool) -> dict[str, Any]:
        payload = self._plugin_config_payload()
        plugins = list(payload.get("plugins") or [])
        for index, item in enumerate(plugins):
            if item.get("name") == name:
                updated = dict(item)
                updated["enabled"] = enabled
                updated.setdefault("sandbox_boundary", self._sandbox_boundary(updated))
                plugins[index] = updated
                payload["plugins"] = plugins
                self.config_service.save(payload)
                state = self._load_plugin_state()
                plugin_state = dict((state.get("plugins") or {}).get(name) or {})
                plugin_state.update(
                    {
                        "status": "enabled" if enabled else "disabled",
                        "operation": "toggle_enabled",
                        "updated_at": self._now_iso(),
                        "sandbox_boundary": updated.get("sandbox_boundary") or self._sandbox_boundary(updated),
                    }
                )
                state.setdefault("plugins", {})[name] = plugin_state
                state = self._record_plugin_operation(
                    "toggle_enabled",
                    plugin_name=name,
                    payload={"enabled": enabled},
                    state=state,
                )
                self._save_plugin_state(state)
                return self._normalize_plugin(updated)
        raise LookupError("plugin not found")

    def list_available_plugins(self, *, refresh_sources: bool = False) -> list[dict[str, Any]]:
        installed = {item["name"] for item in self.list_plugins()}
        rows = []
        for item in self._available_catalog(refresh_sources=refresh_sources):
            row = dict(item)
            row["installed"] = row["name"] in installed
            row["sandbox_boundary"] = row.get("sandbox_boundary") or self._sandbox_boundary(row)
            rows.append(row)
        return rows

    def get_available_plugin(self, name: str) -> dict[str, Any] | None:
        return next((item for item in self.list_available_plugins() if item["name"] == name), None)

    def resolve_dependencies(self, name: str) -> list[dict[str, Any]]:
        catalog = {item["name"]: item for item in self.list_available_plugins()}
        if name not in catalog:
            raise LookupError("plugin catalog entry not found")
        ordered: list[dict[str, Any]] = []
        seen: set[str] = set()

        def visit(plugin_name: str) -> None:
            if plugin_name in seen:
                return
            plugin = catalog.get(plugin_name)
            if plugin is None:
                raise LookupError(f"dependency catalog entry not found: {plugin_name}")
            for dependency in plugin.get("depends_on") or []:
                visit(str(dependency))
            seen.add(plugin_name)
            ordered.append(plugin)

        visit(name)
        return ordered

    def install_plugin(self, name: str, *, enable: bool = True) -> dict[str, Any]:
        dependency_chain = self.resolve_dependencies(name)
        payload = self._plugin_config_payload()
        plugins = list(payload.get("plugins") or [])
        installed_names = {str(item.get("name") or "") for item in plugins}
        state = self._load_plugin_state()
        state_plugins = state.setdefault("plugins", {})
        installed: list[dict[str, Any]] = []
        for entry in dependency_chain:
            plugin_name = str(entry["name"])
            plugin_payload = {
                "name": plugin_name,
                "enabled": enable,
                "version": entry.get("version") or "0.1.0",
                "type": entry.get("type") or "extension",
                "source": entry.get("source") or "community",
                "compatibility": entry.get("compatibility") or "hearth-1.x",
                "description": entry.get("description") or "",
                "permissions": entry.get("permissions") or [],
                "depends_on": entry.get("depends_on") or [],
                "config": entry.get("config") or {},
                "sandbox_boundary": entry.get("sandbox_boundary") or self._sandbox_boundary(entry),
            }
            if plugin_name not in installed_names:
                plugins.append(plugin_payload)
                installed_names.add(plugin_name)
            state_plugins[plugin_name] = {
                "installed_at": state_plugins.get(plugin_name, {}).get("installed_at") or self._now_iso(),
                "updated_at": self._now_iso(),
                "status": "installed",
                "operation": "install",
                "sandbox_boundary": plugin_payload["sandbox_boundary"],
                "source": plugin_payload["source"],
                "version": plugin_payload["version"],
            }
            installed.append(plugin_payload)

        payload["plugins"] = plugins
        result = self.config_service.save(payload)
        if not result.get("saved"):
            raise ValueError("failed to save installed plugin configuration")
        state = self._record_plugin_operation(
            "install",
            plugin_name=name,
            payload={"installed": [item["name"] for item in installed], "enable": enable},
            state=state,
        )
        self._save_plugin_state(state)
        return {
            "installed": True,
            "primary_plugin": name,
            "plugins": [self._normalize_plugin(item) for item in installed],
            "dependency_count": max(len(installed) - 1, 0),
        }

    def uninstall_plugin(self, name: str, *, remove_dependents: bool = False) -> dict[str, Any]:
        payload = self._plugin_config_payload()
        plugins = list(payload.get("plugins") or [])
        installed_names = {str(item.get("name") or "") for item in plugins}
        if name not in installed_names:
            raise LookupError("plugin not installed")
        dependents = [
            str(item.get("name") or "")
            for item in plugins
            if name in [str(dep) for dep in item.get("depends_on") or []]
        ]
        if dependents and not remove_dependents:
            raise ValueError("plugin is still required by other installed plugins")
        removed_names = {name, *dependents} if remove_dependents else {name}
        payload["plugins"] = [item for item in plugins if str(item.get("name") or "") not in removed_names]
        result = self.config_service.save(payload)
        if not result.get("saved"):
            raise ValueError("failed to save plugin removal")
        state = self._load_plugin_state()
        state_plugins = state.setdefault("plugins", {})
        for plugin_name in removed_names:
            state_plugins.pop(plugin_name, None)
        state = self._record_plugin_operation(
            "uninstall",
            plugin_name=name,
            payload={"removed": sorted(removed_names), "remove_dependents": remove_dependents},
            state=state,
        )
        self._save_plugin_state(state)
        return {"uninstalled": True, "removed": sorted(removed_names)}

    def update_plugin(self, name: str, *, enable: bool | None = None) -> dict[str, Any]:
        installed = self.get_plugin(name)
        if installed is None:
            raise LookupError("plugin not installed")
        available = self.get_available_plugin(name) or installed
        payload = self._plugin_config_payload()
        plugins = list(payload.get("plugins") or [])
        updated_row: dict[str, Any] | None = None
        for index, item in enumerate(plugins):
            if item.get("name") != name:
                continue
            updated = {
                **item,
                "version": available.get("version") or item.get("version") or "0.1.0",
                "description": available.get("description") or item.get("description") or "",
                "permissions": available.get("permissions") or item.get("permissions") or [],
                "depends_on": available.get("depends_on") or item.get("depends_on") or [],
                "config": available.get("config") or item.get("config") or {},
                "sandbox_boundary": available.get("sandbox_boundary") or self._sandbox_boundary(available),
            }
            if enable is not None:
                updated["enabled"] = enable
            plugins[index] = updated
            updated_row = updated
            break
        if updated_row is None:
            raise LookupError("plugin not installed")
        payload["plugins"] = plugins
        result = self.config_service.save(payload)
        if not result.get("saved"):
            raise ValueError("failed to save plugin update")
        state = self._load_plugin_state()
        state.setdefault("plugins", {})[name] = {
            **dict((state.get("plugins") or {}).get(name) or {}),
            "updated_at": self._now_iso(),
            "status": "installed",
            "operation": "update",
            "version": updated_row.get("version"),
            "sandbox_boundary": updated_row.get("sandbox_boundary"),
        }
        state = self._record_plugin_operation(
            "update",
            plugin_name=name,
            payload={"version": updated_row.get("version")},
            state=state,
        )
        self._save_plugin_state(state)
        return self._normalize_plugin(updated_row)

    def plugin_history(self, limit: int = 50) -> list[dict[str, Any]]:
        state = self._load_plugin_state()
        return list(state.get("history") or [])[:limit]
