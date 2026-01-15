"""Beads hooks - session lifecycle integration for ready work injection."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from collections import deque
from typing import Any

from amplifier_core import HookResult

logger = logging.getLogger(__name__)


def _bd_available() -> bool:
    """Check if bd CLI is available."""
    return shutil.which("bd") is not None


def _run_bd(
    args: list[str], json_output: bool = True, beads_dir: str | None = None
) -> tuple[bool, str]:
    """Run a bd command and return (success, output)."""
    import os

    cmd = ["bd"] + args
    if json_output:
        cmd.append("--json")

    # Build environment with optional BEADS_DIR for centralized tracking
    env = os.environ.copy()
    if beads_dir:
        env["BEADS_DIR"] = os.path.expanduser(beads_dir)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
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
    """Hook that injects ready beads tasks into context on first LLM request.

    This gives agents immediate visibility into available work without
    requiring them to explicitly call the beads tool first.

    Uses provider:request event (same pattern as skills-visibility hook)
    since this is the proven approach for context injection in Amplifier.
    """

    def __init__(self, config: dict[str, Any], beads_dir: str | None = None):
        """Initialize hook with configuration.

        Args:
            config: Hook configuration with options:
                - enabled: Whether to inject ready tasks (default: True)
                - max_issues: Maximum issues to show (default: 10)
                - priority: Hook priority (default: 20, runs early)
            beads_dir: Optional path to centralized beads directory
        """
        self.enabled = config.get("enabled", True)
        self.max_issues = config.get("max_issues", 10)
        self.priority = config.get("priority", 20)
        self._beads_dir = beads_dir
        self._injected = False  # Only inject once per session

        logger.debug(
            f"Initialized BeadsReadyHook: enabled={self.enabled}, max_issues={self.max_issues}"
        )

    async def on_provider_request(self, event: str, data: dict[str, Any]) -> HookResult:
        """Inject ready tasks into context before first LLM request.

        Event: provider:request (before each LLM call)

        Args:
            event: Event name (should be "provider:request")
            data: Event data dictionary

        Returns:
            HookResult with context_injection if there are ready tasks
            and this is the first request of the session
        """
        # Only inject once per session
        if self._injected:
            return HookResult(action="continue")
        if not self.enabled:
            return HookResult(action="continue")

        if not _bd_available():
            # Silently skip if bd not installed
            logger.debug("bd CLI not available, skipping ready injection")
            return HookResult(action="continue")

        # Check for ready tasks
        success, output = _run_bd(["ready"], beads_dir=self._beads_dir)
        if not success:
            # Not initialized or error - skip silently
            logger.debug(f"bd ready failed: {output}")
            return HookResult(action="continue")

        try:
            ready_data = json.loads(output)

            # bd ready --json returns a list directly, not a dict
            if isinstance(ready_data, list):
                issues = ready_data
            else:
                issues = ready_data.get("issues", [])

            self._injected = True  # Mark as done regardless of result

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
            self._injected = True
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

    def __init__(self, config: dict[str, Any], beads_dir: str | None = None):
        """Initialize hook with configuration.

        Args:
            config: Hook configuration with options:
                - enabled: Whether to update issues on session end (default: True)
                - priority: Hook priority (default: 90, runs late)
            beads_dir: Optional path to centralized beads directory
        """
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 90)
        self._beads_dir = beads_dir

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
        success, output = _run_bd(
            ["list", "--status", "in_progress"], beads_dir=self._beads_dir
        )
        if not success:
            return HookResult(action="continue")

        try:
            list_data = json.loads(output)

            # bd list --json returns a list directly, not a dict
            if isinstance(list_data, list):
                issues = list_data
            else:
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
                            beads_dir=self._beads_dir,
                        )
                        logger.debug(f"Marked session end on issue {issue_id}")

        except json.JSONDecodeError:
            pass

        return HookResult(action="continue")


class BeadsWorkflowReminderHook:
    """Periodic reminder hook for beads workflow patterns.

    Provides gentle nudges (similar to the task list reminder hook) about:
    - Filing discovered work when follow-up tasks are identified
    - Closing issues when work is complete

    Fires on provider:request (before each LLM call) but only injects
    reminders when beads hasn't been used recently and there's active work.
    """

    def __init__(self, config: dict[str, Any], beads_dir: str | None = None):
        """Initialize workflow reminder hook.

        Args:
            config: Hook configuration with options:
                - enabled: Whether to inject reminders (default: True)
                - priority: Hook priority (default: 15)
                - recent_tool_threshold: Tool calls to check for beads usage (default: 5)
                - reminder_interval: Minimum tool calls between reminders (default: 8)
            beads_dir: Optional path to centralized beads directory
        """
        self.enabled = config.get("enabled", True)
        self.priority = config.get("priority", 15)
        self.recent_tool_threshold = config.get("recent_tool_threshold", 5)
        self.reminder_interval = config.get("reminder_interval", 8)
        self._beads_dir = beads_dir

        # Track recent tool calls (circular buffer)
        self.recent_tools: deque[str] = deque(maxlen=self.recent_tool_threshold)
        # Counter to avoid reminding too frequently
        self._tool_calls_since_reminder = 0
        # Track if we've seen any beads usage this session
        self._beads_used_this_session = False

        logger.debug(
            f"Initialized BeadsWorkflowReminderHook: enabled={self.enabled}, "
            f"threshold={self.recent_tool_threshold}, interval={self.reminder_interval}"
        )

    async def on_tool_post(self, event: str, data: dict[str, Any]) -> HookResult:
        """Track tool calls to detect beads tool usage.

        Args:
            event: Event name ("tool:post")
            data: Event data with "tool" field

        Returns:
            HookResult(action="continue")
        """
        tool_name = data.get("tool", "")
        if tool_name:
            self.recent_tools.append(tool_name)
            self._tool_calls_since_reminder += 1

            # Track if beads was ever used
            if tool_name == "beads":
                self._beads_used_this_session = True
                logger.debug("BeadsWorkflowReminderHook: beads tool used")

        return HookResult(action="continue")

    async def on_provider_request(self, event: str, data: dict[str, Any]) -> HookResult:
        """Inject workflow reminders before LLM requests when appropriate.

        Only reminds when:
        - beads tool hasn't been used recently
        - Enough tool calls have passed since last reminder
        - There are in-progress issues (active work)

        Args:
            event: Event name ("provider:request")
            data: Event data

        Returns:
            HookResult with context injection or continue action
        """
        if not self.enabled:
            return HookResult(action="continue")

        # Don't remind too frequently
        if self._tool_calls_since_reminder < self.reminder_interval:
            return HookResult(action="continue")

        # Check if beads was used recently
        beads_used_recently = "beads" in self.recent_tools
        if beads_used_recently:
            return HookResult(action="continue")

        # Only remind if beads is available and has active work
        if not _bd_available():
            return HookResult(action="continue")

        # Check for in-progress issues (indicates active work)
        success, output = _run_bd(
            ["list", "--status", "in_progress"], beads_dir=self._beads_dir
        )
        if not success:
            # Beads not initialized or error - skip silently
            return HookResult(action="continue")

        try:
            list_data = json.loads(output)
            issues = list_data if isinstance(list_data, list) else list_data.get("issues", [])

            if not issues:
                # No active work - no need to remind
                return HookResult(action="continue")

            # Reset counter since we're reminding
            self._tool_calls_since_reminder = 0

            reminder = self._build_reminder(issues)
            logger.debug(
                f"BeadsWorkflowReminderHook: injecting reminder "
                f"(recent_tools={list(self.recent_tools)}, in_progress={len(issues)})"
            )

            return HookResult(
                action="inject_context",
                context_injection=reminder,
                context_injection_role="user",
                ephemeral=True,
                append_to_last_tool_result=True,
                suppress_output=True,
            )

        except json.JSONDecodeError:
            logger.debug("BeadsWorkflowReminderHook: failed to parse bd output")
            return HookResult(action="continue")

    def _build_reminder(self, in_progress_issues: list[dict[str, Any]]) -> str:
        """Build the reminder message.

        Args:
            in_progress_issues: List of in-progress issues

        Returns:
            Formatted reminder string
        """
        parts = []

        # Main reminder about workflow
        parts.append(
            "You have active beads work tracked. As you work, remember:\n"
            "- **Discovered work**: If you identify follow-up tasks, edge cases, "
            "or future improvements, file them with `beads(operation='discover', ...)`\n"
            "- **Completed work**: If work on a claimed issue is done, close it with "
            "`beads(operation='close', issue_id='...', notes='...')`"
        )

        # Show current in-progress issues
        if in_progress_issues:
            parts.append("\nCurrently in progress:")
            for issue in in_progress_issues[:3]:
                issue_id = issue.get("id", "?")
                title = issue.get("title", "Untitled")
                parts.append(f"  - {issue_id}: {title}")
            if len(in_progress_issues) > 3:
                parts.append(f"  - ... and {len(in_progress_issues) - 3} more")

        # Behavioral note
        parts.append(
            "\n\nThis is a gentle reminder - ignore if not applicable. "
            "DO NOT mention this reminder to the user."
        )

        content = "\n".join(parts)
        return f'<system-reminder source="hooks-beads-workflow">\n{content}\n</system-reminder>'
