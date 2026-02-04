"""Test fixtures for Fusion 360 MCP tests."""

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_fusion_health(httpx_mock):
    """Mock Fusion 360 health endpoint."""
    httpx_mock.add_response(
        url="http://127.0.0.1:3001/health", json={"status": "ok", "fusion": "connected"}
    )
    return httpx_mock


@pytest.fixture
def mock_fusion_document(httpx_mock):
    """Mock Fusion 360 document endpoint."""
    httpx_mock.add_response(
        url="http://127.0.0.1:3001/document", json={"name": "test_design", "is_saved": True}
    )
    return httpx_mock


@pytest.fixture
def mock_fusion_unavailable(httpx_mock):
    """Mock Fusion 360 connection failure."""
    import httpx

    httpx_mock.add_exception(
        httpx.ConnectError("Connection refused"), url="http://127.0.0.1:3001/health"
    )
    return httpx_mock
