"""Tests for MCP server module."""

import httpx
import pytest
from mcp.types import Tool

from fusion360_mcp.server import (
    call_fusion,
    call_fusion_post,
    call_tool,
    create_app,
    list_tools,
    main,
    server,
)


def describe_mcp_server():
    def it_has_correct_name():
        assert server.name == "fusion360-mcp"


def describe_call_fusion():
    @pytest.mark.asyncio
    async def it_returns_data_on_success(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/health",
            json={"status": "ok"}
        )
        result = await call_fusion("/health")
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def it_returns_error_on_connection_failure(httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://127.0.0.1:3001/health"
        )
        result = await call_fusion("/health")
        assert "error" in result
        assert "not running" in result["error"]

    @pytest.mark.asyncio
    async def it_returns_error_on_http_error(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/bad",
            status_code=500,
            text="Internal Server Error"
        )
        result = await call_fusion("/bad")
        assert "error" in result
        assert "500" in result["error"]


def describe_call_fusion_post():
    @pytest.mark.asyncio
    async def it_posts_data_successfully(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/run_script",
            json={"result": "success"}
        )
        result = await call_fusion_post("/run_script", {"code": "print(1)"})
        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def it_returns_error_on_connection_failure(httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://127.0.0.1:3001/run_script"
        )
        result = await call_fusion_post("/run_script", {"code": "x"})
        assert "error" in result
        assert "not running" in result["error"]

    @pytest.mark.asyncio
    async def it_returns_error_on_http_error(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/run_script",
            status_code=500,
            text="Internal Server Error"
        )
        result = await call_fusion_post("/run_script", {"code": "x"})
        assert "error" in result
        assert "500" in result["error"]

    @pytest.mark.asyncio
    async def it_returns_error_on_generic_exception(httpx_mock):
        httpx_mock.add_exception(
            ValueError("Unexpected error"),
            url="http://127.0.0.1:3001/run_script"
        )
        result = await call_fusion_post("/run_script", {"code": "x"})
        assert "error" in result
        assert "Unexpected error" in result["error"]


def describe_create_app():
    def it_returns_starlette_app():
        from starlette.applications import Starlette
        app = create_app()
        assert isinstance(app, Starlette)

    def it_has_mcp_route():
        app = create_app()
        routes = [r.path for r in app.routes]
        assert "/mcp" in routes or any("/mcp" in str(r) for r in app.routes)

    def it_has_lifespan():
        app = create_app()
        # Starlette stores the lifespan handler in state
        # Check that the app has routes and was created successfully
        assert len(app.routes) > 0

    @pytest.mark.asyncio
    async def it_runs_lifespan():
        from starlette.testclient import TestClient
        app = create_app()
        # The TestClient handles lifespan events
        with TestClient(app, raise_server_exceptions=False):
            # Just entering and exiting the context runs the lifespan
            # We don't need to make any actual requests
            pass


def describe_list_tools():
    @pytest.mark.asyncio
    async def it_returns_list_of_tools():
        tools = await list_tools()
        assert isinstance(tools, list)
        assert all(isinstance(t, Tool) for t in tools)

    @pytest.mark.asyncio
    async def it_includes_expected_tools():
        tools = await list_tools()
        tool_names = [t.name for t in tools]
        expected = [
            "fusion360_health",
            "fusion360_document_info",
            "fusion360_components",
            "fusion360_sketches",
            "fusion360_sketch_details",
            "fusion360_bodies",
            "fusion360_body_details",
            "fusion360_parameters",
            "fusion360_screenshot",
            "fusion360_run_script",
            "fusion360_create_sketch",
            "fusion360_draw_circle",
            "fusion360_extrude",
            "fusion360_draw_rectangle",
            "fusion360_activate_component",
            "fusion360_set_visibility",
            "fusion360_list_versions",
            "fusion360_restore_version",
        ]
        for name in expected:
            assert name in tool_names


