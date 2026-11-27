"""MCP server: search and download free Blender assets."""
from concurrent.futures import ThreadPoolExecutor

from mcp.server.fastmcp import FastMCP

from . import ambientcg, blenderkit, polyhaven, sketchfab
from .common import KINDS

SOURCES = {"polyhaven": polyhaven, "ambientcg": ambientcg, "blenderkit": blenderkit, "sketchfab": sketchfab}

mcp = FastMCP(
    "blender-assets",
    instructions=(
        "Find and download free 3D assets: models, PBR materials and HDRI environments from "
        "Poly Haven, ambientCG, BlenderKit (free assets only) and Sketchfab (free-license "
        "models). Call search_free_assets, then download_free_asset, then run the returned "
        "blender_python with a Blender MCP tool that executes Python, such as "
        "execute_blender_code. Record the returned license and attribution in the project when "
        "you ship an asset. Many Sketchfab models need credit, and some forbid commercial use: "
        "check commercial_use and tell the user the license and author."
    ),
)


@mcp.tool()
def search_free_assets(
    query: str,
    kind: str = "any",
    sources: list[str] | None = None,
    limit: int = 8,
) -> dict:
    """Search free 3D assets on Poly Haven, ambientCG, BlenderKit and Sketchfab.

    kind: "model", "material", "hdri" or "any". sources: any of "polyhaven", "ambientcg",
    "blenderkit", "sketchfab" (default: all). limit: results per source, at most 25.
    ambientCG has no models; Sketchfab has only models. Each result has a thumbnail URL;
    download and view it to judge the look. Sketchfab results carry commercial_use: false
    when the license forbids commercial use.
    """
    kinds = list(KINDS) if kind == "any" else [kind]
    if not set(kinds) <= set(KINDS):
        raise ValueError(f"kind must be one of {KINDS} or 'any'")
    chosen = sources or list(SOURCES)
    if not set(chosen) <= set(SOURCES):
        raise ValueError(f"sources must be among {tuple(SOURCES)}")
    limit = max(1, min(limit, 25))
    out: dict = {"results": [], "errors": {}}
    with ThreadPoolExecutor(len(chosen)) as pool:
        futures = {name: pool.submit(SOURCES[name].search, query, kinds, limit) for name in chosen}
    for name, future in futures.items():
        try:
            out["results"] += future.result()
        except Exception as ex:
            out["errors"][name] = str(ex)
    return out


@mcp.tool()
def download_free_asset(source: str, asset_id: str, resolution: str = "1k") -> dict:
    """Download a free asset into the local cache and return how to import it.

    source and asset_id come from search_free_assets. resolution: "1k", "2k", "4k"
    (BlenderKit also accepts "0.5k" and "original"; Sketchfab ignores it and serves glTF).
    Sketchfab downloads need $SKETCHFAB_API_TOKEN. Returns the local path, license,
    attribution, and blender_python: code to run with a Blender MCP tool that executes
    Python. It imports models into a new collection, appends materials (assign them
    yourself), or sets an HDRI as the world.
    """
    if source not in SOURCES:
        raise ValueError(f"source must be one of {tuple(SOURCES)}")
    return {"source": source, "id": asset_id, **SOURCES[source].fetch(asset_id, resolution.lower())}


def main() -> None:
    mcp.run()
