from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import tarfile
import tempfile

from hearth.core.config import HearthSettings, load_settings
from hearth.storage.db import Database


class BackupService:
    def __init__(self, settings: HearthSettings, database: Database) -> None:
        self.settings = settings
        self.database = database

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    def _default_archive_path(self) -> Path:
        return self.settings.backups_dir / f"hearth-backup-{self._timestamp()}.tar.gz"

    def _ensure_parent(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def _safe_extract(self, archive: tarfile.TarFile, target_dir: Path) -> None:
        target_dir = target_dir.resolve()
        for member in archive.getmembers():
            destination = (target_dir / member.name).resolve()
            if not str(destination).startswith(str(target_dir)):
                raise ValueError(f"unsafe archive entry: {member.name}")
        try:
            archive.extractall(target_dir, filter="data")
        except TypeError:
            archive.extractall(target_dir)

    def _apply_loaded_settings(self, loaded: HearthSettings) -> None:
        self.settings.system = loaded.system
        self.settings.reticulum = loaded.reticulum
        self.settings.web = loaded.web
        self.settings.security = loaded.security
        self.settings.monitor = loaded.monitor
        self.settings.alerts = loaded.alerts
        self.settings.interfaces = loaded.interfaces
        self.settings.plugins = loaded.plugins
        self.settings.plugin_sources = loaded.plugin_sources
        self.settings.roles = loaded.roles
        self.settings.config_path = loaded.config_path

    def _load_snapshots(self) -> list[dict]:
        path = self.settings.backup_snapshots_path
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return payload if isinstance(payload, list) else []

    def _save_snapshots(self, snapshots: list[dict]) -> None:
        path = self.settings.backup_snapshots_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(snapshots, ensure_ascii=False, indent=2), encoding="utf-8")

    def _record_snapshot(self, archive_path: str | Path, *, kind: str, manifest: dict | None = None) -> dict:
        snapshots = self._load_snapshots()
        payload = {
            "kind": kind,
            "archive_path": str(Path(archive_path).resolve()),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "node_name": self.settings.system.node_name,
            "manifest": manifest or {},
        }
        snapshots.insert(0, payload)
        self._save_snapshots(snapshots[:200])
        return payload

    def _export_manifest(self) -> dict:
        return {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "node_name": self.settings.system.node_name,
            "config_path": str(self.settings.config_path) if self.settings.config_path else None,
            "database_path": str(self.settings.database_path),
            "identity_path": str(self.settings.identity_path),
        }

    def export_plan(self) -> dict:
        return {
            "config": str(self.settings.config_path) if self.settings.config_path else None,
            "database": str(self.settings.database_path),
            "identity": str(self.settings.identity_path),
            "backups_dir": str(self.settings.backups_dir),
        }

    def list_archives(self) -> list[str]:
        self.settings.backups_dir.mkdir(parents=True, exist_ok=True)
        return [str(path) for path in sorted(self.settings.backups_dir.glob("*.tar.gz"), reverse=True)]

    def inspect_archive(self, archive_path: str | Path) -> dict:
        source_path = Path(archive_path)
        if not source_path.exists():
            raise FileNotFoundError(f"backup archive not found: {source_path}")

        manifest: dict = {}
        included: list[str] = []
        with tarfile.open(source_path, "r:gz") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    included.append(member.name)
            try:
                manifest_member = archive.extractfile("manifest.json")
            except KeyError:
                manifest_member = None
            if manifest_member is not None:
                manifest = json.loads(manifest_member.read().decode("utf-8"))

        stat = source_path.stat()
        return {
            "archive_path": str(source_path.resolve()),
            "archive_name": source_path.name,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            "member_count": len(included),
            "included": included,
            "manifest": manifest,
            "node_name": manifest.get("node_name"),
            "created_at": manifest.get("created_at"),
        }

    def export(self, destination_path: str | Path | None = None) -> dict:
        archive_path = Path(destination_path) if destination_path else self._default_archive_path()
        self._ensure_parent(archive_path)

        manifest = self._export_manifest()
        included: list[str] = []
        with tarfile.open(archive_path, "w:gz") as archive:
            if self.settings.config_path and Path(self.settings.config_path).exists():
                archive.add(self.settings.config_path, arcname="config/hearth.toml")
                included.append("config/hearth.toml")
            if self.settings.database_path.exists():
                archive.add(self.settings.database_path, arcname="data/hearth.db")
                included.append("data/hearth.db")
            if self.settings.identity_path.exists():
                archive.add(self.settings.identity_path, arcname="identity/identity")
                included.append("identity/identity")

            with tempfile.TemporaryDirectory() as temp_dir:
                manifest_path = Path(temp_dir) / "manifest.json"
                manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                archive.add(manifest_path, arcname="manifest.json")
                included.append("manifest.json")

        snapshot = self._record_snapshot(archive_path, kind="export", manifest=manifest)
        return {
            "exported": True,
            "archive_path": str(archive_path.resolve()),
            "included": included,
            "manifest": manifest,
            "snapshot": snapshot,
        }

    def import_archive(self, archive_path: str | Path) -> dict:
        source_path = Path(archive_path)
        if not source_path.exists():
            raise FileNotFoundError(f"backup archive not found: {source_path}")

        pre_restore_backup = self.export()
        self.database.dispose()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            with tarfile.open(source_path, "r:gz") as archive:
                self._safe_extract(archive, temp_root)

            config_candidate = temp_root / "config" / "hearth.toml"
            database_candidate = temp_root / "data" / "hearth.db"
            identity_candidate = temp_root / "identity" / "identity"
            manifest_candidate = temp_root / "manifest.json"

            manifest = json.loads(manifest_candidate.read_text(encoding="utf-8")) if manifest_candidate.exists() else {}

            restored: list[str] = []
            if config_candidate.exists() and self.settings.config_path:
                target = Path(self.settings.config_path)
                self._ensure_parent(target)
                shutil.copy2(config_candidate, target)
                restored.append(str(target))
                self._apply_loaded_settings(load_settings(target))
            if database_candidate.exists():
                self._ensure_parent(self.settings.database_path)
                shutil.copy2(database_candidate, self.settings.database_path)
                restored.append(str(self.settings.database_path))
            if identity_candidate.exists():
                self._ensure_parent(self.settings.identity_path)
                shutil.copy2(identity_candidate, self.settings.identity_path)
                restored.append(str(self.settings.identity_path))

        self.database.init_schema()
        snapshot = self._record_snapshot(source_path, kind="import", manifest=manifest)
        return {
            "imported": True,
            "archive_path": str(source_path.resolve()),
            "restored": restored,
            "manifest": manifest,
            "pre_restore_backup": pre_restore_backup["archive_path"],
            "restart_required": True,
            "snapshot": snapshot,
        }

    def create_snapshot(self, destination_path: str | Path | None = None) -> dict:
        result = self.export(destination_path)
        return {
            "snapshot_created": bool(result.get("exported")),
            **result,
        }

    def list_snapshots(self) -> list[dict]:
        snapshots = self._load_snapshots()
        for item in snapshots:
            archive_path = Path(str(item.get("archive_path") or ""))
            item["exists"] = archive_path.exists()
        return snapshots

    def prune_snapshots(self, *, keep: int = 10, max_age_days: int | None = None) -> dict:
        snapshots = self._load_snapshots()
        now = datetime.now(timezone.utc)
        kept: list[dict] = []
        removed: list[str] = []
        for index, item in enumerate(snapshots):
            archive_path = Path(str(item.get("archive_path") or ""))
            created_at = item.get("created_at")
            age_expired = False
            if max_age_days is not None and created_at:
                try:
                    parsed = datetime.fromisoformat(str(created_at))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=timezone.utc)
                    age_expired = (now - parsed.astimezone(timezone.utc)).days > max_age_days
                except ValueError:
                    age_expired = False
            if index >= keep or age_expired:
                if archive_path.exists():
                    archive_path.unlink()
                removed.append(str(archive_path))
                continue
            kept.append(item)
        self._save_snapshots(kept)
        return {"pruned": len(removed), "removed": removed, "kept": len(kept)}

    def disaster_recovery_helper(self, archive_path: str | Path | None = None) -> dict:
        target = Path(archive_path) if archive_path else None
        if target is None:
            archives = self.list_archives()
            target = Path(archives[0]) if archives else None
        detail = self.inspect_archive(target) if target is not None else None
        return {
            "selected_archive": str(target.resolve()) if target and target.exists() else None,
            "archive_detail": detail,
            "steps": [
                "Place the selected backup archive on the target node.",
                "Stop the Hearth service before import to avoid runtime writes.",
                "Run backup import from the API or CLI and verify config, database, and identity paths.",
                "Review the pre-restore backup created automatically before switching traffic back.",
                "Restart Hearth and confirm runtime, interfaces, peers, and routes are healthy.",
            ],
        }
