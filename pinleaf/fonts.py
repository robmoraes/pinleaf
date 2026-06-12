from __future__ import annotations

import ctypes
import ctypes.util
import sys
from pathlib import Path

from pinleaf.config import resource_path


FONT_EXTENSIONS = {".ttf", ".otf"}


def bundled_font_paths() -> list[Path]:
    fonts_dir = resource_path("resources", "fonts")
    if not fonts_dir.exists():
        return []
    return [
        path
        for path in sorted(fonts_dir.rglob("*"))
        if path.is_file() and path.suffix.lower() in FONT_EXTENSIONS
    ]


def load_bundled_fonts() -> int:
    paths = bundled_font_paths()
    if not paths:
        return 0

    library_name = ctypes.util.find_library("fontconfig")
    if library_name is None:
        print("Pinleaf could not load bundled fonts: fontconfig not found.", file=sys.stderr)
        return 0

    fontconfig = ctypes.CDLL(library_name)
    fontconfig.FcConfigGetCurrent.restype = ctypes.c_void_p
    fontconfig.FcConfigAppFontAddFile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    fontconfig.FcConfigAppFontAddFile.restype = ctypes.c_int
    fontconfig.FcConfigBuildFonts.argtypes = [ctypes.c_void_p]
    fontconfig.FcConfigBuildFonts.restype = ctypes.c_int

    config = fontconfig.FcConfigGetCurrent()
    loaded = 0
    for path in paths:
        if fontconfig.FcConfigAppFontAddFile(config, str(path).encode("utf-8")):
            loaded += 1
        else:
            print(f"Pinleaf could not load bundled font: {path}", file=sys.stderr)

    if loaded:
        fontconfig.FcConfigBuildFonts(config)
    return loaded
