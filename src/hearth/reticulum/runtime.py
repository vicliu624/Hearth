from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shlex
import signal
import shutil
import subprocess
import sys
import psutil
from typing import Any

from hearth.core.config import HearthSettings, load_settings, dump_settings
from hearth.core.operations import OperationLock, OperationBusy, atomic_write
from hearth.reticulum.adapter import (
    AnnounceEvent,
    InterfaceRuntimeInfo,
    NodeRuntimeStatus,
    PathEntry,
    ReticulumAdapter,
)
from hearth.reticulum.config_bridge import RuntimeConfigBridge


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2))


@dataclass(slots=True)
class RuntimeFileState:
    backend: str = "mock_process"
    status: str = "stopped"
    pid: int | None = None
    started_at: str | None = None
    heartbeat_at: str | None = None
    restart_count: int = 0
    last_exit_code: int | None = None
    command: list[str] = field(default_factory=list)
    config_path: str | None = None
    identity_path: str | None = None
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "status": self.status,
            "pid": self.pid,
            "started_at": self.started_at,
            "heartbeat_at": self.heartbeat_at,
            "restart_count": self.restart_count,
            "last_exit_code": self.last_exit_code,
            "command": list(self.command),
            "config_path": self.config_path,
            "identity_path": self.identity_path,
            "last_error": self.last_error,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "RuntimeFileState":
        return cls(
            backend=payload.get("backend", "mock_process"),
            status=payload.get("status", "stopped"),
            pid=payload.get("pid"),
            started_at=payload.get("started_at"),
            heartbeat_at=payload.get("heartbeat_at"),
            restart_count=payload.get("restart_count", 0),
            last_exit_code=payload.get("last_exit_code"),
            command=list(payload.get("command", [])),
            config_path=payload.get("config_path"),
            identity_path=payload.get("identity_path"),
            last_error=payload.get("last_error"),
        )


