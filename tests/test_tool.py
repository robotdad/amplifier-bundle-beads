"""Tests for the beads tool module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestBeadsTool:
    """Tests for BeadsTool class."""

    @pytest.fixture
    def mock_coordinator(self):
        """Create a mock coordinator."""
        coordinator = MagicMock()
        coordinator.config = {"session_id": "test-session-123"}
        return coordinator

    def test_bd_not_installed_returns_helpful_error(self, mock_coordinator):
        """When bd is not installed, return installation instructions."""
        # Import here to avoid import errors when amplifier-core not installed
        with patch("shutil.which", return_value=None):
            from amplifier_bundle_beads.tool import BeadsTool

            tool = BeadsTool({}, mock_coordinator)
            assert tool._bd_available() is False

    def test_bd_installed_detected(self, mock_coordinator):
        """When bd is installed, detection succeeds."""
        with patch("shutil.which", return_value="/usr/local/bin/bd"):
            from amplifier_bundle_beads.tool import BeadsTool

            tool = BeadsTool({}, mock_coordinator)
            assert tool._bd_available() is True

    def test_session_id_from_coordinator(self, mock_coordinator):
        """Session ID is retrieved from coordinator config."""
        with patch("shutil.which", return_value="/usr/local/bin/bd"):
            from amplifier_bundle_beads.tool import BeadsTool

            tool = BeadsTool({}, mock_coordinator)
            assert tool.session_id == "test-session-123"

    def test_tool_definition_has_all_operations(self, mock_coordinator):
        """Tool definition includes all expected operations."""
        with patch("shutil.which", return_value="/usr/local/bin/bd"):
            from amplifier_bundle_beads.tool import BeadsTool

            tool = BeadsTool({}, mock_coordinator)
            definition = tool.get_definition()

            assert definition.name == "beads"
            operations = definition.input_schema["properties"]["operation"]["enum"]
            expected_ops = [
                "ready",
                "show",
                "create",
                "update",
                "close",
                "claim",
                "discover",
                "list",
                "sessions",
            ]
            assert operations == expected_ops

    @pytest.mark.asyncio
    async def test_execute_missing_operation_returns_error(self, mock_coordinator):
        """Execute without operation returns error."""
        with patch("shutil.which", return_value="/usr/local/bin/bd"):
            from amplifier_bundle_beads.tool import BeadsTool

            tool = BeadsTool({}, mock_coordinator)
            result = await tool.execute({})

            assert result.success is False
            assert "missing_operation" in result.output

    @pytest.mark.asyncio
    async def test_execute_unknown_operation_returns_error(self, mock_coordinator):
        """Execute with unknown operation returns error."""
        with patch("shutil.which", return_value="/usr/local/bin/bd"):
            from amplifier_bundle_beads.tool import BeadsTool

            tool = BeadsTool({}, mock_coordinator)
            result = await tool.execute({"operation": "invalid"})

            assert result.success is False
            assert "unknown_operation" in result.output


class TestRunBd:
    """Tests for _run_bd helper."""

    @pytest.fixture
    def mock_coordinator(self):
        coordinator = MagicMock()
        coordinator.config = {}
        return coordinator

    def test_run_bd_success(self, mock_coordinator):
        """Successful bd command returns output."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/bd"),
            patch("subprocess.run") as mock_run,
        ):
            from amplifier_bundle_beads.tool import BeadsTool

            mock_run.return_value = MagicMock(
                returncode=0,
                stdout='{"issues": []}',
                stderr="",
            )

            tool = BeadsTool({}, mock_coordinator)
            success, output = tool._run_bd(["ready"])

            assert success is True
            assert output == '{"issues": []}'
            mock_run.assert_called_once()

    def test_run_bd_failure(self, mock_coordinator):
        """Failed bd command returns error message."""
        with (
            patch("shutil.which", return_value="/usr/local/bin/bd"),
            patch("subprocess.run") as mock_run,
        ):
            from amplifier_bundle_beads.tool import BeadsTool

            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Error: not initialized",
            )

            tool = BeadsTool({}, mock_coordinator)
            success, output = tool._run_bd(["ready"])

            assert success is False
            assert "not initialized" in output
