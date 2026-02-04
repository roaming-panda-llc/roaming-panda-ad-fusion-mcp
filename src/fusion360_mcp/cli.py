"""CLI interface for Fusion 360 MCP server."""

import click
import httpx


@click.group()
@click.version_option(package_name="roaming-panda-ad-fusion-mcp")
def main():
    """Fusion 360 MCP Server - Control Fusion 360 via Model Context Protocol."""
    pass


@main.command()
@click.option("--port", default=8765, help="Port to listen on")
@click.option("--host", default="127.0.0.1", help="Host to bind to")
def serve(port: int, host: str):
    """Start the MCP server with Streamable HTTP transport."""
    import uvicorn
    from fusion360_mcp.server import create_app

    click.echo(f"Starting Fusion 360 MCP server on {host}:{port}")
    app = create_app()
    uvicorn.run(app, host=host, port=port)


@main.command()
def health():
    """Check if Fusion 360 add-in is running."""
    try:
        response = httpx.get("http://127.0.0.1:3001/health", timeout=5.0)
        data = response.json()
        click.echo(f"Fusion 360: {data.get('status', 'unknown')}")
        if data.get("fusion") == "connected":
            click.echo("Add-in is connected and ready")
    except httpx.ConnectError:
        click.echo("Fusion 360 add-in not running", err=True)
        raise SystemExit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise SystemExit(1)
