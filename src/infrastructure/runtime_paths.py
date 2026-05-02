from __future__ import annotations

import sys
from pathlib import Path


def get_app_root(default_root: Path) -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return default_root.resolve()


def get_resource_root(default_root: Path) -> Path:
    if getattr(sys, "frozen", False):
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            return Path(bundle_root).resolve()
    return default_root.resolve()
