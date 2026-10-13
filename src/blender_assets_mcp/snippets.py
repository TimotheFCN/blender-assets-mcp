"""Python for Blender that imports a downloaded asset.

Each function returns source code for a Blender MCP tool that runs Python, such as
execute_blender_code. The code sets `result` to a summary of what it added.
"""
import json
from pathlib import Path


def import_blend_objects(path: Path, name: str) -> str:
    return f"""import bpy
with bpy.data.libraries.load({str(path)!r}, link=False) as (src, dst):
    dst.objects = list(src.objects)
coll = bpy.data.collections.new({name!r})
bpy.context.scene.collection.children.link(coll)
added = []
for obj in dst.objects:
    if obj is not None and obj.type not in {{"CAMERA", "LIGHT"}}:
        coll.objects.link(obj)
        added.append(obj.name)
result = {{"collection": coll.name, "objects": added}}
"""


def import_blend_materials(path: Path) -> str:
    return f"""import bpy
with bpy.data.libraries.load({str(path)!r}, link=False) as (src, dst):
    dst.materials = list(src.materials)
result = {{"materials": [m.name for m in dst.materials if m is not None]}}
"""


def set_world_hdri(path: Path) -> str:
    return f"""import bpy
scene = bpy.context.scene
world = scene.world or bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
nodes, links = world.node_tree.nodes, world.node_tree.links
nodes.clear()
env = nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load({str(path)!r}, check_existing=True)
bg = nodes.new("ShaderNodeBackground")
out = nodes.new("ShaderNodeOutputWorld")
links.new(env.outputs["Color"], bg.inputs["Color"])
links.new(bg.outputs["Background"], out.inputs["Surface"])
result = {{"world": world.name, "image": env.image.name}}
"""


def build_material(name: str, maps: dict[str, Path]) -> str:
    """Principled BSDF material from texture maps keyed color, roughness, metalness,
    opacity, normal (OpenGL convention) and displacement."""
    return f"""import bpy
maps = {json.dumps({k: str(v) for k, v in maps.items()})}
mat = bpy.data.materials.new({name!r})
mat.use_nodes = True
nt = mat.node_tree
bsdf = nt.nodes["Principled BSDF"]
out = nt.nodes["Material Output"]
uv = nt.nodes.new("ShaderNodeTexCoord")
def tex(key, color):
    node = nt.nodes.new("ShaderNodeTexImage")
    node.image = bpy.data.images.load(maps[key], check_existing=True)
    node.image.colorspace_settings.name = "sRGB" if color else "Non-Color"
    nt.links.new(uv.outputs["UV"], node.inputs["Vector"])
    return node
if "color" in maps:
    nt.links.new(tex("color", True).outputs["Color"], bsdf.inputs["Base Color"])
if "roughness" in maps:
    nt.links.new(tex("roughness", False).outputs["Color"], bsdf.inputs["Roughness"])
if "metalness" in maps:
    nt.links.new(tex("metalness", False).outputs["Color"], bsdf.inputs["Metallic"])
if "opacity" in maps:
    nt.links.new(tex("opacity", False).outputs["Color"], bsdf.inputs["Alpha"])
if "normal" in maps:
    nmap = nt.nodes.new("ShaderNodeNormalMap")
    nt.links.new(tex("normal", False).outputs["Color"], nmap.inputs["Color"])
    nt.links.new(nmap.outputs["Normal"], bsdf.inputs["Normal"])
if "displacement" in maps:
    disp = nt.nodes.new("ShaderNodeDisplacement")
    disp.inputs["Scale"].default_value = 0.05
    nt.links.new(tex("displacement", False).outputs["Color"], disp.inputs["Height"])
    nt.links.new(disp.outputs["Displacement"], out.inputs["Displacement"])
result = {{"material": mat.name, "maps": sorted(maps)}}
"""
