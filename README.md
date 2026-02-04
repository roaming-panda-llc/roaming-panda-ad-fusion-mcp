# Fusion 360 MCP Server

MCP (Model Context Protocol) server for controlling Autodesk Fusion 360. Enables AI assistants like Claude to interact with Fusion 360 for parametric CAD modeling, script execution, and design automation.

## Features

- **Streamable HTTP Transport**: Long-running operations (>30s) complete without timeout
- **Full Fusion 360 API Access**: Documents, components, sketches, bodies, parameters
- **Script Execution**: Run arbitrary Python code in Fusion 360 context
- **Screenshot Capture**: Get viewport images for visual feedback
- **Version Management**: List and restore document versions

## Installation

### Quick Start (Recommended)

```bash
# Run directly without installing
uvx roaming-panda-ad-fusion-mcp serve
```

### Install from PyPI

```bash
pip install roaming-panda-ad-fusion-mcp
roaming-panda-ad-fusion-mcp serve
```

### Install from Source

```bash
git clone https://github.com/roaming-panda-llc/roaming-panda-ad-fusion-mcp.git
cd roaming-panda-ad-fusion-mcp
pip install -e .
```

## Fusion 360 Add-in Setup

The MCP server communicates with Fusion 360 via a REST API add-in that must be installed:

1. Copy the `addin/` folder to your Fusion 360 add-ins directory:
   - **macOS**: `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/`
   - **Windows**: `%APPDATA%\Autodesk\Autodesk Fusion 360\API\AddIns\`

2. In Fusion 360, go to **Tools > Add-Ins** and enable "FusionMCP"

3. Verify the add-in is running:
   ```bash
   roaming-panda-ad-fusion-mcp health
   ```

## Usage

### Start the MCP Server

```bash
# Default: http://127.0.0.1:8765/mcp
roaming-panda-ad-fusion-mcp serve

# Custom port
roaming-panda-ad-fusion-mcp serve --port 9000
```

### Configure Claude Code

Add to `~/.claude.json`:

```json
{
  "mcpServers": {
    "fusion360": {
      "url": "http://127.0.0.1:8765/mcp"
    }
  }
}
```

### Available Tools

| Tool | Description |
|------|-------------|
| `fusion360_health` | Check if Fusion 360 add-in is running |
| `fusion360_document_info` | Get current document information |
| `fusion360_components` | Get component tree |
| `fusion360_sketches` | List all sketches |
| `fusion360_sketch_details` | Get sketch details by name |
| `fusion360_bodies` | List all bodies |
| `fusion360_body_details` | Get body details by name |
| `fusion360_parameters` | Get user parameters |
| `fusion360_screenshot` | Capture viewport image |
| `fusion360_run_script` | Execute Python code in Fusion 360 |
| `fusion360_create_sketch` | Create a new sketch |
| `fusion360_draw_circle` | Draw a circle in a sketch |
| `fusion360_draw_rectangle` | Draw a rectangle in a sketch |
| `fusion360_extrude` | Extrude a sketch profile |
| `fusion360_activate_component` | Activate a component |
| `fusion360_set_visibility` | Show/hide a component |
| `fusion360_list_versions` | List document versions |
| `fusion360_restore_version` | Restore a document version |

## Development

### Setup

```bash
git clone https://github.com/roaming-panda-llc/roaming-panda-ad-fusion-mcp.git
cd roaming-panda-ad-fusion-mcp
uv sync --all-extras
```

### Run Tests

```bash
uv run pytest --cov --cov-report=term-missing
```

### Run Mutation Tests

```bash
uv run mutmut run
uv run mutmut results
```

### Lint

```bash
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Architecture

```
┌─────────────┐     HTTP POST     ┌──────────────┐     REST API     ┌─────────────┐
│ Claude Code │ ───────────────▶ │  MCP Server  │ ───────────────▶ │  Fusion 360 │
│             │                   │  (Starlette) │                   │   Add-in    │
│             │ ◀─────────────── │              │ ◀─────────────── │             │
└─────────────┘    SSE events    └──────────────┘    JSON response  └─────────────┘
```

## License

MIT License - see LICENSE file for details.
