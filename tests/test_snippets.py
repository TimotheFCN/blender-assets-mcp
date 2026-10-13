from pathlib import Path

from blender_assets_mcp import snippets

TRICKY = Path("/tmp/it's a \"path\"/asset.blend")


def test_snippets_are_valid_python_even_with_quotes_in_paths():
    code = [
        snippets.import_blend_objects(TRICKY, "Chair 'deluxe'"),
        snippets.import_blend_materials(TRICKY),
        snippets.set_world_hdri(TRICKY),
        snippets.build_material("Bricks", {"color": TRICKY, "normal": TRICKY}),
    ]
    for source in code:
        compile(source, "<snippet>", "exec")
        assert "result =" in source
