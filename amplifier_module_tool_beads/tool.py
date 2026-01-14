"""Beads tool module - CLI wrapper for bd commands with session linking."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any

from amplifier_core import ModuleCoordinator, ToolResult

INSTALL_SCRIPT_URL = "https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh"

INSTALL_INSTRUCTIONS = """
The 'bd' CLI (beads) is not installed or not in PATH.

You can install it automatically:
  beads(operation='setup', action='install')

Or install manually via one of these methods:

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
- setup: Install bd CLI and/or initialize beads in current directory
- status: Check if bd is installed and beads is initialized
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
                    "setup",
                    "status",
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
            "action": {
                "type": "string",
                "enum": ["install", "init", "both"],
                "description": "For setup operation: install (install bd CLI), init (initialize beads in current dir), both (install then init)",
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
        # Support configurable beads directory for centralized tracking
        self._beads_dir: str | None = config.get("beads_dir")

    @property
    def session_id(self) -> str | None:
        """Get the current session ID for tagging issues."""
        if self._session_id is None:
            # Try to get from coordinator context
            self._session_id = self.coordinator.config.get("session_id")
        return self._session_id

    async def execute(self, params: dict[str, Any]) -> ToolResult:
        """Execute a beads operation."""
        operation = params.get("operation")
        if not operation:
            return ToolResult(
                success=False,
                output=json.dumps({"error": "missing_operation", "message": "Operation required"}),
            )

        # Setup and status work even without bd installed
        if operation == "setup":
            return await self._op_setup(params)
        if operation == "status":
            return await self._op_status(params)

        # All other operations require bd to be installed
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

    def _beads_initialized(self) -> bool:
        """Check if beads is initialized (either in configured beads_dir or current directory)."""
        import os

        if self._beads_dir:
            # Check configured centralized directory
            beads_path = os.path.expanduser(self._beads_dir)
            return os.path.isdir(beads_path)
        else:
            # Check current directory
            return os.path.isdir(".beads")

    async def _op_setup(self, params: dict[str, Any]) -> ToolResult:
        """Install bd CLI and/or initialize beads in current directory.

        Actions:
        - install: Download and install the bd CLI
        - init: Run 'bd init' in current directory
        - both: Install then init (default if bd not installed)
        """
        action = params.get("action", "both" if not self._bd_available() else "init")

        results: dict[str, Any] = {
            "action": action,
            "bd_installed_before": self._bd_available(),
            "beads_initialized_before": self._beads_initialized() if self._bd_available() else None,
        }

        # Install bd if requested
        if action in ("install", "both"):
            if self._bd_available():
                results["install"] = {"status": "skipped", "reason": "bd already installed"}
            else:
                install_result = self._install_bd()
                results["install"] = install_result
                if not install_result.get("success"):
                    return ToolResult(
                        success=False,
                        output=json.dumps(results, indent=2),
                    )

        # Initialize beads if requested
        if action in ("init", "both"):
            if not self._bd_available():
                results["init"] = {"status": "skipped", "reason": "bd not installed"}
            elif self._beads_initialized():
                results["init"] = {"status": "skipped", "reason": "beads already initialized"}
            else:
                success, output = self._run_bd(["init"], json_output=False)
                results["init"] = {
                    "status": "success" if success else "failed",
                    "output": output,
                }

        results["bd_installed_after"] = self._bd_available()
        results["beads_initialized_after"] = (
            self._beads_initialized() if self._bd_available() else None
        )

        return ToolResult(success=True, output=json.dumps(results, indent=2))

    def _install_bd(self) -> dict[str, Any]:
        """Install bd CLI using the official install script."""
        import os

        try:
            # Use the official install script (handles platform detection internally)
            result = subprocess.run(
                ["bash", "-c", f"curl -fsSL {INSTALL_SCRIPT_URL} | bash"],
                capture_output=True,
                text=True,
                timeout=120,
                env={**os.environ, "HOME": os.path.expanduser("~")},
            )

            if result.returncode == 0:
                # Refresh PATH to find newly installed bd
                return {
                    "success": True,
                    "method": "install_script",
                    "output": result.stdout[-500:] if len(result.stdout) > 500 else result.stdout,
                    "hint": "You may need to restart your shell or run 'hash -r' to use bd",
                }
            else:
                return {
                    "success": False,
                    "method": "install_script",
                    "error": result.stderr or result.stdout,
                    "hint": "Try manual installation - see INSTALL_INSTRUCTIONS",
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Installation timed out after 120 seconds",
                "hint": "Try manual installation",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "hint": "Try manual installation",
            }

    async def _op_status(self, params: dict[str, Any]) -> ToolResult:
        """Check beads prerequisites and initialization status."""
        status: dict[str, Any] = {
            "bd_installed": self._bd_available(),
            "bd_path": shutil.which("bd"),
        }

        if self._bd_available():
            # Get bd version
            success, output = self._run_bd(["version"], json_output=False)
            status["bd_version"] = output.strip() if success else "unknown"

            # Check if initialized
            status["beads_initialized"] = self._beads_initialized()

            if self._beads_initialized():
                # Get issue count
                success, output = self._run_bd(["list", "--status", "all"])
                if success:
                    try:
                        issues = json.loads(output)
                        if isinstance(issues, list):
                            status["issue_count"] = len(issues)
                        else:
                            status["issue_count"] = len(issues.get("issues", []))
                    except json.JSONDecodeError:
                        status["issue_count"] = "unknown"
        else:
            status["setup_hint"] = "Run beads(operation='setup') to install bd CLI"

        return ToolResult(success=True, output=json.dumps(status, indent=2))

    def _run_bd(self, args: list[str], json_output: bool = True) -> tuple[bool, str]:
        """Run a bd command and return (success, output)."""
        import os

        cmd = ["bd"] + args
        if json_output:
            cmd.append("--json")

        # Build environment with optional BEADS_DIR for centralized tracking
        env = os.environ.copy()
        if self._beads_dir:
            env["BEADS_DIR"] = os.path.expanduser(self._beads_dir)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                env=env,
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
    """Mount the beads tool and lifecycle hooks.

    Args:
        coordinator: Module coordinator
        config: Tool configuration with options:
            - hooks.ready.enabled: Inject ready tasks on session start (default: True)
            - hooks.ready.max_issues: Max issues to show (default: 10)
            - hooks.session_end.enabled: Update issues on session end (default: True)
    """
    import logging

    logger = logging.getLogger(__name__)
    config = config or {}

    # Mount the tool
    tool = BeadsTool(config, coordinator)
    await coordinator.mount("tools", tool)
    logger.info("Mounted beads tool")

    # Mount hooks
    hooks_config = config.get("hooks", {})

    # Get beads_dir from top-level config to pass to hooks
    beads_dir = config.get("beads_dir")

    # Ready hook - injects ready tasks on first LLM request
    ready_config = hooks_config.get("ready", {})
    if ready_config.get("enabled", True):
        from amplifier_module_tool_beads.hooks import BeadsReadyHook

        ready_hook = BeadsReadyHook(ready_config, beads_dir=beads_dir)
        coordinator.hooks.register(
            event="provider:request",
            handler=ready_hook.on_provider_request,
            priority=ready_hook.priority,
            name="beads-ready",
        )
        logger.info("Registered beads-ready hook on provider:request")

    # Session end hook - updates claimed issues when session ends
    session_end_config = hooks_config.get("session_end", {})
    if session_end_config.get("enabled", True):
        from amplifier_module_tool_beads.hooks import BeadsSessionEndHook

        session_end_hook = BeadsSessionEndHook(session_end_config, beads_dir=beads_dir)
        coordinator.hooks.register(
            event="session:end",
            handler=session_end_hook.on_session_end,
            priority=session_end_hook.priority,
            name="beads-session-end",
        )
        logger.info("Registered beads-session-end hook on session:end")

    return tool
