"""Amplifier Beads Integration - persistent, dependency-aware task tracking."""

from amplifier_bundle_beads.hooks import mount as mount_hooks
from amplifier_bundle_beads.tool import BeadsTool
from amplifier_bundle_beads.tool import mount as mount_tool

__all__ = ["BeadsTool", "mount_tool", "mount_hooks"]
__version__ = "0.1.0"
