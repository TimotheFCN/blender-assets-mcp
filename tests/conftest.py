import pytest

from blender_assets_mcp import polyhaven


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("BLENDER_ASSETS_CACHE", str(tmp_path / "cache"))
    monkeypatch.setattr(polyhaven, "_catalogs", {})
    return tmp_path / "cache"