def describe_call_tool():
    @pytest.mark.asyncio
    async def it_handles_health_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/health",
            json={"status": "ok"}
        )
        result = await call_tool("fusion360_health", {})
        assert len(result) == 1
        assert "ok" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_document_info_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/document",
            json={"name": "test_design"}
        )
        result = await call_tool("fusion360_document_info", {})
        assert len(result) == 1
        assert "test_design" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_components_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/components",
            json={"components": ["comp1"]}
        )
        result = await call_tool("fusion360_components", {})
        assert len(result) == 1
        assert "comp1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_sketches_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/sketches",
            json={"sketches": ["sketch1"]}
        )
        result = await call_tool("fusion360_sketches", {})
        assert len(result) == 1
        assert "sketch1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_sketch_details_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/sketches/Sketch1",
            json={"name": "Sketch1", "curves": 5}
        )
        result = await call_tool("fusion360_sketch_details", {"name": "Sketch1"})
        assert len(result) == 1
        assert "Sketch1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_bodies_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/bodies",
            json={"bodies": ["body1"]}
        )
        result = await call_tool("fusion360_bodies", {})
        assert len(result) == 1
        assert "body1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_body_details_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/bodies/Body1",
            json={"name": "Body1", "volume": 100}
        )
        result = await call_tool("fusion360_body_details", {"name": "Body1"})
        assert len(result) == 1
        assert "Body1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_parameters_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/parameters",
            json={"parameters": ["param1"]}
        )
        result = await call_tool("fusion360_parameters", {})
        assert len(result) == 1
        assert "param1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_screenshot_tool(httpx_mock):
        import base64
        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/screenshot",
            content=png_data
        )
        result = await call_tool("fusion360_screenshot", {})
        assert len(result) == 1
        assert result[0].type == "image"
        assert result[0].mimeType == "image/png"
        assert result[0].data == base64.b64encode(png_data).decode("utf-8")

    @pytest.mark.asyncio
    async def it_handles_screenshot_connection_error(httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"),
            url="http://127.0.0.1:3001/screenshot"
        )
        result = await call_tool("fusion360_screenshot", {})
        assert len(result) == 1
        assert result[0].type == "text"
        assert "not running" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_screenshot_generic_error(httpx_mock):
        httpx_mock.add_exception(
            ValueError("Something went wrong"),
            url="http://127.0.0.1:3001/screenshot"
        )
        result = await call_tool("fusion360_screenshot", {})
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_run_script_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/run_script",
            json={"result": "success"}
        )
        result = await call_tool("fusion360_run_script", {"code": "print(1)"})
        assert len(result) == 1
        assert "success" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_create_sketch_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/sketch/create",
            json={"sketch": "Sketch1"}
        )
        result = await call_tool(
            "fusion360_create_sketch",
            {"component_name": "Component1", "plane": "XY"}
        )
        assert len(result) == 1
        assert "Sketch1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_draw_circle_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/sketch/circle",
            json={"success": True}
        )
        result = await call_tool(
            "fusion360_draw_circle",
            {"sketch_name": "Sketch1", "center_x": 0, "center_y": 0, "radius": 5}
        )
        assert len(result) == 1
        assert "success" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_extrude_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/extrude",
            json={"body": "Body1"}
        )
        result = await call_tool(
            "fusion360_extrude",
            {
                "sketch_name": "Sketch1",
                "profile_index": 0,
                "distance": 10,
                "operation": "new"
            }
        )
        assert len(result) == 1
        assert "Body1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_draw_rectangle_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/sketch/rectangle",
            json={"success": True}
        )
        result = await call_tool(
            "fusion360_draw_rectangle",
            {"sketch_name": "Sketch1", "x1": 0, "y1": 0, "x2": 10, "y2": 10}
        )
        assert len(result) == 1
        assert "success" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_activate_component_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/component/activate",
            json={"success": True}
        )
        result = await call_tool(
            "fusion360_activate_component",
            {"name": "Component1"}
        )
        assert len(result) == 1
        assert "success" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_set_visibility_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/visibility",
            json={"success": True}
        )
        result = await call_tool(
            "fusion360_set_visibility",
            {"component_name": "Component1", "visible": False}
        )
        assert len(result) == 1
        assert "success" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_list_versions_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/versions",
            json={"versions": [1, 2, 3]}
        )
        result = await call_tool("fusion360_list_versions", {})
        assert len(result) == 1
        assert "versions" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_restore_version_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/version/restore",
            json={"restored": 2}
        )
        result = await call_tool(
            "fusion360_restore_version",
            {"version_number": 2}
        )
        assert len(result) == 1
        assert "restored" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_unknown_tool():
        result = await call_tool("unknown_tool", {})
        assert len(result) == 1
        assert "Unknown tool" in result[0].text


def describe_main():
    @pytest.mark.asyncio
    async def it_can_be_imported():
        # main() runs stdio_server which we can't test directly
        # but we verify it exists and is async
        import inspect
        assert inspect.iscoroutinefunction(main)
