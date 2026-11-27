import io
import zipfile

import pytest

from blender_assets_mcp import ambientcg, blenderkit, polyhaven, server, sketchfab

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
    monkeypatch.setattr(sketchfab, "search", lambda *a: [])
    out = server.search_free_assets("chair", kind="model")
    assert out["errors"] == {"ambientcg": "down"}
    assert out["results"][0]["source"] == "polyhaven"


def test_tools_validate_arguments():
    with pytest.raises(ValueError):
        server.search_free_assets("x", kind="sound")
    with pytest.raises(ValueError):
        server.search_free_assets("x", sources=["turbosquid"])
    with pytest.raises(ValueError):
        server.download_free_asset("turbosquid", "x")


def sf_model(slug="by", downloadable=True):
    labels = {"by": "CC Attribution", "by-nc": "CC Attribution-NonCommercial", "st": "Standard"}
    return {
        "uid": "u1", "name": "Chair", "isDownloadable": downloadable,
        "license": {"slug": slug, "label": labels[slug], "url": "http://creativecommons.org/licenses/by/4.0/"},
        "user": {"displayName": "Someone"},
        "thumbnails": {"images": [{"width": 64, "url": "small"}, {"width": 256, "url": "mid"}]},
    }


def test_sketchfab_search_only_models(monkeypatch):
    monkeypatch.setattr(sketchfab, "get_json", lambda *a, **k: {"results": [sf_model(), sf_model("by-nc")]})
    assert sketchfab.search("chair", ["material", "hdri"], 5) == []
    results = sketchfab.search("chair", ["model"], 5)
    assert [r["commercial_use"] for r in results] == [True, False]
    assert results[0]["thumbnail"] == "mid"
    assert results[0]["page"] == "https://sketchfab.com/3d-models/u1"


def test_sketchfab_fetch_refuses_store_licenses(monkeypatch):
    monkeypatch.setattr(sketchfab, "get_json", lambda *a, **k: sf_model("st"))
    with pytest.raises(ValueError, match="only free licenses"):
        sketchfab.fetch("u1", "1k")


def test_sketchfab_fetch_needs_token(monkeypatch):
    monkeypatch.delenv(sketchfab.TOKEN_ENV, raising=False)
    monkeypatch.setattr(sketchfab, "get_json", lambda *a, **k: sf_model())
    with pytest.raises(ValueError, match=sketchfab.TOKEN_ENV):
        sketchfab.fetch("u1", "1k")


def test_sketchfab_fetch_extracts_gltf(monkeypatch, tmp_path):
    monkeypatch.setenv(sketchfab.TOKEN_ENV, "secret")
    calls = []

    def fake_json(url, params=None, headers=None):
        calls.append((url, headers))
        if url.endswith("/download"):
            return {"gltf": {"url": "https://x/model.zip"}}
        return sf_model()

    def fake_download(url, dest):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("scene.gltf", "{}")
            zf.writestr("textures/a.png", b"png")
        dest.write_bytes(buf.getvalue())
        return dest

    monkeypatch.setattr(sketchfab, "get_json", fake_json)
    monkeypatch.setattr(sketchfab, "download", fake_download)
    out = sketchfab.fetch("u1", "1k")
    assert out["path"].endswith("scene.gltf")
    assert "import_scene.gltf" in out["blender_python"]
    assert "by Someone on Sketchfab" in out["attribution"]
    assert calls[1][1] == {"Authorization": "Token secret"}
