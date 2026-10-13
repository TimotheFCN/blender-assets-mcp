# blender-assets-mcp

An MCP server that lets AI agents find and download free models, PBR materials and HDRI
environments for Blender. It searches three libraries:

| Source | What it has | License |
| --- | --- | --- |
| [Poly Haven](https://polyhaven.com) | Models, textures, HDRIs | CC0 |
| [ambientCG](https://ambientcg.com) | PBR materials, HDRIs | CC0 |
| [BlenderKit](https://www.blenderkit.com) | Models, materials, HDRIs | Free assets only: CC0 or BlenderKit Royalty Free |

No account or API key is needed. Free BlenderKit assets download anonymously. The server
refuses paid BlenderKit assets, even if the API would serve them.

The server doesn't control Blender itself. Each download returns a short Python script, and
the agent runs it with whatever Blender MCP it already has, such as the
[Blender Lab MCP server](https://www.blender.org/lab/mcp-server/) or
[MCP for Blender](https://github.com/ahujasid/blender-mcp) (both have an
`execute_blender_code` tool). That keeps this server small and lets it work with either one.

## Install

You need [uv](https://docs.astral.sh/uv/). Run it straight from GitHub:

```sh
uvx --from git+https://github.com/TimotheFCN/blender-assets-mcp blender-assets-mcp
```

Or install it once and get a `blender-assets-mcp` command:

```sh
uv tool install git+https://github.com/TimotheFCN/blender-assets-mcp
```

### Claude Code

```sh
claude mcp add --scope user blender_assets -- uvx --from git+https://github.com/TimotheFCN/blender-assets-mcp blender-assets-mcp
```

### Codex

In `~/.codex/config.toml`:

```toml
[mcp_servers.blender_assets]
command = "uvx"
args = ["--from", "git+https://github.com/TimotheFCN/blender-assets-mcp", "blender-assets-mcp"]
tool_timeout_sec = 300  # large downloads can take longer than the 60 s default
```

### Other clients

Any MCP client that starts stdio servers works. Use the same command and arguments.

## Tools

`search_free_assets(query, kind="any", sources=None, limit=8)`
searches every source at once and returns id, name, kind, license, author and a thumbnail
URL for each hit. `kind` is `model`, `material`, `hdri` or `any`. `limit` applies per
source, up to 25. If one source fails, its error goes in `errors` and the others still return.

`download_free_asset(source, asset_id, resolution="1k")`
downloads into the cache and returns:

- `path`: the downloaded file (a folder for ambientCG materials)
- `license` and `attribution`: put the attribution in your project's credits
- `blender_python`: code to run inside Blender

What the code does depends on the asset kind:

- Models are appended from their `.blend` into a new collection named after the asset.
  Cameras and lights in the file are skipped.
- Materials are appended, or built as a Principled BSDF from ambientCG's texture maps.
  The agent still has to assign them to objects.
- HDRIs replace the scene's world with an environment texture.

Resolutions are `1k`, `2k` and `4k`. BlenderKit also accepts `0.5k` and `original`, and falls
back to the original file when an asset has no smaller version.

## Cache

Downloads go to `$BLENDER_ASSETS_CACHE`, or `$XDG_CACHE_HOME/blender-assets`, or
`~/.cache/blender-assets`, in that order. Several agents can share one cache. Files are
written to a temporary name and renamed, so a reader never sees half a download. A folder
only counts as complete once its `.complete` marker exists. The Poly Haven catalog is cached
for a day.

## Licenses of the assets

CC0 assets are public domain. Credit is optional, but the server still returns a credit line.

BlenderKit's Royalty Free license lets you use an asset in any project, including commercial
ones. You can't resell or redistribute the asset file on its own. Read the
[BlenderKit license terms](https://www.blenderkit.com/docs/licenses/) before you ship
anything built with them.

## Safety

Asset libraries send back file paths, and ambientCG sends zip archives. The server refuses any
path that would land outside the asset's cache folder, so a crafted `../` entry can't write
elsewhere on disk.

The returned `blender_python` only loads files from the cache. Still, it is code that runs
in your Blender, so read it if you're not sure.

## Development

```sh
uv run pytest
uv run ruff check
```

The tests run offline and stub the network. To try the server by hand, point an MCP client
at `uv run blender-assets-mcp`.

This project isn't affiliated with Poly Haven, ambientCG, BlenderKit or the Blender Foundation.

## License

MIT
