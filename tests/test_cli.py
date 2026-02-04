"""Tests for CLI module."""

import sys
from unittest.mock import MagicMock, patch

from fusion360_mcp.cli import main


def describe_main_group():
    def it_shows_version(cli_runner):
        result = cli_runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


def describe_health_command():
    def it_reports_fusion_connected(cli_runner, mock_fusion_health):
        result = cli_runner.invoke(main, ["health"])
        assert result.exit_code == 0
        assert "ok" in result.output
        assert "connected and ready" in result.output

    def it_reports_status_without_connected(cli_runner, httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/health",
            json={"status": "ok", "fusion": "disconnected"}
        )
        result = cli_runner.invoke(main, ["health"])
        assert result.exit_code == 0
        assert "ok" in result.output
        assert "connected and ready" not in result.output

    def it_reports_fusion_unavailable(cli_runner, mock_fusion_unavailable):
        result = cli_runner.invoke(main, ["health"])
        assert result.exit_code == 1
        assert "not running" in result.output

    def it_reports_generic_error(cli_runner, httpx_mock):
        httpx_mock.add_response(
            url="http://127.0.0.1:3001/health",
            status_code=500,
            text="Server Error"
        )
        result = cli_runner.invoke(main, ["health"])
        assert result.exit_code == 1
        assert "Error" in result.output


def describe_serve_command():
    def it_has_default_port(cli_runner):
        # We can't actually start the server in tests, but we can check help
        result = cli_runner.invoke(main, ["serve", "--help"])
        assert result.exit_code == 0
        assert "8765" in result.output
        assert "--port" in result.output

    def it_has_default_host(cli_runner):
        result = cli_runner.invoke(main, ["serve", "--help"])
        assert "127.0.0.1" in result.output
        assert "--host" in result.output

    def it_starts_server_with_uvicorn(cli_runner):
        mock_uvicorn = MagicMock()
        mock_create_app = MagicMock()
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        with patch.dict(sys.modules, {"uvicorn": mock_uvicorn}):
            with patch("fusion360_mcp.server.create_app", mock_create_app):
                result = cli_runner.invoke(main, ["serve"])

        assert result.exit_code == 0
        mock_uvicorn.run.assert_called_once_with(
            mock_app, host="127.0.0.1", port=8765
        )

    def it_starts_server_with_custom_port_and_host(cli_runner):
        mock_uvicorn = MagicMock()
        mock_create_app = MagicMock()
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        with patch.dict(sys.modules, {"uvicorn": mock_uvicorn}):
            with patch("fusion360_mcp.server.create_app", mock_create_app):
                result = cli_runner.invoke(
                    main, ["serve", "--port", "9000", "--host", "0.0.0.0"]
                )

        assert result.exit_code == 0
        mock_uvicorn.run.assert_called_once_with(
            mock_app, host="0.0.0.0", port=9000
        )
