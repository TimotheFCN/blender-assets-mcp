import io
import zipfile

import pytest

from blender_assets_mcp import ambientcg, blenderkit, polyhaven, server

CATALOGS = {
    "models": {
        "modern_arm_chair_01": {"name": "Modern Arm Chair 01", "tags": ["chair", "wood"], "download_count": 10},
        "wooden_table_02": {"name": "Wooden Table 02", "tags": ["wood", "table"], "download_count": 50},
    },
    "textures": {},
    "hdris": {
        "photo_studio": {"name": "Photo Studio", "tags": ["chair", "wood"], "download_count": 9999},
    },
}


@pytest.fixture
def fake_polyhaven(monkeypatch):
    monkeypatch.setattr(polyhaven, "catalog", lambda kind: CATALOGS[polyhaven.TYPES[kind]])


def test_polyhaven_name_hits_outrank_popular_tag_hits(fake_polyhaven):
    ids = [r["id"] for r in polyhaven.search("wooden chair", ["model", "material", "hdri"], 5)]
    assert ids[0] == "modern_arm_chair_01"
    assert "photo_studio" in ids


def test_polyhaven_limit_and_empty_query(fake_polyhaven):
    assert len(polyhaven.search("", ["model"], 1)) == 1
    assert polyhaven.search("spaceship", ["model"], 5) == []


def bk_asset(free, asset_type="model"):
    return {
        "assetBaseId": "abc", "name": "Chair", "assetType": asset_type, "isFree": free,
        "license": "royalty_free", "author": {"fullName": "Someone"}, "files": [],
    }


def test_blenderkit_search_drops_paid_assets(monkeypatch):
    monkeypatch.setattr(blenderkit, "query", lambda text, size: [bk_asset(True), bk_asset(False)])
    results = blenderkit.search("chair", ["model"], 5)
    assert len(results) == 1
    assert results[0]["license"].startswith("BlenderKit Royalty Free")


def test_blenderkit_fetch_refuses_paid_assets(monkeypatch):
    monkeypatch.setattr(blenderkit, "query", lambda text, size: [bk_asset(False)])
    with pytest.raises(ValueError, match="not a free"):
        blenderkit.fetch("abc", "1k")


def test_blenderkit_fetch_refuses_unsupported_types(monkeypatch):
    monkeypatch.setattr(blenderkit, "query", lambda text, size: [bk_asset(True, "brush")])
    with pytest.raises(ValueError, match="only models"):
        blenderkit.fetch("abc", "1k")


def test_ambientcg_extract_refuses_zip_traversal(tmp_path):
    archive = tmp_path / "evil.zip"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Bricks_Color.jpg", b"ok")
        zf.writestr("../../escape.txt", b"bad")
    archive.write_bytes(buf.getvalue())
    with pytest.raises(ValueError, match="outside"):
        ambientcg.extract(archive, tmp_path / "out")
    assert not (tmp_path / "escape.txt").exists()


def test_search_tool_reports_failing_sources(monkeypatch, fake_polyhaven):
    def broken(*args):
        raise RuntimeError("down")

    monkeypatch.setattr(ambientcg, "search", broken)
    monkeypatch.setattr(blenderkit, "search", lambda *a: [])
    out = server.search_free_assets("chair", kind="model")
    assert out["errors"] == {"ambientcg": "down"}
    assert out["results"][0]["source"] == "polyhaven"


def test_tools_validate_arguments():
    with pytest.raises(ValueError):
        server.search_free_assets("x", kind="sound")
    with pytest.raises(ValueError):
        server.search_free_assets("x", sources=["sketchfab"])
    with pytest.raises(ValueError):
        server.download_free_asset("sketchfab", "x")
