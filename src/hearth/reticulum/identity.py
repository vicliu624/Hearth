from __future__ import annotations

from pathlib import Path


class IdentityManager:
    def __init__(self, identity_path: Path) -> None:
        self.identity_path = identity_path

    def ensure_identity(self) -> Path:
        self.identity_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.identity_path.exists():
            self.identity_path.write_text("hearth-placeholder-identity\n", encoding="utf-8")
        return self.identity_path

