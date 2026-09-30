"""Read-only deployment verification, with an optional management restart check."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import time
import tomllib
import urllib.error
import urllib.request
from urllib.parse import quote


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("/etc/hearth/hearth.toml"))
    parser.add_argument("--restart-management", action="store_true")
    args = parser.parse_args()
    settings = tomllib.loads(args.config.read_text(encoding="utf-8"))
    base = f"http://127.0.0.1:{settings['web']['port']}"
    token = settings["security"]["admin_token"]

    def fetch(path: str, authenticated: bool = True):
        request = urllib.request.Request(
            base + path, headers={"X-Hearth-Token": token} if authenticated else {}
        )
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, response.read()

    before = json.loads(fetch("/api/node/status")[1])
    assert before["runtime_status"] == "running", before["runtime_status"]
    assert before["health_status"] == "healthy", before["issues"]
    pages = {
        path: fetch(path)[0]
        for path in (
            "/",
            "/interfaces?lang=zh-CN",
            "/metrics-dashboard?lang=en",
            "/config?lang=zh-CN",
            "/roles?lang=en",
            "/static/island/hearth.js",
            "/static/island/hearth.css",
        )
    }
    for interface in before["interfaces"]:
        encoded = quote(interface["name"], safe="")
        pages[f"/interfaces/{encoded}"] = fetch(f"/interfaces/{encoded}")[0]
        assert fetch(f"/api/interfaces/{encoded}/metrics")[0] == 200
    try:
        fetch("/api/config/status", authenticated=False)
    except urllib.error.HTTPError as error:
        assert error.code in {401, 403}
    else:
        raise AssertionError(
            "Protected configuration endpoint accepted an unauthenticated request"
        )
    config_state = json.loads(fetch("/api/config/status")[1])
    assert config_state["pending"] is False
    version = json.loads(fetch("/openapi.json")[1])["info"]["version"]
    after = before
    if args.restart_management:
        subprocess.run(
            ["sudo", "-n", "systemctl", "restart", "hearth.service"], check=True
        )
        for _ in range(45):
            try:
                after = json.loads(fetch("/api/node/status")[1])
                if after["health_status"] == "healthy":
                    break
            except (OSError, urllib.error.URLError):
                pass
            time.sleep(1)
        assert before["runtime"]["pid"] == after["runtime"]["pid"], (
            "Management restart interrupted the runtime"
        )
        assert after["health_status"] == "healthy"
    print(
        json.dumps(
            {
                "version": version,
                "health": after["health_status"],
                "runtime": after["runtime_status"],
                "runtime_pid_preserved": before["runtime"]["pid"]
                == after["runtime"]["pid"],
                "management_restart_tested": args.restart_management,
                "pages": pages,
                "interfaces": [
                    {
                        "name": row["name"],
                        "managed": row.get("managed"),
                        "status": row["status"],
                    }
                    for row in after["interfaces"]
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
