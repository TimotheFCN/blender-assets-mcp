"""Poly Haven: CC0 models, textures and HDRIs (https://polyhaven.com)."""
import json
import time
import urllib.parse

from . import snippets
from .common import CC0, KINDS, asset_dir, cache_dir, download, get_json, inside, url_filename, words_matched

TYPES = {"model": "models", "material": "textures", "hdri": "hdris"}
CATALOG_TTL = 86400
_catalogs: dict[str, dict] = {}


def catalog(kind: str) -> dict:
    """All assets of a kind, keyed by id. The API has no search, so we filter locally."""
    ph_type = TYPES[kind]
    if ph_type not in _catalogs:
        cached = cache_dir() / f"polyhaven-{ph_type}.json"
        if cached.exists() and time.time() - cached.stat().st_mtime < CATALOG_TTL:
            _catalogs[ph_type] = json.loads(cached.read_text())
        else:
            data = get_json("https://api.polyhaven.com/assets", {"type": ph_type})
            cached.parent.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps(data))
            _catalogs[ph_type] = data
    return _catalogs[ph_type]


def search(query: str, kinds: list[str], limit: int) -> list[dict]:
    words = query.lower().split()
    hits = []
    for kind in kinds:
        for asset_id, info in catalog(kind).items():
            name = f"{asset_id} {info.get('name', '')}"
            tags = " ".join([*info.get("tags", []), *info.get("categories", [])])
            total = words_matched(words, f"{name} {tags}")
            if total or not words:
                # Name hits outrank tag hits, so a chair beats a studio HDRI tagged "chair".
                hits.append(((words_matched(words, name), total, info.get("download_count", 0)), kind, asset_id, info))
    hits.sort(key=lambda h: h[0], reverse=True)
    return [
        {
            "source": "polyhaven",
            "id": asset_id,
            "name": info.get("name", asset_id),
            "kind": kind,
            "license": CC0,
            "author": ", ".join(info.get("authors", {})),
            "page": f"https://polyhaven.com/a/{asset_id}",
            "thumbnail": f"https://cdn.polyhaven.com/asset_img/thumbs/{asset_id}.png?height=256",
        }
        for _, kind, asset_id, info in hits[:limit]
    ]


def fetch(asset_id: str, resolution: str) -> dict:
    kind = next((k for k in KINDS if asset_id in catalog(k)), None)
    if kind is None:
        raise ValueError(f"unknown Poly Haven asset: {asset_id}")
    info = catalog(kind)[asset_id]
    files = get_json(f"https://api.polyhaven.com/files/{urllib.parse.quote(asset_id)}")
    group, fmt = ("hdri", "hdr") if kind == "hdri" else ("blend", "blend")
    by_res = files.get(group, {})
    if resolution not in by_res:
        raise ValueError(f"{asset_id} has no {resolution} file; available: {sorted(by_res)}")
    entry = by_res[resolution][fmt]
    root = asset_dir("polyhaven", asset_id, resolution)
    main = root / url_filename(entry["url"])
    if not (root / ".complete").exists():
        for rel, inc in entry.get("include", {}).items():
            download(inc["url"], inside(root, rel))
        download(entry["url"], main)
        (root / ".complete").touch()
    name = info.get("name", asset_id)
    if kind == "hdri":
        code = snippets.set_world_hdri(main)
    elif kind == "material":
        code = snippets.import_blend_materials(main)
    else:
        code = snippets.import_blend_objects(main, name)
    return {
        "kind": kind,
        "path": str(main),
        "license": CC0,
        "attribution": f"{name} by {', '.join(info.get('authors', {}))}, Poly Haven (CC0)",
        "blender_python": code,
    }