class ManagedReticulumAdapter(ReticulumAdapter):
    def __init__(self, settings: HearthSettings) -> None:
        self.settings = settings
        self.operations = OperationLock(settings.data_dir / "operations.lock")
        self._config_bridge = RuntimeConfigBridge(settings)
        self._configured_interfaces: list[InterfaceRuntimeInfo] = []
        self._observed_interfaces: list[InterfaceRuntimeInfo] = []
        self._paths: list[PathEntry] = []
        self._announces: list[AnnounceEvent] = []
        self._observed_runtime: dict[str, Any] = {}
        self.on_change = None
        self.allow_pending_configuration = False

    def _assert_current_configuration(self) -> None:
        if self.allow_pending_configuration or not self.settings.config_path:
            return
        active = self.settings.config_path.with_suffix(".active.toml")
        if active.exists() and dump_settings(load_settings(active)) != dump_settings(
            self.settings
        ):
            raise OperationBusy(
                "Active configuration changed in another process; reload and retry the operation"
            )

    def control_state(self) -> dict:
        path = self.settings.runtime_dir / "control.json"
        if not path.exists():
            return {
                "desired_state": "running"
                if self.settings.reticulum.auto_start
                else "stopped",
                "interfaces": {},
            }
        return json.loads(path.read_text(encoding="utf-8"))

    def _save_control(self, state: dict) -> None:
        write_json_atomic(self.settings.runtime_dir / "control.json", state)

    def desired_state(self) -> str:
        return self.control_state()["desired_state"]

    def _set_desired(self, state: str) -> None:
        control = self.control_state()
        control["desired_state"] = state
        self._save_control(control)

    def _changed(self) -> None:
        if self.on_change is not None:
            self.on_change()

    def _transport_identity_ready(self) -> bool:
        path = self.settings.reticulum_config_path / "storage" / "transport_identity"
        try:
            return path.stat().st_size == 64
        except OSError:
            return False

    def _prepare_transport_identity(self) -> None:
        from RNS import Identity

        path = self.settings.reticulum_config_path / "storage" / "transport_identity"
        if path.exists():
            if Identity.from_file(str(path)) is None:
                raise RuntimeError(
                    "Existing Reticulum transport identity is invalid; restore it from a backup"
                )
            return
        # CLI observers also initialize RNS. Seed the stable identity before any
        # process starts so observers cannot race the daemon's identity creation.
        atomic_write(path, Identity().get_private_key())

    def _stable_hash(self, value: str) -> str:
        return hashlib.sha1(value.encode("utf-8")).hexdigest()[:16]

    def _parse_epoch(self, value: Any) -> datetime | None:
        if value is None:
            return None
        try:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        except (OSError, OverflowError, TypeError, ValueError):
            return None

    def _normalize_interface_name(self, raw_name: Any, short_name: Any = None) -> str:
        short = str(short_name or "").strip()
        if short and "\x00" not in short:
            return short

        raw = str(raw_name or "").strip()
        if "[" in raw and raw.endswith("]"):
            label = raw.split("[", 1)[1][:-1].strip()
            if (
                label
                and raw.startswith(
                    ("TCPInterface[", "TCPClientInterface[", "TCPServerInterface[")
                )
                and "/" in label
            ):
                label = label.split("/", 1)[0].strip()
            if label:
                return label
        return raw or "unknown"

    def _normalize_interface_type(self, raw_type: Any) -> str:
        normalized = str(raw_type or "").lower()
        if "tcp" in normalized:
            return "tcp"
        if "rnode" in normalized:
            return "rnode"
        if "serial" in normalized:
            return "serial"
        if "autointerface" in normalized or "local" in normalized:
            return "local"
        return "custom"

    def _build_synthetic_paths(
        self,
        interfaces: list[InterfaceRuntimeInfo],
        timestamp: datetime,
    ) -> tuple[list[PathEntry], list[AnnounceEvent]]:
        paths: list[PathEntry] = []
        announces: list[AnnounceEvent] = []
        for index, interface in enumerate(interfaces, start=1):
            destination_hash = self._stable_hash(f"{interface.name}:destination")
            peer_hash = self._stable_hash(f"{interface.name}:peer")
            display_name = f"{interface.name}-peer"
            paths.append(
                PathEntry(
                    destination_hash=destination_hash,
                    via_interface=interface.name,
                    next_hop=peer_hash,
                    hop_count=index,
                    expires_at=timestamp,
                    last_updated_at=timestamp,
                )
            )
            announces.append(
                AnnounceEvent(
                    source_hash=peer_hash,
                    via_interface=interface.name,
                    received_at=timestamp,
                    hop_count=index,
                    raw_summary=f"announce from {display_name}",
                    metadata={
                        "display_name": display_name,
                        "source_type": "transport",
                        "interface_name": interface.name,
                        "destination_hash": destination_hash,
                    },
                )
            )
        return paths, announces

    def _run_json_command(
        self, command: list[str] | None, extra_args: list[str]
    ) -> Any | None:
        if not command:
            return None

        try:
            completed = subprocess.run(
                [*command, *extra_args],
                check=False,
                capture_output=True,
                encoding="utf-8",
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None

        if completed.returncode != 0:
            return None

        stdout = completed.stdout.strip()
        if not stdout:
            return None

        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            return None

    def _load_real_observations(
        self,
    ) -> (
        tuple[
            list[InterfaceRuntimeInfo],
            list[PathEntry],
            list[AnnounceEvent],
            dict[str, Any],
        ]
        | None
    ):
        observer_command = [sys.executable, "-m", "hearth.reticulum.observer"]
        config_dir = str(self.settings.reticulum_config_path)
        observation = self._run_json_command(observer_command, ["--config", config_dir])
        if not isinstance(observation, dict):
            return None
        status_payload = observation.get("status")
        path_payload = observation.get("paths")
        status_command = observer_command
        path_command = observer_command

        if status_payload is None and path_payload is None:
            return None

        observed_runtime = {
            "observed_at": utcnow(),
            "observation_status": "ok"
            if isinstance(status_payload, dict) and isinstance(path_payload, list)
            else "partial",
            "interfaces_valid": isinstance(status_payload, dict),
            "paths_valid": isinstance(path_payload, list),
            "status_command": [*status_command, "--config", config_dir]
            if status_command
            else None,
            "path_command": [*path_command, "--config", config_dir]
            if path_command
            else None,
        }

        interfaces: list[InterfaceRuntimeInfo] = []
        seen_interface_names: set[str] = set()
        if isinstance(status_payload, dict):
            observed_runtime.update(
                {
                    "transport_id": status_payload.get("transport_id"),
                    "network_id": status_payload.get("network_id"),
                    "transport_uptime": status_payload.get("transport_uptime"),
                    "rss": status_payload.get("rss"),
                    "interface_count": len(status_payload.get("interfaces", [])),
                }
            )
            for item in status_payload.get("interfaces", []):
                if not isinstance(item, dict):
                    continue
                name = self._normalize_interface_name(
                    item.get("name"), item.get("short_name")
                )
                if name in seen_interface_names:
                    continue
                seen_interface_names.add(name)
                running = bool(item.get("status"))
                interfaces.append(
                    InterfaceRuntimeInfo(
                        name=name,
                        type=self._normalize_interface_type(item.get("type")),
                        enabled=True,
                        status="running" if running else "stopped",
                        health_status="healthy" if running else "warning",
                        last_seen_at=observed_runtime["observed_at"]
                        if running
                        else None,
                        metrics={
                            "rx_bytes": int(item.get("rxb", 0) or 0),
                            "tx_bytes": int(item.get("txb", 0) or 0),
                            "error_count": 0,
                            "rx_bytes_per_second": int(item.get("rxs", 0) or 0),
                            "tx_bytes_per_second": int(item.get("txs", 0) or 0),
                            "announce_queue": int(item.get("announce_queue", 0) or 0),
                            "held_announces": int(item.get("held_announces", 0) or 0),
                            "clients": int(item.get("clients", 0) or 0),
                            "peers": int(item.get("peers", 0) or 0),
                            "bitrate": int(item.get("bitrate", 0) or 0),
                        },
                        last_error=None if running else "reported as down by rnstatus",
                    )
                )

        paths: list[PathEntry] = []
        announces: list[AnnounceEvent] = []
        if isinstance(path_payload, list):
            for item in path_payload:
                if not isinstance(item, dict):
                    continue
                destination_hash = str(item.get("hash") or "").strip()
                if not destination_hash:
                    continue
                interface_name = self._normalize_interface_name(item.get("interface"))
                timestamp = self._parse_epoch(item.get("timestamp"))
                path_entry = PathEntry(
                    destination_hash=destination_hash,
                    via_interface=interface_name or None,
                    next_hop=str(item.get("via") or "").strip() or None,
                    hop_count=int(item.get("hops"))
                    if item.get("hops") is not None
                    else None,
                    expires_at=self._parse_epoch(item.get("expires")),
                    last_updated_at=timestamp,
                )
                paths.append(path_entry)

        return interfaces, paths, announces, observed_runtime

    def _rebuild_observations(self, state: RuntimeFileState) -> None:
        self._observed_runtime = {}
        runtime_status = self._state_to_runtime_status(state, allow_observed=False)
        if not runtime_status.running:
            self._observed_interfaces = []
            self._paths = []
            self._announces = []
            return

        if self.settings.reticulum.backend != "mock_process":
            try:
                observed = (
                    self._load_real_observations()
                    if self._transport_identity_ready()
                    else None
                )
            except (ValueError, TypeError, KeyError, OSError):
                observed = None
            if observed is not None:
                interfaces, paths, announces, metadata = observed
                if metadata.get("interfaces_valid", True):
                    self._observed_interfaces = interfaces
                if metadata.get("paths_valid", True):
                    self._paths = paths
                self._announces = announces
                self._observed_runtime = metadata
            else:
                self._observed_runtime = {
                    "observation_status": "unavailable",
                    "paths_valid": False,
                    "interfaces_valid": False,
                }
            return

        timestamp = (
            runtime_status.last_heartbeat_at or runtime_status.started_at or utcnow()
        )
        self._observed_interfaces = list(self._configured_interfaces)
        active_interfaces = [
            item
            for item in self._configured_interfaces
            if item.enabled and item.status == "running"
        ]
        self._paths, self._announces = self._build_synthetic_paths(
            active_interfaces, timestamp
        )

    def _read_state(self) -> RuntimeFileState:
        if not self.settings.runtime_state_path.exists():
            return RuntimeFileState(
                backend=self.settings.reticulum.backend,
                config_path=str(self.settings.reticulum_config_path),
                identity_path=str(self.settings.identity_path),
            )
        try:
            payload = json.loads(
                self.settings.runtime_state_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            return RuntimeFileState(
                backend=self.settings.reticulum.backend,
                config_path=str(self.settings.reticulum_config_path),
                identity_path=str(self.settings.identity_path),
                status="crashed",
                last_error="invalid runtime state file",
            )
        state = RuntimeFileState.from_dict(payload)
        if not state.config_path:
            state.config_path = str(self.settings.reticulum_config_path)
        if not state.identity_path:
            state.identity_path = str(self.settings.identity_path)
        return state

    def _write_state(self, state: RuntimeFileState) -> None:
        write_json_atomic(self.settings.runtime_state_path, state.to_dict())

    def _read_pid(self) -> int | None:
        try:
            return int(
                self.settings.runtime_pid_path.read_text(encoding="utf-8").strip()
            )
        except (OSError, ValueError):
            return None

    def _write_pid(self, pid: int | None) -> None:
        if pid is None:
            try:
                self.settings.runtime_pid_path.unlink()
            except FileNotFoundError:
                pass
            return
        self.settings.runtime_pid_path.write_text(f"{pid}\n", encoding="utf-8")

    def _is_pid_running(self, pid: int | None) -> bool:
        if pid is None or pid <= 0:
            return False
        try:
            process = psutil.Process(pid)
            if not process.is_running() or process.status() == psutil.STATUS_ZOMBIE:
                return False
            owned = self.control_state().get("process")
            if owned:
                if owned["pid"] == pid:
                    if abs(owned["created_at"] - process.create_time()) > 0.01:
                        return False
                else:
                    # Windows venv's python.exe launcher starts a child Python
                    # process. Accept only a descendant of our verified launcher,
                    # never an unrelated process that happens to reuse a PID.
                    if not any(
                        parent.pid == owned["pid"]
                        and abs(parent.create_time() - owned["created_at"]) <= 0.01
                        for parent in process.parents()
                    ):
                        return False
            return True
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            return True

    def _state_to_runtime_status(
        self, state: RuntimeFileState, *, allow_observed: bool = True
    ) -> NodeRuntimeStatus:
        pid = state.pid if self._is_pid_running(state.pid) else None
        running = pid is not None
        started_at = parse_datetime(state.started_at)
        heartbeat_at = parse_datetime(state.heartbeat_at)
        uptime = 0
        if running and started_at:
            uptime = int((utcnow() - started_at).total_seconds())

        if running and allow_observed and self._observed_runtime:
            heartbeat_at = self._observed_runtime.get("observed_at") or heartbeat_at
            observed_uptime = self._observed_runtime.get("transport_uptime")
            if observed_uptime is not None:
                try:
                    uptime = max(int(float(observed_uptime)), 0)
                    started_at = utcnow() - timedelta(seconds=uptime)
                except (TypeError, ValueError):
                    pass

        status = state.status
        if running:
            if status in {"starting", "stopped", "crashed"}:
                status = "running"
        else:
            if status in {"running", "starting"} and state.pid is not None:
                status = "crashed"
            elif status not in {"stopped", "crashed"}:
                status = "stopped"

        return NodeRuntimeStatus(
            status=status,
            running=running,
            started_at=started_at,
            uptime_seconds=uptime,
            restart_count=state.restart_count,
            pid=pid,
            backend=state.backend,
            last_heartbeat_at=heartbeat_at,
            last_exit_code=state.last_exit_code,
            details={
                "command": state.command,
                "config_path": state.config_path,
                "identity_path": state.identity_path,
                "state_path": str(self.settings.runtime_state_path),
                "stdout_path": str(self.settings.runtime_stdout_path),
                "stderr_path": str(self.settings.runtime_stderr_path),
                "last_error": state.last_error,
                "observation_status": self._observed_runtime.get(
                    "observation_status",
                    "mock" if state.backend == "mock_process" else "unknown",
                ),
                "observation_capabilities": {
                    "interfaces": True,
                    "paths": True,
                    "announces": state.backend == "mock_process",
                    "peers": state.backend == "mock_process",
                },
                "transport_id": self._observed_runtime.get("transport_id")
                if allow_observed
                else None,
                "network_id": self._observed_runtime.get("network_id")
                if allow_observed
                else None,
                "rss": self._observed_runtime.get("rss") if allow_observed else None,
                "interface_count": self._observed_runtime.get("interface_count")
                if allow_observed
                else None,
                "observation_commands": {
                    "rnstatus": self._observed_runtime.get("status_command")
                    if allow_observed
                    else None,
                    "rnpath": self._observed_runtime.get("path_command")
                    if allow_observed
                    else None,
                },
            },
        )

    def _build_command(self) -> list[str]:
        if self.settings.reticulum.render_managed_config:
            effective = self.settings.model_copy(deep=True)
            overrides = self.control_state().get("interfaces", {})
            for item in effective.interfaces:
                if item.name in overrides:
                    item.enabled = overrides[item.name] == "running"
            RuntimeConfigBridge(effective).sync()

        if self.settings.reticulum.backend == "managed_rnsd":
            return self._build_managed_rnsd_command()

        if self.settings.reticulum.backend == "external_process":
            if not self.settings.reticulum.command:
                raise ValueError(
                    "reticulum.command is required when backend=external_process"
                )
            return self._expand_command(list(self.settings.reticulum.command))

        return [
            sys.executable,
            "-m",
            "hearth.reticulum.worker",
            "--state-file",
            str(self.settings.runtime_state_path),
            "--heartbeat-interval",
            str(self.settings.reticulum.heartbeat_interval_sec),
            "--restart-count",
            str(self._read_state().restart_count),
            "--config-path",
            str(self.settings.reticulum_config_path),
            "--identity-path",
            str(self.settings.identity_path),
        ]

    def _expand_command(self, command: list[str]) -> list[str]:
        placeholders = {
            "config_dir": str(self.settings.reticulum_config_path),
            "config_file": str(self.settings.runtime_managed_config_path),
            "identity_path": str(self.settings.identity_path),
            "state_file": str(self.settings.runtime_state_path),
            "stdout_log": str(self.settings.runtime_stdout_path),
            "stderr_log": str(self.settings.runtime_stderr_path),
        }
        expanded: list[str] = []
        for item in command:
            text = str(item)
            try:
                expanded.append(text.format(**placeholders))
            except KeyError:
                expanded.append(text)
        return expanded

    def _build_managed_rnsd_command(self) -> list[str]:
        configured = str(self.settings.reticulum.managed_command or "").strip()
        if configured:
            base = shlex.split(configured)
        elif shutil.which("rnsd"):
            base = ["rnsd"]
        elif importlib.util.find_spec("RNS.Utilities.rnsd") is not None:
            base = [sys.executable, "-m", "RNS.Utilities.rnsd"]
        else:
            raise ValueError(
                "managed_rnsd backend requires the rnsd executable or Python module RNS.Utilities.rnsd"
            )
        command = [
            *base,
            "--config",
            str(self.settings.reticulum_config_path),
            "--service",
        ]
        return self._expand_command(command)

    async def refresh(self) -> NodeRuntimeStatus:
        state = self._read_state()
        if state.pid is None:
            state.pid = self._read_pid()

        if state.pid is not None and not self._is_pid_running(state.pid):
            if state.status in {"running", "starting"}:
                state.status = "crashed"
                state.last_exit_code = (
                    state.last_exit_code if state.last_exit_code is not None else 1
                )
            state.pid = None

        await asyncio.to_thread(self._rebuild_observations, state)
        return self._state_to_runtime_status(state)

    async def start(self, *, recovery: bool = False) -> None:
        async with self.operations.acquire():
            self._assert_current_configuration()
            if recovery and self.desired_state() != "running":
                return
            self._set_desired("running")
            await self._start()
            self._changed()

    async def _start(self) -> None:
        current = await self.refresh()
        if current.running:
            return

        if self.settings.reticulum.backend == "managed_rnsd":
            self._prepare_transport_identity()

        state = self._read_state()
        command = self._build_command()
        now = utcnow().isoformat()
        state.backend = self.settings.reticulum.backend
        state.status = "starting"
        state.started_at = now
        state.heartbeat_at = now
        state.command = command
        state.config_path = str(self.settings.reticulum_config_path)
        state.identity_path = str(self.settings.identity_path)
        state.last_exit_code = None
        state.last_error = None
        self._write_state(state)

        stdout_handle = self.settings.runtime_stdout_path.open("a", encoding="utf-8")
        stderr_handle = self.settings.runtime_stderr_path.open("a", encoding="utf-8")
        popen_kwargs: dict[str, Any] = {
            "cwd": str(self.settings.data_dir),
            "stdout": stdout_handle,
            "stderr": stderr_handle,
        }
        if os.name == "nt":
            popen_kwargs["creationflags"] = getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            ) | getattr(subprocess, "DETACHED_PROCESS", 0)
        else:
            popen_kwargs["start_new_session"] = True

        try:
            process = subprocess.Popen(command, **popen_kwargs)
        finally:
            stdout_handle.close()
            stderr_handle.close()

        state.pid = process.pid
        control = self.control_state()
        control["process"] = {
            "pid": process.pid,
            "created_at": psutil.Process(process.pid).create_time(),
        }
        self._save_control(control)
        self._write_pid(process.pid)
        self._write_state(state)

        deadline = asyncio.get_running_loop().time() + max(
            self.settings.reticulum.health_timeout_sec, 5
        )
        while asyncio.get_running_loop().time() < deadline:
            refreshed = await self.refresh()
            ready = self.settings.reticulum.backend != "managed_rnsd" or (
                self._observed_runtime.get("interfaces_valid")
                and self._observed_runtime.get("paths_valid")
            )
            if refreshed.running and ready:
                if self.settings.reticulum.backend != "mock_process":
                    state.status = "running"
                    self._write_state(state)
                return
            await asyncio.sleep(0.1)

        await self._stop()
        state = self._read_state()
        state.status = "crashed"
        state.last_error = "runtime failed to become healthy during startup"
        state.last_exit_code = (
            state.last_exit_code if state.last_exit_code is not None else 1
        )
        self._write_state(state)
        raise RuntimeError(state.last_error)

    async def stop(self, *, intentional: bool = False) -> None:
        async with self.operations.acquire():
            if intentional:
                self._assert_current_configuration()
                self._set_desired("stopped")
            await self._stop()
            self._changed()

    async def _stop(self) -> None:
        state = self._read_state()
        pid = state.pid if state.pid is not None else self._read_pid()
        if pid is not None and self._is_pid_running(pid):
            try:
                os.kill(pid, signal.SIGTERM)
            except (ProcessLookupError, PermissionError, OSError):
                pass

            deadline = (
                asyncio.get_running_loop().time()
                + self.settings.reticulum.shutdown_timeout_sec
            )
            while asyncio.get_running_loop().time() < deadline:
                if not self._is_pid_running(pid):
                    break
                await asyncio.sleep(0.1)

            if self._is_pid_running(pid):
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/T", "/F"],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    os.kill(pid, signal.SIGKILL)

        state.pid = None
        state.status = "stopped"
        state.started_at = None
        state.heartbeat_at = utcnow().isoformat()
        state.last_exit_code = 0
        self._write_pid(None)
        self._write_state(state)

    async def restart(self, *, recovery: bool = False) -> None:
        async with self.operations.acquire():
            self._assert_current_configuration()
            if recovery and self.desired_state() != "running":
                return
            self._set_desired("running")
            await self._restart()
            self._changed()

    async def _restart(self) -> None:
        state = self._read_state()
        state.restart_count += 1
        self._write_state(state)
        await self._stop()
        await self._start()

    async def control_interface(self, name: str, action: str) -> dict:
        if (
            self.settings.reticulum.backend != "managed_rnsd"
            or not self.settings.reticulum.render_managed_config
        ):
            raise NotImplementedError(
                "This runtime does not support verified interface control"
            )
        if name not in {item.name for item in self.settings.interfaces}:
            raise KeyError(f"unknown interface: {name}")
        if action not in {"start", "stop", "restart"}:
            raise ValueError(f"unknown interface action: {action}")
        async with self.operations.acquire():
            self._assert_current_configuration()
            if not self.status().running:
                raise ValueError("Start the node before operating an interface")
            previous = self.control_state()
            desired = "stopped" if action == "stop" else "running"
            updated = {
                **previous,
                "interfaces": {**previous.get("interfaces", {}), name: desired},
            }
            self._save_control(updated)
            try:
                # rnsd has no per-interface mutation API. Apply the generated
                # configuration through a node restart, then verify rnstatus.
                await self._restart()
                await self.refresh()
                if not self._observed_runtime.get("interfaces_valid"):
                    raise RuntimeError(
                        "Cannot verify interface operation: rnstatus is unavailable"
                    )
                actual = next(
                    (item for item in self.get_interfaces() if item.name == name), None
                )
                verified = (
                    (actual is None or actual.status == "stopped")
                    if desired == "stopped"
                    else (actual is not None and actual.status == "running")
                )
                if not verified:
                    raise RuntimeError(
                        f"Interface {name} did not reach requested state {desired}"
                    )
            except Exception:
                self._save_control(previous)
                await self._restart()
                raise
            finally:
                self._changed()
            return {
                "name": name,
                "status": desired,
                "desired_state": desired,
                "verified": True,
                "restart_scope": "node",
                "operation": action,
            }

    def status(self) -> NodeRuntimeStatus:
        return self._state_to_runtime_status(self._read_state())

    def get_paths(self) -> list[PathEntry]:
        return list(self._paths)

    def get_interfaces(self) -> list[InterfaceRuntimeInfo]:
        if self.settings.reticulum.backend == "mock_process":
            return list(self._observed_interfaces or self._configured_interfaces)
        return list(self._observed_interfaces)

    def set_interfaces(self, interfaces: list[InterfaceRuntimeInfo]) -> None:
        self._configured_interfaces = list(interfaces)

    def get_announces(self) -> list[AnnounceEvent]:
        return list(self._announces)
