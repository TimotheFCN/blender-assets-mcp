from pathlib import Path

import pytest

from blender_assets_mcp.common import cache_dir, inside, safe_name, url_filename, words_matched


def test_cache_dir_override(isolated_cache):
    assert cache_dir() == isolated_cache


def test_words_matched_counts_stems_and_substrings():
    assert words_matched(["wooden", "chair"], "ArmChair_01 wood furniture") == 2
    assert words_matched(["sunset"], "venice_sunset Venice Sunset") == 1
    assert words_matched(["car"], "an ox") == 0


def test_inside_rejects_traversal(tmp_path):
    assert inside(tmp_path, "textures/a.jpg") == tmp_path / "textures/a.jpg"
    for bad in ("../escape.txt", "/etc/passwd", "a/../../b"):
        with pytest.raises(ValueError):
            inside(tmp_path, bad)


def test_names_are_filesystem_safe():
    assert safe_name("../../etc") == "etc"
    assert safe_name("Brick Wall (2)") == "Brick_Wall_2"
    assert url_filename("https://x.org/a/b/model_1k.blend?sig=1/2") == "model_1k.blend"
    assert safe_name("") == "asset"
    assert "/" not in safe_name(str(Path("a") / "b"))
