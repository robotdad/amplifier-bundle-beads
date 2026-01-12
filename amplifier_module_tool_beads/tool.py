"""Beads tool module - CLI wrapper for bd commands with session linking."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from amplifier_core import ModuleCoordinator, ToolResult

INSTALL_INSTRUCTIONS = """
The 'bd' CLI (beads) is not installed or not in PATH.

Install via one of these methods:

  Homebrew (macOS/Linux):
    brew tap steveyegge/beads && brew install bd

  npm:
    npm install -g @beads/bd

  go install:
    go install github.com/steveyegge/beads/cmd/bd@latest

  Shell script:
    curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash

Documentation: https://github.com/steveyegge/beads/blob/main/docs/INSTALLING.md
""".strip()


class BeadsTool:
    """Wraps the bd CLI for Amplifier agents with session linking."""

    name = "beads"
    description = """Persistent, dependency-aware task tracking with git-backed storage.

Use beads to:
- Track work across sessions with `bd ready` (tasks with no open blockers)
- Create issues that persist beyond the current session
- Link discovered work to parent tasks with dependency tracking
- Claim tasks for the current session

Operations:
- ready: List tasks ready to work on (no open blockers)
- show: Show details of a specific issue
- create: Create a new issue
- update: Update an issue (status, title, notes, dependencies)
- close: Close an issue with optional summary
- claim: Claim an issue for the current session
- discover: Create a new issue linked to a parent (discovered-from)
- list: List all issues (optionally filtered)
- sessions: Show sessions linked to an issue"""

    # Tool input schema - required by Amplifier Tool protocol
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "operation": {
                "type": "string",
                "enum": [
                    "ready",
                    "show",
                    "create",
                    "update",
                    "close",
                    "claim",
                    "discover",
                    "list",
                    "sessions",
                ],
                "description": "The beads operation to perform",
            },
            "issue_id": {
                "type": "string",
                "description": "Issue ID (e.g., 'bd-a1b2') - required for show, update, close, claim, sessions",
            },
            "title": {
                "type": "string",
                "description": "Issue title - required for create, optional for update",
            },
            "status": {
                "type": "string",
                "enum": ["open", "in_progress", "blocked", "closed"],
                "description": "Issue status - for update operation",
            },
            "notes": {
                "type": "string",
                "description": "Notes to add to the issue",
            },
            "parent_id": {
                "type": "string",
                "description": "Parent issue ID - for discover operation (creates discovered-from link)",
            },
            "blocks": {
                "type": "string",
                "description": "Comma-separated issue IDs that this issue blocks",
            },
            "blocked_by": {
                "type": "string",
                "description": "Comma-separated issue IDs that block this issue",
            },
            "filter_status": {
                "type": "string",
                "enum": ["open", "in_progress", "blocked", "closed", "all"],
                "description": "Filter for list operation (default: open)",
            },
        },
        "required": ["operation"],
    }

    def __init__(self, config: dict[str, Any], coordinator: ModuleCoordinator) -> None:
        self.config = config
        self.coordinator = coordinator
        self._session_id: str | None = None

    @property
    def session_id(self) -> str | None:
        """Get the current session ID for tagging issues."""
        if self._session_id is None:
            # Try to get from coordinator context
            self._session_id = self.coordinator.config.get("session_id")
        return self._session_id

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute a beads operation."""
        # Check if bd is available
        if not self._bd_available():
            return ToolResult(
                success=False,
                output=json.dumps(
                    {
                        "error": "beads_not_installed",
                        "message": INSTALL_INSTRUCTIONS,
                    }
                ),
            )

        operation = params.get("operation")
        if not operation:
            return ToolResult(
                success=False,
                output=json.dumps({"error": "missing_operation", "message": "Operation required"}),
            )

        # Dispatch to operation handlers
        handlers = {
            "ready": self._op_ready,
            "show": self._op_show,
            "create": self._op_create,
            "update": self._op_update,
            "close": self._op_close,
            "claim": self._op_claim,
            "discover": self._op_discover,
            "list": self._op_list,
            "sessions": self._op_sessions,
        }

        handler = handlers.get(operation)
        if not handler:
            return ToolResult(
                success=False,
                output=json.dumps(
                    {"error": "unknown_operation", "message": f"Unknown operation: {operation}"}
                ),
            )

        return await handler(params)

    def _bd_available(self) -> bool:
        """Check if bd CLI is available."""
        return shutil.which("bd") is not None

    def _run_bd(self, args: list[str], json_output: bool = True) -> tuple[bool, str]:
        """Run a bd command and return (success, output)."""
        cmd = ["bd"] + args
        if json_output:
            cmd.append("--json")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            else:
                error_msg = result.stderr.strip() or result.stdout.strip()
                return False, error_msg
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 30 seconds"
        except Exception as e:
            return False, f"Failed to execute bd: {e}"

    async def _op_ready(self, params: dict[str, Any]) -> ToolResult:
        """List tasks ready to work on (no open blockers)."""
        success, output = self._run_bd(["ready"])
        if success:
            try:
                data = json.loads(output)
                return ToolResult(success=True, output=json.dumps(data, indent=2))
            except json.JSONDecodeError:
                return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=json.dumps({"error": output}))

    async def _op_show(self, params: dict[str, Any]) -> ToolResult:
        """Show details of a specific issue."""
        issue_id = params.get("issue_id")
        if not issue_id:
            return ToolResult(
                success=False,
                output=json.dumps({"error": "issue_id required for show operation"}),
            )

        success, output = self._run_bd(["show", issue_id])
        if success:
            try:
                data = json.loads(output)
                return ToolResult(success=True, output=json.dumps(data, indent=2))
            except json.JSONDecodeError:
                return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=json.dumps({"error": output}))

    async def _op_create(self, params: dict[str, Any]) -> ToolResult:
        """Create a new issue."""
        title = params.get("title")
        if not title:
            return ToolResult(
                success=False,
                output=json.dumps({"error": "title required for create operation"}),
            )

        args = ["create", title]

        # Add optional parameters
        if params.get("notes"):
            args.extend(["--notes", params["notes"]])
        if params.get("blocked_by"):
            args.extend(["--blocked-by", params["blocked_by"]])
        if params.get("blocks"):
            args.extend(["--blocks", params["blocks"]])

        # Tag with session ID if available
        if self.session_id:
            session_note = f"[amplifier:session:{self.session_id}]"
            existing_notes = params.get("notes", "")
            combined_notes = f"{existing_notes}\n{session_note}" if existing_notes else session_note
            # Update args to include session tag in notes
            if "--notes" in args:
                idx = args.index("--notes")
                args[idx + 1] = combined_notes
            else:
                args.extend(["--notes", session_note])

        success, output = self._run_bd(args)
        if success:
            try:
                data = json.loads(output)
                return ToolResult(success=True, output=json.dumps(data, indent=2))
            except json.JSONDecodeError:
                return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=json.dumps({"error": output}))

    async def _op_update(self, params: dict[str, Any]) -> ToolResult:
        """Update an existing issue."""
        issue_id = params.get("issue_id")
        if not issue_id:
            return ToolResult(
                success=False,
                output=json.dumps({"error": "issue_id required for update operation"}),
            )

        args = ["update", issue_id]

        # Add optional parameters
        if params.get("title"):
            args.extend(["--title", params["title"]])
        if params.get("status"):
            args.extend(["--status", params["status"]])
        if params.get("notes"):
            args.extend(["--notes", params["notes"]])
        if params.get("blocked_by"):
            args.extend(["--blocked-by", params["blocked_by"]])
        if params.get("blocks"):
            args.extend(["--blocks", params["blocks"]])

        success, output = self._run_bd(args)
        if success:
            try:
                data = json.loads(output)
                return ToolResult(success=True, output=json.dumps(data, indent=2))
            except json.JSONDecodeError:
                return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=json.dumps({"error": output}))

    async def _op_close(self, params: dict[str, Any]) -> ToolResult:
        """Close an issue with optional summary."""
        issue_id = params.get("issue_id")
        if not issue_id:
            return ToolResult(
                success=False,
                output=json.dumps({"error": "issue_id required for close operation"}),
            )

        args = ["close", issue_id]

        # Add session summary if available
        notes = params.get("notes", "")
        if self.session_id:
            session_note = f"[amplifier:closed-in-session:{self.session_id}]"
            notes = f"{notes}\n{session_note}" if notes else session_note

        if notes:
            args.extend(["--notes", notes])

        success, output = self._run_bd(args)
        if success:
            try:
                data = json.loads(output)
                return ToolResult(success=True, output=json.dumps(data, indent=2))
            except json.JSONDecodeError:
                return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=json.dumps({"error": output}))

    async def _op_claim(self, params: dict[str, Any]) -> ToolResult:
        """Claim an issue for the current session."""
        issue_id = params.get("issue_id")
        if not issue_id:
            return ToolResult(
                success=False,
                output=json.dumps({"error": "issue_id required for claim operation"}),
            )

        # Update status to in_progress and tag with session
        args = ["update", issue_id, "--status", "in_progress"]

        if self.session_id:
            args.extend(["--notes", f"[amplifier:claimed-by-session:{self.session_id}]"])

        success, output = self._run_bd(args)
        if success:
            try:
                data = json.loads(output)
                data["claimed_by_session"] = self.session_id
                return ToolResult(success=True, output=json.dumps(data, indent=2))
            except json.JSONDecodeError:
                return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=json.dumps({"error": output}))

    async def _op_discover(self, params: dict[str, Any]) -> ToolResult:
        """Create a new issue linked to a parent (discovered-from dependency)."""
        title = params.get("title")
        parent_id = params.get("parent_id")

        if not title:
            return ToolResult(
                success=False,
                output=json.dumps({"error": "title required for discover operation"}),
            )
        if not parent_id:
            return ToolResult(
                success=False,
                output=json.dumps({"error": "parent_id required for discover operation"}),
            )

        # Create with discovered-from dependency
        args = ["create", title, "--discovered-from", parent_id]

        if params.get("notes"):
            args.extend(["--notes", params["notes"]])

        # Tag with session
        if self.session_id:
            session_note = f"[amplifier:discovered-in-session:{self.session_id}]"
            if "--notes" in args:
                idx = args.index("--notes")
                args[idx + 1] = f"{args[idx + 1]}\n{session_note}"
            else:
                args.extend(["--notes", session_note])

        success, output = self._run_bd(args)
        if success:
            try:
                data = json.loads(output)
                return ToolResult(success=True, output=json.dumps(data, indent=2))
            except json.JSONDecodeError:
                return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=json.dumps({"error": output}))

    async def _op_list(self, params: dict[str, Any]) -> ToolResult:
        """List all issues, optionally filtered by status."""
        args = ["list"]

        filter_status = params.get("filter_status", "open")
        if filter_status and filter_status != "all":
            args.extend(["--status", filter_status])

        success, output = self._run_bd(args)
        if success:
            try:
                data = json.loads(output)
                return ToolResult(success=True, output=json.dumps(data, indent=2))
            except json.JSONDecodeError:
                return ToolResult(success=True, output=output)
        return ToolResult(success=False, output=json.dumps({"error": output}))

    async def _op_sessions(self, params: dict[str, Any]) -> ToolResult:
        """Show sessions linked to an issue by parsing notes for session tags."""
        issue_id = params.get("issue_id")
        if not issue_id:
            return ToolResult(
                success=False,
                output=json.dumps({"error": "issue_id required for sessions operation"}),
            )

        # Get issue details and extract session tags from notes
        success, output = self._run_bd(["show", issue_id])
        if not success:
            return ToolResult(success=False, output=json.dumps({"error": output}))

        try:
            data = json.loads(output)
            notes = data.get("notes", "")

            # Extract session IDs from tags like [amplifier:session:abc123]
            import re

            session_pattern = r"\[amplifier:(?:session|claimed-by-session|closed-in-session|discovered-in-session):([^\]]+)\]"
            sessions = list(set(re.findall(session_pattern, notes)))

            return ToolResult(
                success=True,
                output=json.dumps(
                    {
                        "issue_id": issue_id,
                        "linked_sessions": sessions,
                        "session_count": len(sessions),
                        "hint": "Use 'amplifier session resume <session_id>' to revive a session for follow-up questions",
                    },
                    indent=2,
                ),
            )
        except json.JSONDecodeError:
            return ToolResult(
                success=False,
                output=json.dumps({"error": "Failed to parse issue data"}),
            )


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None) -> BeadsTool:
    """Mount the beads tool."""
    tool = BeadsTool(config or {}, coordinator)
    await coordinator.mount("tools", tool)
    return tool
