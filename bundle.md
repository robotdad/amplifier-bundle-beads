---
bundle:
  name: beads
  version: 0.2.0
  description: |
    Beads integration for Amplifier - persistent, dependency-aware task tracking
    using the bd CLI. Agents use bd directly via bash.

hooks:
  - module: beads-hooks
    source: git+https://github.com/robotdad/amplifier-bundle-beads@main
    config:
      # Centralized beads directory - all projects share this database
      # Comment out to use per-project .beads/ directories instead
      beads_dir: ~/Work/.beads
      hooks:
        ready:
          enabled: true
          max_issues: 10
        session_end:
          enabled: true
        workflow_reminder:
          enabled: true
          reminder_interval: 8
---

# Beads Integration

Persistent, dependency-aware task tracking using the `bd` CLI.

@beads:context/beads-instructions.md

## Your Responsibilities

When using beads, you MUST:

1. **File discovered work immediately** - If you think "we should also..." or "later we need to...", file it NOW with `bd create "Title" --discovered-from <parent-id> --json`. This is the primary value of beads.

2. **Close issues when complete** - Notes saying "done" ≠ closed. Explicitly close with `bd close <id> --reason "Summary" --json`.

3. **Before ending any session** with beads work:
   - Review what you did
   - File any follow-up work as discovered issues
   - Close completed issues OR update incomplete ones with status
   - Run `bd sync` to ensure changes are persisted

**Anti-pattern**: Updating notes with "implementation complete" but not closing the issue and not filing follow-up work. This defeats the entire purpose of beads.

## Quick Reference

| Task | Command |
|------|---------|
| See ready work | `bd ready --json` |
| Claim/start work | `bd update <id> --status in_progress --json` |
| Create new task | `bd create "Title" -p 1 --json` |
| Discovered work | `bd create "Title" --discovered-from <parent-id> --json` |
| Complete work | `bd close <id> --reason "Summary" --json` |
| Update status | `bd update <id> --notes "Progress..." --json` |
| Sync at end | `bd sync` |
