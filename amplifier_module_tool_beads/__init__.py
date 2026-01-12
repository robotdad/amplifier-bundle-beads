"""Amplifier Beads Integration - persistent, dependency-aware task tracking."""

# Amplifier module metadata
__amplifier_module_type__ = "tool"

from amplifier_module_tool_beads.hooks import mount as mount_hooks
from amplifier_module_tool_beads.tool import BeadsTool
from amplifier_module_tool_beads.tool import mount as mount_tool

__all__ = ["BeadsTool", "mount_tool", "mount_hooks"]
__version__ = "0.1.0"
