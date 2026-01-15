"""Beads integration for Amplifier - hooks for ready work injection and workflow reminders."""

from __future__ import annotations

import logging
from typing import Any

from amplifier_core import ModuleCoordinator

from .hooks import BeadsReadyHook, BeadsSessionEndHook, BeadsWorkflowReminderHook

logger = logging.getLogger(__name__)

__all__ = [
    "mount",
    "BeadsReadyHook",
    "BeadsSessionEndHook",
    "BeadsWorkflowReminderHook",
]


async def mount(coordinator: ModuleCoordinator, config: dict[str, Any] | None = None) -> None:
    """Mount beads hooks for ready work injection and workflow reminders.

    Args:
        coordinator: Module coordinator
        config: Hook configuration with options:
            - beads_dir: Path to centralized beads directory (default: uses BEADS_DIR env)
            - hooks.ready.enabled: Inject ready tasks on session start (default: True)
            - hooks.ready.max_issues: Max issues to show (default: 10)
            - hooks.session_end.enabled: Update issues on session end (default: True)
            - hooks.workflow_reminder.enabled: Periodic workflow nudges (default: True)
            - hooks.workflow_reminder.reminder_interval: Tool calls between reminders (default: 8)
    """
    config = config or {}
    hooks_config = config.get("hooks", {})
    beads_dir = config.get("beads_dir")

    # Ready hook - injects ready tasks on first LLM request
    ready_config = hooks_config.get("ready", {})
    if ready_config.get("enabled", True):
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
        session_end_hook = BeadsSessionEndHook(session_end_config, beads_dir=beads_dir)
        coordinator.hooks.register(
            event="session:end",
            handler=session_end_hook.on_session_end,
            priority=session_end_hook.priority,
            name="beads-session-end",
        )
        logger.info("Registered beads-session-end hook on session:end")

    # Workflow reminder hook - periodic nudges about discovered work and closing issues
    workflow_config = hooks_config.get("workflow_reminder", {})
    if workflow_config.get("enabled", True):
        workflow_hook = BeadsWorkflowReminderHook(workflow_config, beads_dir=beads_dir)
        # Register on tool:post to track tool usage
        coordinator.hooks.register(
            event="tool:post",
            handler=workflow_hook.on_tool_post,
            priority=workflow_hook.priority,
            name="beads-workflow-tracker",
        )
        # Register on provider:request to inject reminders
        coordinator.hooks.register(
            event="provider:request",
            handler=workflow_hook.on_provider_request,
            priority=workflow_hook.priority,
            name="beads-workflow-reminder",
        )
        logger.info("Registered beads-workflow-reminder hooks")
