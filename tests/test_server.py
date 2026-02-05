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
        httpx_mock.add_response(url="http://127.0.0.1:3001/health", json={"status": "ok"})
        result = await call_fusion("/health")
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def it_returns_error_on_connection_failure(httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"), url="http://127.0.0.1:3001/health"
        )
        result = await call_fusion("/health")
        assert result == {"error": "Fusion 360 not running or add-in not loaded"}

    @pytest.mark.asyncio
    async def it_returns_error_on_http_error(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/bad", status_code=500, text="Internal Server Error"
        )
        result = await call_fusion("/bad")
        assert "error" in result
        assert "500" in result["error"]


def describe_call_fusion_post():
    @pytest.mark.asyncio
    async def it_posts_data_successfully(httpx_mock):
        httpx_mock.add_response(url="http://127.0.0.1:3001/run_script", json={"result": "success"})
        result = await call_fusion_post("/run_script", {"code": "print(1)"})
        assert result == {"result": "success"}
        # Verify the POST body was sent correctly
        request = httpx_mock.get_request()
        import json

        assert json.loads(request.content) == {"code": "print(1)"}

    @pytest.mark.asyncio
    async def it_returns_error_on_connection_failure(httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"), url="http://127.0.0.1:3001/run_script"
        )
        result = await call_fusion_post("/run_script", {"code": "x"})
        assert result == {"error": "Fusion 360 not running or add-in not loaded"}

    @pytest.mark.asyncio
    async def it_returns_error_on_http_error(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/run_script", status_code=500, text="Internal Server Error"
        )
        result = await call_fusion_post("/run_script", {"code": "x"})
        assert "error" in result
        assert "500" in result["error"]

    @pytest.mark.asyncio
    async def it_returns_error_on_generic_exception(httpx_mock):
        httpx_mock.add_exception(
            ValueError("Unexpected error"), url="http://127.0.0.1:3001/run_script"
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
        httpx_mock.add_response(url="http://127.0.0.1:3001/health", json={"status": "ok"})
        result = await call_tool("fusion360_health", {})
        assert len(result) == 1
        assert "ok" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_document_info_tool(httpx_mock):
        httpx_mock.add_response(url="http://127.0.0.1:3001/document", json={"name": "test_design"})
        result = await call_tool("fusion360_document_info", {})
        assert len(result) == 1
        assert "test_design" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_components_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/components", json={"components": ["comp1"]}
        )
        result = await call_tool("fusion360_components", {})
        assert len(result) == 1
        assert "comp1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_sketches_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/sketches", json={"sketches": ["sketch1"]}
        )
        result = await call_tool("fusion360_sketches", {})
        assert len(result) == 1
        assert "sketch1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_sketch_details_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/sketches/Sketch1", json={"name": "Sketch1", "curves": 5}
        )
        result = await call_tool("fusion360_sketch_details", {"name": "Sketch1"})
        assert len(result) == 1
        assert "Sketch1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_bodies_tool(httpx_mock):
        httpx_mock.add_response(url="http://127.0.0.1:3001/bodies", json={"bodies": ["body1"]})
        result = await call_tool("fusion360_bodies", {})
        assert len(result) == 1
        assert "body1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_body_details_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/bodies/Body1", json={"name": "Body1", "volume": 100}
        )
        result = await call_tool("fusion360_body_details", {"name": "Body1"})
        assert len(result) == 1
        assert "Body1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_parameters_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/parameters", json={"parameters": ["param1"]}
        )
        result = await call_tool("fusion360_parameters", {})
        assert len(result) == 1
        assert "param1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_screenshot_tool(httpx_mock):
        import base64

        png_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        httpx_mock.add_response(url="http://127.0.0.1:3001/screenshot", content=png_data)
        result = await call_tool("fusion360_screenshot", {})
        assert len(result) == 1
        assert result[0].type == "image"
        assert result[0].mimeType == "image/png"
        assert result[0].data == base64.b64encode(png_data).decode("utf-8")

    @pytest.mark.asyncio
    async def it_handles_screenshot_connection_error(httpx_mock):
        httpx_mock.add_exception(
            httpx.ConnectError("Connection refused"), url="http://127.0.0.1:3001/screenshot"
        )
        result = await call_tool("fusion360_screenshot", {})
        assert len(result) == 1
        assert result[0].type == "text"
        assert "not running" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_screenshot_generic_error(httpx_mock):
        httpx_mock.add_exception(
            ValueError("Something went wrong"), url="http://127.0.0.1:3001/screenshot"
        )
        result = await call_tool("fusion360_screenshot", {})
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_run_script_tool(httpx_mock):
        httpx_mock.add_response(url="http://127.0.0.1:3001/run_script", json={"result": "success"})
        result = await call_tool("fusion360_run_script", {"code": "print(1)"})
        assert len(result) == 1
        assert "success" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_create_sketch_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/sketch/create", json={"sketch": "Sketch1"}
        )
        result = await call_tool(
            "fusion360_create_sketch", {"component_name": "Component1", "plane": "XY"}
        )
        assert len(result) == 1
        assert "Sketch1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_draw_circle_tool(httpx_mock):
        httpx_mock.add_response(url="http://127.0.0.1:3001/sketch/circle", json={"success": True})
        result = await call_tool(
            "fusion360_draw_circle",
            {"sketch_name": "Sketch1", "center_x": 0, "center_y": 0, "radius": 5},
        )
        assert len(result) == 1
        assert "success" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_extrude_tool(httpx_mock):
        httpx_mock.add_response(url="http://127.0.0.1:3001/extrude", json={"body": "Body1"})
        result = await call_tool(
            "fusion360_extrude",
            {"sketch_name": "Sketch1", "profile_index": 0, "distance": 10, "operation": "new"},
        )
        assert len(result) == 1
        assert "Body1" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_draw_rectangle_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/sketch/rectangle", json={"success": True}
        )
        result = await call_tool(
            "fusion360_draw_rectangle",
            {"sketch_name": "Sketch1", "x1": 0, "y1": 0, "x2": 10, "y2": 10},
        )
        assert len(result) == 1
        assert "success" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_activate_component_tool(httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/component/activate", json={"success": True}
        )
        result = await call_tool("fusion360_activate_component", {"name": "Component1"})
        assert len(result) == 1
        assert "success" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_set_visibility_tool(httpx_mock):
        httpx_mock.add_response(url="http://127.0.0.1:3001/visibility", json={"success": True})
        result = await call_tool(
            "fusion360_set_visibility", {"component_name": "Component1", "visible": False}
        )
        assert len(result) == 1
        assert "success" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_list_versions_tool(httpx_mock):
        httpx_mock.add_response(url="http://127.0.0.1:3001/versions", json={"versions": [1, 2, 3]})
        result = await call_tool("fusion360_list_versions", {})
        assert len(result) == 1
        assert "versions" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_restore_version_tool(httpx_mock):
        httpx_mock.add_response(url="http://127.0.0.1:3001/version/restore", json={"restored": 2})
        result = await call_tool("fusion360_restore_version", {"version_number": 2})
        assert len(result) == 1
        assert "restored" in result[0].text

    @pytest.mark.asyncio
    async def it_handles_unknown_tool():
        result = await call_tool("unknown_tool", {})
        assert len(result) == 1
        assert "Unknown tool" in result[0].text


