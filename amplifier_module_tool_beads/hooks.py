"""Beads hooks - session lifecycle integration for ready work injection."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any

from amplifier_core import HookResult

logger = logging.getLogger(__name__)


def _bd_available() -> bool:
    """Check if bd CLI is available."""
    return shutil.which("bd") is not None


def _run_bd(args: list[str], json_output: bool = True) -> tuple[bool, str]:
    """Run a bd command and return (success, output)."""
    cmd = ["bd"] + args
    if json_output:
        cmd.append("--json")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


class BeadsReadyHook:
    """Hook that injects ready beads tasks into context on session start.

    This gives agents immediate visibility into available work without
    requiring them to explicitly call the beads tool first.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize hook with configuration.

        Args:
            config: Hook configuration with options:
                - enabled: Whether to inject ready tasks (default: True)
                - max_issues: Maximum issues to show (default: 10)
                - priority: Hook priority (default: 50)
        """
        self.enabled = config.get("enabled", True)
        self.max_issues = config.get("max_issues", 10)
        self.priority = config.get("priority", 50)

        logger.debug(
            f"Initialized BeadsReadyHook: enabled={self.enabled}, max_issues={self.max_issues}"
        )

    async def on_session_start(self, event: str, data: dict[str, Any]) -> HookResult:
        """Inject ready tasks into context on session start.

        Event: session:start

        Args:
            event: Event name (should be "session:start")
            data: Event data dictionary

        Returns:
            HookResult with context_injection if there are ready tasks
        """
        if not self.enabled:
            return HookResult(action="continue")

        if not _bd_available():
            # Silently skip if bd not installed
            logger.debug("bd CLI not available, skipping ready injection")
            return HookResult(action="continue")

        # Check for ready tasks
        success, output = _run_bd(["ready"])
        if not success:
            # Not initialized or error - skip silently
            logger.debug(f"bd ready failed: {output}")
            return HookResult(action="continue")

        try:
            ready_data = json.loads(output)
            issues = ready_data.get("issues", [])

            if not issues:
                # No ready work - don't inject anything
                return HookResult(action="continue")

            context = self._format_ready_work(issues)
            return HookResult(
                action="inject_context",
                context_injection=context,
                context_injection_role="user",
                ephemeral=True,
                suppress_output=True,
            )

        except json.JSONDecodeError:
            logger.debug("Failed to parse bd ready output as JSON")
            return HookResult(action="continue")

    def _format_ready_work(self, issues: list[dict[str, Any]]) -> str:
        """Format ready work for context injection.

        Args:
            issues: List of ready issues from bd ready

        Returns:
            Formatted markdown string wrapped in system-reminder tags
        """
        lines = ["Ready work from beads (tasks with no open blockers):", ""]

        for issue in issues[: self.max_issues]:
            issue_id = issue.get("id", "?")
            title = issue.get("title", "Untitled")
            priority = issue.get("priority", "")
            priority_str = f" [{priority}]" if priority else ""
            lines.append(f"- **{issue_id}**: {title}{priority_str}")

        if len(issues) > self.max_issues:
            lines.append(f"- ... and {len(issues) - self.max_issues} more")

        lines.append("")
        lines.append("Use `beads(operation='claim', issue_id='...')` to claim a task.")

        content = "\n".join(lines)

        # Add behavioral note
        behavioral_note = (
            "\n\nThis context is for your reference. Consider these tasks when "
            "the user's request aligns with available work."
        )

        # Wrap in system-reminder tag with source attribution
        return f'<system-reminder source="hooks-beads-ready">\n{content}{behavioral_note}\n</system-reminder>'


class BeadsSessionEndHook:
    """Hook that updates claimed issues when session ends.

    This provides continuity by recording session end markers on issues
    that were claimed during the session.
    """

    def __init__(self, config: dict[str, Any]):
        """Initialize hook with configuration.

        Args:
            config: Hook configuration with options:
                - enabled: Whether to update issues on session end (default: True)
                - priority: Hook priority (default: 90, runs late)
        """
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 90)

        logger.debug(f"Initialized BeadsSessionEndHook: enabled={self.enabled}")

    async def on_session_end(self, event: str, data: dict[str, Any]) -> HookResult:
        """Update claimed issues when session ends.

        Event: session:end

        Args:
            event: Event name (should be "session:end")
            data: Event data with session_id

        Returns:
            HookResult (always continue, this is observational)
        """
        if not self.enabled:
            return HookResult(action="continue")

        if not _bd_available():
            return HookResult(action="continue")

        session_id = data.get("session_id")
        if not session_id:
            return HookResult(action="continue")

        # Find issues claimed by this session
        success, output = _run_bd(["list", "--status", "in_progress"])
        if not success:
            return HookResult(action="continue")

        try:
            list_data = json.loads(output)
            issues = list_data.get("issues", [])

            # Look for issues with this session's claim tag
            session_tag = f"[amplifier:claimed-by-session:{session_id}]"

            for issue in issues:
                notes = issue.get("notes", "")
                if session_tag in notes:
                    issue_id = issue.get("id")
                    if issue_id:
                        _run_bd(
                            [
                                "update",
                                issue_id,
                                "--notes",
                                f"[amplifier:session-ended:{session_id}]",
                            ],
                            json_output=False,
                        )
                        logger.debug(f"Marked session end on issue {issue_id}")

        except json.JSONDecodeError:
            pass

        return HookResult(action="continue")
