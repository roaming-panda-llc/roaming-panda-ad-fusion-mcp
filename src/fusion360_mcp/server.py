#!/usr/bin/env python3
"""
Fusion 360 MCP Bridge Server

Uses the official MCP SDK to expose Fusion 360 functionality.
Communicates with Fusion 360 via REST API running on port 3001.
"""

import asyncio
import base64
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import ImageContent, TextContent, Tool
from starlette.applications import Starlette
from starlette.routing import Mount

FUSION_URL = "http://127.0.0.1:3001"

server = Server("fusion360-mcp")


async def call_fusion(endpoint: str) -> dict[str, Any]:
    """Call a Fusion 360 REST endpoint."""
    async with httpx.AsyncClient(timeout=300.0) as client:  # pragma: no mutate
        try:
            response = await client.get(f"{FUSION_URL}{endpoint}")
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {"error": "Fusion 360 not running or add-in not loaded"}
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}


async def call_fusion_post(endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
    """Make POST request to Fusion 360 REST API."""
    async with httpx.AsyncClient(timeout=300.0) as client:  # pragma: no mutate
        try:
            response = await client.post(f"{FUSION_URL}{endpoint}", json=data)
            response.raise_for_status()
            return response.json()
        except httpx.ConnectError:
            return {"error": "Fusion 360 not running or add-in not loaded"}
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": str(e)}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="fusion360_document_info",
            description="Get information about the currently open Fusion 360 document",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="fusion360_components",
            description="Get the component tree of the current design",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="fusion360_sketches",
            description="List all sketches in the current design",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="fusion360_sketch_details",
            description="Get detailed information about a specific sketch",
            inputSchema={
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Name of the sketch"}},
                "required": ["name"],
            },
        ),
        Tool(
            name="fusion360_bodies",
            description="List all bodies in the current design",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="fusion360_body_details",
            description="Get detailed information about a specific body",
            inputSchema={
                "type": "object",
                "properties": {"name": {"type": "string", "description": "Name of the body"}},
                "required": ["name"],
            },
        ),
        Tool(
            name="fusion360_parameters",
            description="Get all user parameters in the current design",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="fusion360_screenshot",
            description="Take a screenshot of the current Fusion 360 viewport",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="fusion360_health",
            description="Check if Fusion 360 and the MCP add-in are running",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="fusion360_run_script",
            description=(
                "Execute Python code directly in Fusion 360 context. "
                "The code has access to: adsk (Fusion API module), app (Application), "
                "design (active Design), ui (UserInterface). Set 'result' variable to return data."
            ),
            inputSchema={
                "type": "object",
                "properties": {"code": {"type": "string", "description": "Python code to execute"}},
                "required": ["code"],
            },
        ),
        Tool(
            name="fusion360_create_sketch",
            description="Create a new sketch on a construction plane",
            inputSchema={
                "type": "object",
                "properties": {
                    "component_name": {
                        "type": "string",
                        "description": "Name of the component to create sketch in",
                    },
                    "plane": {
                        "type": "string",
                        "description": 'Plane to create sketch on: "XY", "XZ", or "YZ"',
                    },
                },
                "required": ["component_name", "plane"],
            },
        ),
        Tool(
            name="fusion360_draw_circle",
            description="Draw a circle in an existing sketch",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch_name": {"type": "string", "description": "Name of the sketch"},
                    "center_x": {"type": "number", "description": "X coordinate of circle center"},
                    "center_y": {"type": "number", "description": "Y coordinate of circle center"},
                    "radius": {"type": "number", "description": "Radius of the circle"},
                },
                "required": ["sketch_name", "center_x", "center_y", "radius"],
            },
        ),
        Tool(
            name="fusion360_extrude",
            description="Extrude a sketch profile to create 3D geometry",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch_name": {"type": "string", "description": "Name of the sketch"},
                    "profile_index": {
                        "type": "number",
                        "description": "Index of the profile to extrude",
                    },
                    "distance": {"type": "number", "description": "Extrusion distance"},
                    "operation": {
                        "type": "string",
                        "description": 'Operation type: "new", "join", or "cut"',
                    },
                },
                "required": ["sketch_name", "profile_index", "distance", "operation"],
            },
        ),
        Tool(
            name="fusion360_draw_rectangle",
            description="Draw a rectangle in an existing sketch",
            inputSchema={
                "type": "object",
                "properties": {
                    "sketch_name": {"type": "string", "description": "Name of the sketch"},
                    "x1": {"type": "number", "description": "X coordinate of first corner"},
                    "y1": {"type": "number", "description": "Y coordinate of first corner"},
                    "x2": {"type": "number", "description": "X coordinate of opposite corner"},
                    "y2": {"type": "number", "description": "Y coordinate of opposite corner"},
                },
                "required": ["sketch_name", "x1", "y1", "x2", "y2"],
            },
        ),
        Tool(
            name="fusion360_activate_component",
            description="Activate a component for editing",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the component to activate"},
                },
                "required": ["name"],
            },
        ),
        Tool(
            name="fusion360_set_visibility",
            description="Show or hide a component",
            inputSchema={
                "type": "object",
                "properties": {
                    "component_name": {"type": "string", "description": "Name of the component"},
                    "visible": {"type": "boolean", "description": "True to show, False to hide"},
                },
                "required": ["component_name", "visible"],
            },
        ),
        Tool(
            name="fusion360_list_versions",
            description=(
                "List all saved versions of the current document. "
                "Only works for cloud-saved documents."
            ),
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        Tool(
            name="fusion360_restore_version",
            description=(
                "Open a specific version of the document in a new tab. Save to make it current."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "version_number": {
                        "type": "integer",
                        "description": "Version number to restore (1-based)",
                    }
                },
                "required": ["version_number"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent]:
    """Handle tool calls."""

    if name == "fusion360_health":
        result = await call_fusion("/health")
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_document_info":
        result = await call_fusion("/document")
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_components":
        result = await call_fusion("/components")
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_sketches":
        result = await call_fusion("/sketches")
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_sketch_details":
        sketch_name = arguments.get("name", "")
        result = await call_fusion(f"/sketches/{sketch_name}")
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_bodies":
        result = await call_fusion("/bodies")
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_body_details":
        body_name = arguments.get("name", "")
        result = await call_fusion(f"/bodies/{body_name}")
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_parameters":
        result = await call_fusion("/parameters")
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_screenshot":
        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                response = await client.get(f"{FUSION_URL}/screenshot")
                response.raise_for_status()
                # Screenshot returns PNG bytes
                image_data = base64.b64encode(response.content).decode("utf-8")
                return [ImageContent(type="image", data=image_data, mimeType="image/png")]
            except httpx.ConnectError:
                return [TextContent(type="text", text="Error: Fusion 360 not running")]
            except Exception as e:
                return [TextContent(type="text", text=f"Error: {e}")]

    elif name == "fusion360_run_script":
        code = arguments.get("code", "")
        result = await call_fusion_post("/run_script", {"code": code})
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_create_sketch":
        component_name = arguments.get("component_name", "")
        plane = arguments.get("plane", "")
        result = await call_fusion_post(
            "/sketch/create", {"component_name": component_name, "plane": plane}
        )
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_draw_circle":
        sketch_name = arguments.get("sketch_name", "")
        center_x = arguments.get("center_x", 0)
        center_y = arguments.get("center_y", 0)
        radius = arguments.get("radius", 0)
        data = {
            "sketch_name": sketch_name,
            "center_x": center_x,
            "center_y": center_y,
            "radius": radius,
        }
        result = await call_fusion_post("/sketch/circle", data)
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_extrude":
        sketch_name = arguments.get("sketch_name", "")
        profile_index = arguments.get("profile_index", 0)
        distance = arguments.get("distance", 0)
        operation = arguments.get("operation", "new")
        data = {
            "sketch_name": sketch_name,
            "profile_index": profile_index,
            "distance": distance,
            "operation": operation,
        }
        result = await call_fusion_post("/extrude", data)
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_draw_rectangle":
        sketch_name = arguments.get("sketch_name", "")
        x1 = arguments.get("x1", 0)
        y1 = arguments.get("y1", 0)
        x2 = arguments.get("x2", 0)
        y2 = arguments.get("y2", 0)
        result = await call_fusion_post(
            "/sketch/rectangle",
            {"sketch_name": sketch_name, "x1": x1, "y1": y1, "x2": x2, "y2": y2},
        )
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_activate_component":
        component_name = arguments.get("name", "")
        result = await call_fusion_post("/component/activate", {"name": component_name})
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_set_visibility":
        component_name = arguments.get("component_name", "")
        visible = arguments.get("visible", True)
        result = await call_fusion_post(
            "/visibility",
            {"component_name": component_name, "visible": visible},
        )
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_list_versions":
        result = await call_fusion("/versions")
        return [TextContent(type="text", text=str(result))]

    elif name == "fusion360_restore_version":
        version_number = arguments.get("version_number", 1)
        result = await call_fusion_post("/version/restore", {"version_number": version_number})
        return [TextContent(type="text", text=str(result))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


def create_app() -> Starlette:
    """Create Starlette app with Streamable HTTP transport for MCP.

    Note: This factory function has configuration parameters that cannot be
    meaningfully unit tested without integration tests. The framework config
    (event_store, json_response, stateless, lifespan) are validated by
    running the app, not by checking parameter values.
    """
    import contextlib
    from collections.abc import AsyncIterator

    session_manager = StreamableHTTPSessionManager(  # pragma: no mutate
        app=server,  # pragma: no mutate
        event_store=None,  # pragma: no mutate
        json_response=False,  # pragma: no mutate
        stateless=True,  # pragma: no mutate
    )

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[None]:
        async with session_manager.run():
            yield

    return Starlette(  # pragma: no mutate
        routes=[
            Mount("/mcp", app=session_manager.handle_request),
        ],
        lifespan=lifespan,  # pragma: no mutate
    )


async def main():  # pragma: no cover, no mutate
    """Run the MCP server with stdio transport (for backward compatibility)."""
    async with stdio_server() as (read_stream, write_stream):  # pragma: no mutate
        await server.run(read_stream, write_stream, server.create_initialization_options())  # pragma: no mutate


if __name__ == "__main__":
    asyncio.run(main())