def describe_timeout_configuration():
    """Tests to verify timeout values are correct (kills mutants on timeout=300.0)."""

    @pytest.mark.asyncio
    async def it_uses_300_second_timeout_for_get(mocker):
        """Verify call_fusion uses exactly 300 second timeout."""
        # Mock the AsyncClient class to capture the timeout parameter
        mock_client = mocker.AsyncMock()
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = mocker.Mock()
        mock_client.get.return_value = mock_response

        mock_async_client = mocker.patch("fusion360_mcp.server.httpx.AsyncClient")
        mock_async_client.return_value.__aenter__.return_value = mock_client
        mock_async_client.return_value.__aexit__.return_value = None

        result = await call_fusion("/health")

        # Verify the timeout was exactly 300.0
        mock_async_client.assert_called_once_with(timeout=300.0)
        assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def it_uses_300_second_timeout_for_post(mocker):
        """Verify call_fusion_post uses exactly 300 second timeout."""
        mock_client = mocker.AsyncMock()
        mock_response = mocker.Mock()
        mock_response.json.return_value = {"result": "ok"}
        mock_response.raise_for_status = mocker.Mock()
        mock_client.post.return_value = mock_response

        mock_async_client = mocker.patch("fusion360_mcp.server.httpx.AsyncClient")
        mock_async_client.return_value.__aenter__.return_value = mock_client
        mock_async_client.return_value.__aexit__.return_value = None

        result = await call_fusion_post("/run_script", {"code": "x=1"})

        # Verify the timeout was exactly 300.0
        mock_async_client.assert_called_once_with(timeout=300.0)
        assert result == {"result": "ok"}


