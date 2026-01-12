"""Beads hook module - session lifecycle integration."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from amplifier_core import HookResult, ModuleCoordinator


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


def _format_ready_work(data: dict[str, Any]) -> str:
    """Format ready work for context injection."""
    issues = data.get("issues", [])
    if not issues:
        return ""

    lines = ["## Ready Work (beads)", ""]
    lines.append("Tasks with no open blockers, ready to work on:")
    lines.append("")

    for issue in issues[:10]:  # Limit to 10 to save context
        issue_id = issue.get("id", "?")
        title = issue.get("title", "Untitled")
        priority = issue.get("priority", "")
        priority_str = f" [{priority}]" if priority else ""
        lines.append(f"- **{issue_id}**: {title}{priority_str}")

    if len(issues) > 10:
        lines.append(f"- ... and {len(issues) - 10} more")

    lines.append("")
    lines.append("Use `beads(operation='claim', issue_id='...')` to claim a task.")
    lines.append("")

    return "\n".join(lines)


async def on_session_start(event: str, data: dict[str, Any]) -> HookResult:
    """Inject bd ready output into agent context on session start.

    This gives the agent immediate visibility into what work is available.
    """
    if not _bd_available():
        # Silently skip if bd not installed - tool will show install instructions when used
        return HookResult()

    # Check if beads is initialized in this directory
    success, output = _run_bd(["ready"])
    if not success:
        # Not initialized or other error - skip silently
        return HookResult()

    try:
        ready_data = json.loads(output)
        issues = ready_data.get("issues", [])

        if not issues:
            # No ready work - don't inject anything
            return HookResult()

        context = _format_ready_work(ready_data)
        return HookResult(context_injection=context)

    except json.JSONDecodeError:
        return HookResult()


async def on_session_end(event: str, data: dict[str, Any]) -> HookResult:
    """Update claimed issues when session ends.

    This provides continuity by recording what happened in this session.
    """
    if not _bd_available():
        return HookResult()

    session_id = data.get("session_id")
    if not session_id:
        return HookResult()

    # Find issues that were claimed by this session
    success, output = _run_bd(["list", "--status", "in_progress"])
    if not success:
        return HookResult()

    try:
        list_data = json.loads(output)
        issues = list_data.get("issues", [])

        # Look for issues with this session's claim tag
        session_tag = f"[amplifier:claimed-by-session:{session_id}]"
        claimed_issues = []

        for issue in issues:
            notes = issue.get("notes", "")
            if session_tag in notes:
                claimed_issues.append(issue.get("id"))

        # Add session-end note to claimed issues
        for issue_id in claimed_issues:
            _run_bd(
                [
                    "update",
                    issue_id,
                    "--notes",
                    f"[amplifier:session-ended:{session_id}]",
                ],
                json_output=False,
            )

    except json.JSONDecodeError:
        pass

    return HookResult()


class BeadsHook:
    """Beads lifecycle hook for session start/end events."""

    name = "beads"

    def __init__(self, config: dict[str, Any], coordinator: ModuleCoordinator) -> None:
        self.config = config
        self.coordinator = coordinator
        self.inject_ready = config.get("inject_ready", True)

    async def __call__(self, event: str, data: dict[str, Any]) -> HookResult:
        """Handle lifecycle events."""
        if event == "session:start" and self.inject_ready:
            return await on_session_start(event, data)
        elif event == "session:end":
            return await on_session_end(event, data)

        return HookResult()


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any]) -> None:
    """Mount the beads hook."""
    hook = BeadsHook(config, coordinator)

    # Subscribe to session lifecycle events
    coordinator.subscribe("session:start", hook)
    coordinator.subscribe("session:end", hook)
