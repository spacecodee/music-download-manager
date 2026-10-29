"""Detect and install a Nerd Font (JetBrainsMono) for the TUI icons."""

import io
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

FONT_NAME = "JetBrainsMono Nerd Font"
FONT_URL = "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip"
_PREFIX = "JetBrainsMonoNerdFont-"


def user_font_dir() -> Path | None:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Fonts"
    if sys.platform.startswith("linux"):
        return Path.home() / ".local" / "share" / "fonts"
    return None


def _search_dirs() -> list[Path]:
    dirs = [Path("/Library/Fonts"), Path("/usr/share/fonts"), Path("/usr/local/share/fonts")]
    user = user_font_dir()
    return ([user] if user else []) + dirs


def is_installed() -> bool:
    """True if any Nerd Font file is present in the system or user font folders."""
    for d in _search_dirs():
        if d.is_dir() and next(d.rglob("*NerdFont*.ttf"), None) is not None:
            return True
    return False


def install() -> Path:
    """Download JetBrainsMono Nerd Font into the user font folder. Raises on failure."""
    target = user_font_dir()
    if target is None:
        raise RuntimeError(f"Automatic font install is not supported on {sys.platform}.")
    with urllib.request.urlopen(FONT_URL, timeout=60) as resp:
        data = resp.read()
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        for member in zf.namelist():
            name = Path(member).name  # basename only: never trust archive paths
            if name.startswith(_PREFIX) and name.endswith(".ttf"):
                (target / name).write_bytes(zf.read(member))
    if sys.platform.startswith("linux"):
        subprocess.run(["fc-cache", "-f", str(target)], capture_output=True, timeout=60, check=False)
    if not is_installed():
        raise RuntimeError("Font download finished but no font files were installed.")
    return target