def describe_session_manager_configuration():
    """Tests to verify StreamableHTTPSessionManager is configured correctly."""

    def it_uses_server_as_app(mocker):
        """Verify session manager is created with the server instance."""
        mock_manager_class = mocker.patch("fusion360_mcp.server.StreamableHTTPSessionManager")
        mock_manager = mocker.Mock()
        mock_manager.handle_request = mocker.Mock()
        mock_manager.run = mocker.Mock(return_value=mocker.AsyncMock())
        mock_manager_class.return_value = mock_manager

        create_app()

        # Verify server is passed as app parameter
        call_kwargs = mock_manager_class.call_args.kwargs
        assert call_kwargs["app"] is server

    def it_uses_none_for_event_store(mocker):
        """Verify event_store is explicitly set to None."""
        mock_manager_class = mocker.patch("fusion360_mcp.server.StreamableHTTPSessionManager")
        mock_manager = mocker.Mock()
        mock_manager.handle_request = mocker.Mock()
        mock_manager.run = mocker.Mock(return_value=mocker.AsyncMock())
        mock_manager_class.return_value = mock_manager

        create_app()

        call_kwargs = mock_manager_class.call_args.kwargs
        assert call_kwargs["event_store"] is None

    def it_uses_false_for_json_response(mocker):
        """Verify json_response is set to False."""
        mock_manager_class = mocker.patch("fusion360_mcp.server.StreamableHTTPSessionManager")
        mock_manager = mocker.Mock()
        mock_manager.handle_request = mocker.Mock()
        mock_manager.run = mocker.Mock(return_value=mocker.AsyncMock())
        mock_manager_class.return_value = mock_manager

        create_app()

        call_kwargs = mock_manager_class.call_args.kwargs
        assert call_kwargs["json_response"] is False

    def it_uses_true_for_stateless(mocker):
        """Verify stateless is set to True."""
        mock_manager_class = mocker.patch("fusion360_mcp.server.StreamableHTTPSessionManager")
        mock_manager = mocker.Mock()
        mock_manager.handle_request = mocker.Mock()
        mock_manager.run = mocker.Mock(return_value=mocker.AsyncMock())
        mock_manager_class.return_value = mock_manager

        create_app()

        call_kwargs = mock_manager_class.call_args.kwargs
        assert call_kwargs["stateless"] is True


def describe_starlette_app_configuration():
    """Tests to verify Starlette app is configured correctly."""

    def it_mounts_mcp_at_correct_path(mocker):
        """Verify MCP route is mounted at /mcp."""
        mock_manager_class = mocker.patch("fusion360_mcp.server.StreamableHTTPSessionManager")
        mock_manager = mocker.Mock()
        mock_manager.handle_request = mocker.Mock()
        mock_manager.run = mocker.Mock(return_value=mocker.AsyncMock())
        mock_manager_class.return_value = mock_manager

        app = create_app()

        # Verify /mcp route exists
        route_paths = [str(r.path) for r in app.routes]
        assert "/mcp" in route_paths

    def it_sets_lifespan_handler(mocker):
        """Verify lifespan handler is set (not None)."""
        mock_manager_class = mocker.patch("fusion360_mcp.server.StreamableHTTPSessionManager")
        mock_manager = mocker.Mock()
        mock_manager.handle_request = mocker.Mock()
        mock_manager.run = mocker.Mock(return_value=mocker.AsyncMock())
        mock_manager_class.return_value = mock_manager

        # Mock Starlette to capture the lifespan parameter
        mock_starlette = mocker.patch("fusion360_mcp.server.Starlette")

        create_app()

        # Verify lifespan parameter was passed (not None)
        call_kwargs = mock_starlette.call_args.kwargs
        assert "lifespan" in call_kwargs
        assert call_kwargs["lifespan"] is not None


def describe_main():
    @pytest.mark.asyncio
    async def it_can_be_imported():
        # main() runs stdio_server which we can't test directly
        # Verify it exists and is callable
        # Note: mutmut 3.x wraps async functions in trampolines, so we check callable
        assert callable(main)

    @pytest.mark.asyncio
    async def it_runs_server_with_stdio_streams(mocker):
        """Verify main() correctly wires stdio_server streams to server.run()."""
        # Mock the streams returned by stdio_server
        mock_read_stream = mocker.Mock(name="read_stream")
        mock_write_stream = mocker.Mock(name="write_stream")

        # Mock stdio_server as async context manager
        mock_stdio = mocker.patch("fusion360_mcp.server.stdio_server")
        mock_stdio.return_value.__aenter__ = mocker.AsyncMock(
            return_value=(mock_read_stream, mock_write_stream)
        )
        mock_stdio.return_value.__aexit__ = mocker.AsyncMock(return_value=None)

        # Mock server.run and create_initialization_options
        mock_run = mocker.patch.object(server, "run", new_callable=mocker.AsyncMock)
        mock_init_opts = mocker.Mock(name="init_options")
        mocker.patch.object(server, "create_initialization_options", return_value=mock_init_opts)

        await main()

        # Verify stdio_server was called
        mock_stdio.assert_called_once()

        # Verify server.run was called with the correct streams
        mock_run.assert_called_once_with(mock_read_stream, mock_write_stream, mock_init_opts)
