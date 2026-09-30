from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import tarfile
import tempfile
import sqlite3
from hashlib import sha256
from contextlib import closing

from hearth.core.config import HearthSettings, load_settings, dump_settings
from hearth.core.operations import OperationLock, atomic_write
from hearth.interfaces.registry import InterfaceRegistry
from hearth.reticulum.runtime import ManagedReticulumAdapter
from hearth.storage.db import Database


class BackupService:
    def __init__(self, settings: HearthSettings, database: Database) -> None:
        self.settings = settings
        self.database = database
        self.operations = OperationLock(settings.data_dir / "operations.lock")

    def _timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")

    def _default_archive_path(self) -> Path:
        return self.settings.backups_dir / f"hearth-backup-{self._timestamp()}.tar.gz"

    def _ensure_parent(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def _safe_extract(self, archive: tarfile.TarFile, target_dir: Path) -> None:
        target_dir = target_dir.resolve()
        for member in archive.getmembers():
            destination = (target_dir / member.name).resolve()
            if (
                not destination.is_relative_to(target_dir)
                or member.issym()
                or member.islnk()
                or not (member.isfile() or member.isdir())
            ):
                raise ValueError(f"unsafe archive entry: {member.name}")
        archive.extractall(target_dir, filter="data")

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
        path.write_text(
            json.dumps(snapshots, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def _record_snapshot(
        self, archive_path: str | Path, *, kind: str, manifest: dict | None = None
    ) -> dict:
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
            "config_path": str(self.settings.config_path)
            if self.settings.config_path
            else None,
            "database_path": str(self.settings.database_path),
            "identity_path": str(self.settings.identity_path),
        }

    def export_plan(self) -> dict:
        return {
            "config": str(self.settings.config_path)
            if self.settings.config_path
            else None,
            "database": str(self.settings.database_path),
            "identity": str(self.settings.identity_path),
            "backups_dir": str(self.settings.backups_dir),
        }

    def list_archives(self) -> list[str]:
        self.settings.backups_dir.mkdir(parents=True, exist_ok=True)
        return [
            str(path)
            for path in sorted(self.settings.backups_dir.glob("*.tar.gz"), reverse=True)
        ]

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
            "modified_at": datetime.fromtimestamp(
                stat.st_mtime, tz=timezone.utc
            ).isoformat(),
            "member_count": len(included),
            "included": included,
            "manifest": manifest,
            "node_name": manifest.get("node_name"),
            "created_at": manifest.get("created_at"),
        }

    def export(self, destination_path: str | Path | None = None) -> dict:
        with self.operations.hold():
            return self._export(destination_path)

    def _export(self, destination_path: str | Path | None = None) -> dict:
        archive_path = (
            Path(destination_path) if destination_path else self._default_archive_path()
        )
        self._ensure_parent(archive_path)

        manifest = self._export_manifest()
        included: list[str] = []
        temporary_archive = archive_path.with_suffix(archive_path.suffix + ".partial")
        with (
            tempfile.TemporaryDirectory() as snapshot_dir,
            tarfile.open(temporary_archive, "w:gz") as archive,
        ):
            checksums = {}
            if self.settings.config_path and Path(self.settings.config_path).exists():
                archive.add(self.settings.config_path, arcname="config/hearth.toml")
                included.append("config/hearth.toml")
                checksums["config/hearth.toml"] = sha256(
                    Path(self.settings.config_path).read_bytes()
                ).hexdigest()
                active = Path(snapshot_dir) / "active.toml"
                active_file = Path(self.settings.config_path).with_suffix(
                    ".active.toml"
                )
                active.write_text(
                    active_file.read_text(encoding="utf-8")
                    if active_file.exists()
                    else dump_settings(self.settings),
                    encoding="utf-8",
                )
                archive.add(active, arcname="config/active.toml")
                included.append("config/active.toml")
                checksums["config/active.toml"] = sha256(
                    active.read_bytes()
                ).hexdigest()
                control_file = Path(snapshot_dir) / "control.json"
                control = ManagedReticulumAdapter(self.settings).control_state()
                control.pop("process", None)
                control_file.write_text(json.dumps(control), encoding="utf-8")
                archive.add(control_file, arcname="runtime/control.json")
                included.append("runtime/control.json")
                checksums["runtime/control.json"] = sha256(
                    control_file.read_bytes()
                ).hexdigest()
            if self.settings.database_path.exists():
                snapshot_path = Path(snapshot_dir) / "hearth.db"
                self.database.snapshot(snapshot_path)
                archive.add(snapshot_path, arcname="data/hearth.db")
                included.append("data/hearth.db")
                checksums["data/hearth.db"] = sha256(
                    snapshot_path.read_bytes()
                ).hexdigest()
            if self.settings.identity_path.exists():
                archive.add(self.settings.identity_path, arcname="identity/identity")
                included.append("identity/identity")
                checksums["identity/identity"] = sha256(
                    self.settings.identity_path.read_bytes()
                ).hexdigest()
            transport_identity = (
                self.settings.reticulum_config_path / "storage" / "transport_identity"
            )
            if transport_identity.is_file():
                archive.add(transport_identity, arcname="reticulum/transport_identity")
                included.append("reticulum/transport_identity")
                checksums["reticulum/transport_identity"] = sha256(
                    transport_identity.read_bytes()
                ).hexdigest()

            manifest["format_version"] = 2
            manifest["sha256"] = checksums

            with tempfile.TemporaryDirectory() as temp_dir:
                manifest_path = Path(temp_dir) / "manifest.json"
                manifest_path.write_text(
                    json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                archive.add(manifest_path, arcname="manifest.json")
                included.append("manifest.json")
        temporary_archive.replace(archive_path)

        snapshot = self._record_snapshot(archive_path, kind="export", manifest=manifest)
        return {
            "exported": True,
            "archive_path": str(archive_path.resolve()),
            "included": included,
            "manifest": manifest,
            "snapshot": snapshot,
        }

    def import_archive(self, archive_path: str | Path) -> dict:
        with self.operations.hold(), self.database.access.hold():
            if ManagedReticulumAdapter(self.settings).status().running:
                raise ValueError(
                    "Stop the runtime before restore; use the managed restore operation"
                )
            return self._import_archive(archive_path)

    def _import_archive(self, archive_path: str | Path) -> dict:
        source_path = Path(archive_path)
        if not source_path.exists():
            raise FileNotFoundError(f"backup archive not found: {source_path}")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            with tarfile.open(source_path, "r:gz") as archive:
                self._safe_extract(archive, temp_root)

            config_candidate = temp_root / "config" / "hearth.toml"
            database_candidate = temp_root / "data" / "hearth.db"
            identity_candidate = temp_root / "identity" / "identity"
            manifest_candidate = temp_root / "manifest.json"

            manifest = (
                json.loads(manifest_candidate.read_text(encoding="utf-8"))
                if manifest_candidate.exists()
                else {}
            )
            required = [config_candidate, database_candidate, identity_candidate]
            if not all(path.is_file() for path in required):
                raise ValueError(
                    "Backup must contain configuration, database and identity"
                )
            for relative, digest in manifest.get("sha256", {}).items():
                path = (temp_root / relative).resolve()
                if (
                    not path.is_relative_to(temp_root.resolve())
                    or not path.is_file()
                    or sha256(path.read_bytes()).hexdigest() != digest
                ):
                    raise ValueError(f"Backup checksum mismatch: {relative}")
            loaded = load_settings(config_candidate)
            active_candidate = temp_root / "config" / "active.toml"
            active = (
                load_settings(active_candidate)
                if active_candidate.is_file()
                else loaded.model_copy(deep=True)
            )
            control_candidate = temp_root / "runtime" / "control.json"
            archived_control = (
                json.loads(control_candidate.read_text(encoding="utf-8"))
                if control_candidate.is_file()
                else {}
            )
            if (
                not isinstance(archived_control, dict)
                or not isinstance(archived_control.get("interfaces", {}), dict)
                or any(
                    value not in {"running", "stopped"}
                    for value in archived_control.get("interfaces", {}).values()
                )
            ):
                raise ValueError("Backup contains invalid interface desired states")
            # Deployment locations belong to the target machine, not the backup.
            loaded.system.data_dir = self.settings.system.data_dir
            loaded.reticulum.config_path = self.settings.reticulum.config_path
            loaded.reticulum.identity_path = self.settings.reticulum.identity_path
            loaded.web.host, loaded.web.port = (
                self.settings.web.host,
                self.settings.web.port,
            )
            active.system.data_dir = self.settings.system.data_dir
            active.reticulum.config_path = self.settings.reticulum.config_path
            active.reticulum.identity_path = self.settings.reticulum.identity_path
            active.web.host, active.web.port = (
                self.settings.web.host,
                self.settings.web.port,
            )
            registry = InterfaceRegistry()
            registry.register_builtins()
            errors = registry.validate_interfaces(
                loaded.interfaces
            ) + registry.validate_interfaces(active.interfaces)
            if errors:
                raise ValueError(f"Invalid backup configuration: {errors}")
            with closing(sqlite3.connect(database_candidate)) as candidate_db:
                if candidate_db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise ValueError("Backup database failed integrity check")
                if not candidate_db.execute(
                    "SELECT name FROM sqlite_master WHERE name = 'node_state'"
                ).fetchone():
                    raise ValueError("Backup database is not a Hearth database")

            pre_restore_backup = self.export()
            rollback_db = temp_root / "rollback.db"
            self.database.snapshot(rollback_db)
            target = Path(self.settings.config_path)
            active_target = target.with_suffix(".active.toml")
            transport_candidate = temp_root / "reticulum" / "transport_identity"
            transport_target = (
                self.settings.reticulum_config_path / "storage" / "transport_identity"
            )
            control_target = self.settings.runtime_dir / "control.json"
            current_control = ManagedReticulumAdapter(self.settings).control_state()
            restored_control = {
                **current_control,
                "interfaces": archived_control.get("interfaces", {}),
            }
            original_files = {
                path: path.read_bytes() if path.exists() else None
                for path in (
                    target,
                    active_target,
                    self.settings.identity_path,
                    transport_target,
                    control_target,
                )
            }
            try:
                atomic_write(target, dump_settings(loaded))
                atomic_write(active_target, dump_settings(active))
                atomic_write(control_target, json.dumps(restored_control))
                self.database.restore_snapshot(database_candidate)
                atomic_write(
                    self.settings.identity_path, identity_candidate.read_bytes()
                )
                if transport_candidate.is_file():
                    atomic_write(transport_target, transport_candidate.read_bytes())
                self.database.init_schema()
            except BaseException:
                self.database.restore_snapshot(rollback_db)
                for path, content in original_files.items():
                    if content is None:
                        path.unlink(missing_ok=True)
                    else:
                        atomic_write(path, content)
                raise
            restored = [
                str(target),
                str(active_target),
                str(self.settings.database_path),
                str(self.settings.identity_path),
            ]

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

    def prune_snapshots(
        self, *, keep: int = 10, max_age_days: int | None = None
    ) -> dict:
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
                    age_expired = (
                        now - parsed.astimezone(timezone.utc)
                    ).days > max_age_days
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
            "selected_archive": str(target.resolve())
            if target and target.exists()
            else None,
            "archive_detail": detail,
            "steps": [
                "Place the selected backup archive on the target node.",
                "Stop the Hearth service before import to avoid runtime writes.",
                "Run backup import from the API or CLI and verify config, database, and identity paths.",
                "Review the pre-restore backup created automatically before switching traffic back.",
                "Restart Hearth and confirm runtime, interfaces, peers, and routes are healthy.",
            ],
        }
