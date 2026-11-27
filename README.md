# blender-assets-mcp

An MCP server that lets AI agents find and download free models, PBR materials and HDRI
environments for Blender. It searches four libraries:

| Source | What it has | License |
| --- | --- | --- |
| [Poly Haven](https://polyhaven.com) | Models, textures, HDRIs | CC0 |
| [ambientCG](https://ambientcg.com) | PBR materials, HDRIs | CC0 |
| [BlenderKit](https://www.blenderkit.com) | Models, materials, HDRIs | Free assets only: CC0 or BlenderKit Royalty Free |
| [Sketchfab](https://sketchfab.com) | Models | Free licenses only: Creative Commons or Free Standard |

No account or API key is needed for Poly Haven, ambientCG and BlenderKit. Free BlenderKit
assets download anonymously. The server refuses paid BlenderKit assets, even if the API would
serve them.

Sketchfab search works without an account, but Sketchfab only serves downloads to signed-in
users. To download from Sketchfab, set `SKETCHFAB_API_TOKEN` to the API token from your
[Sketchfab password settings](https://sketchfab.com/settings/password). The server refuses
models under the paid store licenses (Standard and Editorial).

The server doesn't control Blender itself. Each download returns a short Python script, and
the agent runs it with whatever Blender MCP it already has, such as the
[Blender Lab MCP server](https://www.blender.org/lab/mcp-server/) or
[MCP for Blender](https://github.com/ahujasid/blender-mcp) (both have an
`execute_blender_code` tool). That keeps this server small and lets it work with either one.

## Install

You need [uv](https://docs.astral.sh/uv/). Run it straight from GitHub:

```sh
uvx --from git+https://github.com/Rhaluk/blender-assets-mcp blender-assets-mcp
```

Or install it once and get a `blender-assets-mcp` command:

```sh
uv tool install git+https://github.com/Rhaluk/blender-assets-mcp
```

### Claude Code

```sh
claude mcp add --scope user blender_assets -- uvx --from git+https://github.com/Rhaluk/blender-assets-mcp blender-assets-mcp
```

Add `-e SKETCHFAB_API_TOKEN=your-token` before `--` to enable Sketchfab downloads. See
[Sketchfab setup](#sketchfab-setup).

### Codex

In `~/.codex/config.toml`:

```toml
[mcp_servers.blender_assets]
command = "uvx"
args = ["--from", "git+https://github.com/Rhaluk/blender-assets-mcp", "blender-assets-mcp"]
env = { SKETCHFAB_API_TOKEN = "your-token" }  # optional, for Sketchfab downloads
tool_timeout_sec = 300  # large downloads can take longer than the 60 s default
```

### Other clients

Any MCP client that starts stdio servers works. Use the same command and arguments.

## Sketchfab setup

This fork adds [Sketchfab](https://sketchfab.com) as a fourth source, using the
[Sketchfab Data API v3](https://sketchfab.com/developers/data-api/v3) and
[Download API](https://sketchfab.com/developers/download-api). The original server searched
only Poly Haven, ambientCG and BlenderKit.

Searching Sketchfab needs no account. Downloading does, because Sketchfab only serves model
files to signed-in users.

### Get an API token

1. Sign in to [sketchfab.com](https://sketchfab.com), or create a free account.
2. Open [Settings > Password & API](https://sketchfab.com/settings/password).
3. Copy the value under **API Token**.

The token gives access to your Sketchfab account. Keep it out of the repository, chat logs
and screenshots. If it leaks, generate a new one on the same page.

### Give the token to the server

The server reads the token from the `SKETCHFAB_API_TOKEN` environment variable. Pass it in
the MCP client config, not in a file inside this repository.

Claude Code, running from GitHub:

```sh
claude mcp add --scope user blender_assets -e SKETCHFAB_API_TOKEN=your-token -- uvx --from git+https://github.com/Rhaluk/blender-assets-mcp blender-assets-mcp
```

Claude Code, running from a local clone:

```sh
claude mcp add --scope user blender_assets -e SKETCHFAB_API_TOKEN=your-token -- uv run --directory /path/to/blender-assets-mcp blender-assets-mcp
```

The value after `-e` must have the form `NAME=value`. A bare token fails. If the server is
already registered, run `claude mcp remove --scope user blender_assets` first. Restart the
client after you change the config.

### How it works

- `search_free_assets` calls `GET https://api.sketchfab.com/v3/search` with `type=models` and
  `downloadable=true`. Sketchfab results are always models; material and HDRI searches skip it.
- `download_free_asset` reads the model from `GET /v3/models/{uid}` and checks its license.
  It then calls `GET /v3/models/{uid}/download` with the header
  `Authorization: Token <your token>`. That returns a short-lived link to a `.glb` file or a
  zipped glTF, which goes into the cache.
- The returned `blender_python` imports the file with Blender's glTF importer into a new
  collection named after the model. Cameras and lights in the file are dropped.
- Sketchfab serves one file per model, so the `resolution` argument is ignored.

The server accepts these licenses: CC0, the six Creative Commons Attribution variants and
Free Standard. It refuses models under the paid store licenses (Standard and Editorial).

Each Sketchfab result carries `page` (the model page), `author`, `license` and
`commercial_use`. `commercial_use` is `false` for NonCommercial licenses. Downloads also
return an `attribution` line that names the model, its page, the author, the license and
Sketchfab, as the [Sketchfab API guidelines](https://sketchfab.com/developers/guidelines)
require. Put that line in your project's credits.

### Errors

- `Sketchfab downloads need an API token`: `SKETCHFAB_API_TOKEN` is not set for the server.
- `Sketchfab rejected the API token`: the token is wrong or was regenerated. Copy it again.
- `... uses the Standard license; only free licenses are allowed`: the model is a store
  purchase. Pick another result.

## Tools

`search_free_assets(query, kind="any", sources=None, limit=8)`
searches every source at once and returns id, name, kind, license, author and a thumbnail
URL for each hit. `kind` is `model`, `material`, `hdri` or `any`. `limit` applies per
source, up to 25. If one source fails, its error goes in `errors` and the others still return.
Sketchfab results also carry `page` and `commercial_use`, which is `false` for NonCommercial
licenses.

`download_free_asset(source, asset_id, resolution="1k")`
downloads into the cache and returns:

- `path`: the downloaded file (a folder for ambientCG materials)
- `license` and `attribution`: put the attribution in your project's credits
- `blender_python`: code to run inside Blender

What the code does depends on the asset kind:

- Models are appended from their `.blend` into a new collection named after the asset.
  Cameras and lights in the file are skipped. Sketchfab models are glTF files, imported
  with Blender's glTF importer into a new collection the same way.
- Materials are appended, or built as a Principled BSDF from ambientCG's texture maps.
  The agent still has to assign them to objects.
- HDRIs replace the scene's world with an environment texture.

Resolutions are `1k`, `2k` and `4k`. BlenderKit also accepts `0.5k` and `original`, and falls
back to the original file when an asset has no smaller version. Sketchfab serves one glTF
file per model and ignores the resolution.

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

Sketchfab models are mostly Creative Commons. Every license except CC0 requires credit:
use the returned `attribution`, which names the model, its Sketchfab page, the author and the
license. NonCommercial (`by-nc`) licenses forbid commercial use, and NoDerivs (`nd`) licenses
forbid sharing modified versions. Read the license on the model page before you ship. Models
are provided by [Sketchfab](https://sketchfab.com).

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

This project isn't affiliated with Poly Haven, ambientCG, BlenderKit, Sketchfab or the Blender Foundation.

## License

MIT
