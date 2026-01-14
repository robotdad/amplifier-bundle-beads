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
    config:
      # Centralized beads directory - all projects share this database
      beads_dir: ~/Work/.beads
      hooks:
        ready:
          enabled: true
          max_issues: 10
        session_end:
          enabled: true
---

# Beads Integration

Persistent, dependency-aware task tracking that survives across sessions.

@beads:context/beads-instructions.md

## Your Responsibilities

When using beads, you MUST:

1. **File discovered work immediately** - If you think "we should also..." or "later we need to...", file it NOW as a discovered issue. This is the primary value of beads.

2. **Close issues when complete** - Notes saying "done" ≠ closed. Explicitly close with `beads(operation='close', ...)`.

3. **Before ending any session** with beads work:
   - Review what you did
   - File any follow-up work as discovered issues
   - Close completed issues OR update incomplete ones with status

**Anti-pattern**: Updating notes with "implementation complete" but not closing the issue and not filing follow-up work. This defeats the entire purpose of beads.

## Prerequisites

This bundle requires the `bd` CLI to be installed. The tool will provide installation
instructions if `bd` is not found.

## Quick Reference

| Operation | When to Use |
|-----------|-------------|
| `beads(operation='ready')` | See what work is available |
| `beads(operation='claim', issue_id='...')` | Before starting work on an issue |
| `beads(operation='create', title='...')` | New multi-session work identified |
| `beads(operation='discover', title='...', parent_id='...')` | **Found work while doing other work** (use often!) |
| `beads(operation='close', issue_id='...')` | **Work complete** (required, not optional) |
| `beads(operation='update', issue_id='...', notes='...')` | Work incomplete, update status |

## Session Linking

Issues are automatically tagged with session IDs. Use `beads(operation='sessions', issue_id='...')` to find linked sessions, then `amplifier session resume <session_id>` to revive context.
