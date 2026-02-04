"""Tests for __main__ module."""

import subprocess
import sys


def describe_main_module():
    def it_imports_main_from_cli():
        """Test that __main__ imports main correctly."""
        # This triggers the import in __main__.py
        from fusion360_mcp import __main__
        from fusion360_mcp.cli import main
        assert __main__.main is main

    def it_can_be_run_as_module():
        """Test that the module can be invoked via python -m."""
        # Just test that it shows help when called with --help
        result = subprocess.run(
            [sys.executable, "-m", "fusion360_mcp", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0
        assert "Fusion 360 MCP Server" in result.stdout
