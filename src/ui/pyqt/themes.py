from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Theme:
    name: str
    values: dict[str, str]

    def get(self, key: str, default: str) -> str:
        return self.values.get(key, default)


def load_themes(themes_dir: Path) -> dict[str, Theme]:
    themes: dict[str, Theme] = {}
    if not themes_dir.exists():
        return themes

    for path in sorted(themes_dir.glob("*.theme")):
        values = _parse_theme_file(path)
        theme_name = values.get("name", path.stem)
        themes[path.stem] = Theme(name=theme_name, values=values)
    return themes


def _parse_theme_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", maxsplit=1)
        values[key.strip()] = value.strip()
    return values
