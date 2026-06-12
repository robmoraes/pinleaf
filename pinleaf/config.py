from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "pinleaf"
DB_FILENAME = "pinleaf.sqlite3"
PACKAGE_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    database_path: Path


def default_data_dir(env: dict[str, str] | None = None) -> Path:
    values = env if env is not None else os.environ
    xdg_data_home = values.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def load_config(env: dict[str, str] | None = None) -> AppConfig:
    data_dir = default_data_dir(env)
    return AppConfig(data_dir=data_dir, database_path=data_dir / DB_FILENAME)


def ensure_data_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        path.chmod(0o700)
    except OSError:
        # Some filesystems do not allow chmod. Directory creation still gives
        # us the best available platform behavior.
        pass


def resource_path(*parts: str) -> Path:
    return PACKAGE_ROOT.joinpath(*parts)


def icon_path(size: int | None = None) -> Path:
    filename = f"pinleaf-{size}.png" if size else "pinleaf.png"
    return resource_path("resources", "icons", filename)


def icon_svg_path() -> Path:
    return resource_path("resources", "icons", "pinleaf.svg")
