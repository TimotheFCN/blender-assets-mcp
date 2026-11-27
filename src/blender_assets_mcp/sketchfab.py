"""Sketchfab: downloadable models under free licenses (https://sketchfab.com).

Search needs no account. Downloads need a Sketchfab API token in $SKETCHFAB_API_TOKEN
(https://sketchfab.com/settings/password). Store-bought models (Standard and Editorial
licenses) are refused, so agents only pull models that are free to everyone.

Most models are Creative Commons and need credit. Sketchfab's guidelines ask apps to show
the license, the author and a link to the model page, and to say that models come from
Sketchfab, so every result carries those.
"""
import os
import tempfile
import urllib.error
import urllib.parse
from pathlib import Path

from . import snippets
from .common import asset_dir, download, extract, get_json

API = "https://api.sketchfab.com/v3"
TOKEN_ENV = "SKETCHFAB_API_TOKEN"
# Licenses anyone can download for free. "st" and "ed" are paid store licenses.
FREE_LICENSES = {"cc0", "by", "by-sa", "by-nd", "by-nc", "by-nc-sa", "by-nc-nd", "free-st"}


def license_text(lic: dict) -> str:
    label = lic.get("label") or lic.get("fullName") or "unknown license"
    if lic.get("requirements"):
        label += f": {lic['requirements']}"
    return label


def page_url(model: dict) -> str:
    return f"https://sketchfab.com/3d-models/{model['uid']}"


def search(text: str, kinds: list[str], limit: int) -> list[dict]:
    if "model" not in kinds:
        return []  # Sketchfab has no standalone materials or HDRIs
    params = {"type": "models", "q": text, "downloadable": "true", "count": limit}
    found = get_json(f"{API}/search", params).get("results", [])
    return [
        {
            "source": "sketchfab",
            "id": m["uid"],
            "name": m.get("name", ""),
            "kind": "model",
            "license": license_text(m.get("license") or {}),
            "commercial_use": "NonCommercial" not in (m.get("license") or {}).get("label", ""),
            "author": (m.get("user") or {}).get("displayName", ""),
            "description": (m.get("description") or "")[:200],
            "page": page_url(m),
            "thumbnail": thumbnail(m),
            "face_count": m.get("faceCount"),
        }
        for m in found
        if m.get("isDownloadable")
    ][:limit]


def thumbnail(model: dict) -> str:
    """The smallest thumbnail at least 256 px wide, or the largest one."""
    images = sorted((model.get("thumbnails") or {}).get("images", []), key=lambda i: i.get("width", 0))
    return next((i["url"] for i in images if i.get("width", 0) >= 256), images[-1]["url"] if images else "")


def download_links(uid: str, token: str) -> dict:
    try:
        return get_json(f"{API}/models/{urllib.parse.quote(uid)}/download", headers={"Authorization": f"Token {token}"})
    except urllib.error.HTTPError as ex:
        if ex.code == 401:
            raise ValueError(f"Sketchfab rejected the API token in ${TOKEN_ENV}") from ex
        raise


def fetch(asset_id: str, resolution: str) -> dict:
    # Sketchfab serves one glTF archive per model; resolution doesn't apply.
    model = get_json(f"{API}/models/{urllib.parse.quote(asset_id)}")
    lic = model.get("license") or {}
    name = model.get("name") or asset_id
    if not model.get("isDownloadable"):
        raise ValueError(f"{name} is not downloadable from Sketchfab")
    if lic.get("slug") not in FREE_LICENSES:
        raise ValueError(f"{name} uses the {lic.get('label', 'unknown')} license; only free licenses are allowed")
    root = asset_dir("sketchfab", asset_id, "gltf")
    if not (root / ".complete").exists():
        token = os.environ.get(TOKEN_ENV)
        if not token:
            raise ValueError(
                f"Sketchfab downloads need an API token. Set ${TOKEN_ENV} to the token from "
                "https://sketchfab.com/settings/password"
            )
        links = download_links(asset_id, token)
        if "glb" in links:
            download(links["glb"]["url"], root / "scene.glb")
        elif "gltf" in links:
            with tempfile.TemporaryDirectory() as tmp:
                extract(download(links["gltf"]["url"], Path(tmp) / "model.zip"), root)
        else:
            raise ValueError(f"{name} has no glTF download; available: {sorted(links)}")
        (root / ".complete").touch()
    main = next(
        (p for pattern in ("scene.glb", "scene.gltf", "*.glb", "*.gltf") for p in sorted(root.rglob(pattern))),
        None,
    )
    if main is None:
        raise ValueError(f"no .gltf or .glb file in the Sketchfab download for {name}")
    user = model.get("user") or {}
    author = user.get("displayName") or user.get("username") or "unknown"
    lic_name = lic.get("label", "unknown license")
    lic_url = f" ({lic['url']})" if lic.get("url") else ""
    return {
        "kind": "model",
        "path": str(main),
        "license": license_text(lic),
        "commercial_use": not lic.get("slug", "").startswith("by-nc"),
        "page": page_url(model),
        "attribution": f'"{name}" ({page_url(model)}) by {author} on Sketchfab, licensed under {lic_name}{lic_url}',
        "blender_python": snippets.import_gltf(main, name),
    }
