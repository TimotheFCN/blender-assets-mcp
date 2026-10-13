"""HTTP, cache and path helpers shared by the asset sources."""
import json
import os
import re
import shutil
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from . import __version__

USER_AGENT = f"blender-assets-mcp/{__version__} (+https://github.com/TimotheFCN/blender-assets-mcp)"
KINDS = ("model", "material", "hdri")
CC0 = "CC0 1.0 (public domain, no attribution required)"


def cache_dir() -> Path:
    if override := os.environ.get("BLENDER_ASSETS_CACHE"):
        return Path(override)
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "blender-assets"


def get_json(url: str, params: dict | None = None) -> dict:
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def download(url: str, dest: Path) -> Path:
    """Download to a temporary file beside dest, then rename, so readers never see partial files."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as resp, tempfile.NamedTemporaryFile(
        dir=dest.parent, delete=False
    ) as tmp:
        shutil.copyfileobj(resp, tmp)
    Path(tmp.name).replace(dest)
    return dest


def inside(root: Path, rel: str) -> Path:
    """Resolve a server-supplied relative path, refusing anything outside root."""
    path = (root / rel).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"refusing path outside the asset folder: {rel}")
    return path


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("._") or "asset"


def url_filename(url: str) -> str:
    return safe_name(Path(urllib.parse.urlparse(url).path).name)


def asset_dir(source: str, asset_id: str, resolution: str) -> Path:
    return cache_dir() / source / safe_name(asset_id) / safe_name(resolution)


def words_matched(words: list[str], text: str) -> int:
    """Count query words found in a word of text, or sharing its stem ("wooden" matches "wood")."""
    tokens = {t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= 3}
    return sum(any(w in t or w.startswith(t) for t in tokens) for w in words)
