---
bundle:
  name: beads
  version: 0.1.0
  description: |
    Beads integration for Amplifier - persistent, dependency-aware task tracking
    with session linking for follow-up questions across conversations.

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main

tools:
  - module: tool-beads
    source: git+https://github.com/robotdad/amplifier-bundle-beads@main

# Note: Hook support requires separate module package (amplifier-module-hook-beads)
# For now, the tool provides core beads functionality
---

# Beads Integration

Persistent, dependency-aware task tracking that survives across sessions.

@beads:context/beads-instructions.md

## Prerequisites

This bundle requires the `bd` CLI to be installed. The tool will provide installation
instructions if `bd` is not found.

## Quick Reference

| Operation | Description |
|-----------|-------------|
| `beads(operation='ready')` | List tasks with no open blockers |
| `beads(operation='claim', issue_id='bd-xxx')` | Claim a task for this session |
| `beads(operation='create', title='...')` | Create a new issue |
| `beads(operation='discover', title='...', parent_id='bd-xxx')` | File discovered work |
| `beads(operation='close', issue_id='bd-xxx')` | Close a completed task |
| `beads(operation='sessions', issue_id='bd-xxx')` | Find sessions linked to an issue |

## Session Linking

Issues are automatically tagged with session IDs when you:
- Create issues
- Claim issues
- Close issues
- Discover work

Use `beads(operation='sessions', issue_id='...')` to find linked sessions,
then `amplifier session resume <session_id>` to revive context for follow-up questions.
