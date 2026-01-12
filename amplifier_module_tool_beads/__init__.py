"""Amplifier Beads Integration - persistent, dependency-aware task tracking."""

# Amplifier module metadata
__amplifier_module_type__ = "tool"

from amplifier_module_tool_beads.tool import BeadsTool, mount

__all__ = ["BeadsTool", "mount"]
__version__ = "0.1.0"
