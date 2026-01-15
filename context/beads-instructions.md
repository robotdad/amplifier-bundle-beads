# Beads Task Tracking

You have access to **beads** (`bd` CLI), a persistent, dependency-aware task tracker that survives across sessions. Use it via bash.

## Setup

Check if bd is installed:

```bash
which bd
```

If not found, install it:

```bash
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
```

Initialize beads (once per workspace or centralized location):

```bash
bd init
```

For centralized tracking across projects, set `BEADS_DIR` in your environment:

```bash
export BEADS_DIR=~/Work/.beads
bd init  # Run once in that directory
```

When `BEADS_DIR` is set, all `bd` commands use that database regardless of current directory.

## When to Use Beads

Use beads when:
- Work will span multiple sessions
- Tasks have dependencies (one blocks another)
- You discover new work while working on something else
- You want to track what's ready to work on
- Work spans multiple projects or repositories

Do NOT use beads for:
- Simple, single-session tasks (use the todo tool instead)
- Temporary scratch work
- Tasks that will be completed in this conversation

## Essential Commands

| Command | Purpose |
|---------|---------|
| `bd ready` | List tasks with no open blockers (what can be done now) |
| `bd create "Title" -p 1` | Create a new task (priority 0-3) |
| `bd show <id>` | View task details and audit trail |
| `bd close <id> --reason "Done"` | Close a completed task |
| `bd list` | List all tasks |
| `bd list --status in_progress` | Filter by status |

Always use `--json` flag when you need to parse output programmatically:

```bash
bd ready --json
bd show bd-a1b2 --json
```

## Core Workflow

### 1. Check What's Ready

At session start, check for available work:

```bash
bd ready --json
```

This shows tasks with **no open blockers** - work that can be done now.

### 2. Claim Before Working

Before starting on an issue, mark it in progress:

```bash
bd update bd-a1b2 --status in_progress --json
```

### 3. Discover New Work

If you find new work while working on something, file it with a link:

```bash
bd create "Fix edge case in parser" -p 2 --discovered-from bd-a1b2 --json
```

This creates a `discovered-from` dependency, preserving context about how the work was found.

### 4. Close When Done

```bash
bd close bd-a1b2 --reason "Implemented caching with Redis" --json
```

## Dependency Types

Beads tracks four types of relationships:

| Type | Flag | Use When |
|------|------|----------|
| `blocks` | `--blocks bd-xyz` | This task blocks another |
| `blocked-by` | `--blocked-by bd-xyz` | This task is blocked by another |
| `discovered-from` | `--discovered-from bd-xyz` | Found while working on another task |
| `parent-child` | `--parent bd-xyz` | Hierarchical breakdown (epics) |

### Adding Dependencies

```bash
bd dep add bd-a1b2 bd-c3d4 --type blocks --json
```

## Landing the Plane (MANDATORY)

Before ending ANY session where you worked on tracked issues, complete this checklist:

### Step 1: File ALL Discovered Work

Review what you did. For each of these, file a discovered issue:
- Follow-up tasks mentioned but not done
- "We should also..." items
- Edge cases deferred
- Integration/testing work identified
- Documentation needs
- Refactoring opportunities noted

**If you identified work and didn't file it, the whole point of beads is lost.**

```bash
bd create "Integration testing needed" -p 2 --discovered-from bd-xyz --json
```

### Step 2: Update or Close Issues

For each issue you worked on:
- **Complete?** → `bd close <id> --reason "Summary of what was done"`
- **Incomplete?** → `bd update <id> --notes "Current state and what remains"`

### Step 3: Sync (if using centralized tracking)

```bash
bd sync
```

This exports to JSONL and syncs with git if configured.

### Step 4: Verify

Ask yourself:
- "If a different agent picks this up tomorrow, do they have everything they need?"
- "Is there any work I identified that isn't tracked anywhere?"

If the answer to either is "no" → go back and fix it.

## Agent Behavior Guidelines

### CRITICAL: Filing Discovered Work

**This is the primary value of beads.** When you identify work that should be done but won't be done in this session, you MUST file it as a discovered issue.

| While Working On | You Notice | Action |
|------------------|------------|--------|
| Implementing feature | Edge case needs handling later | `bd create ... --discovered-from ...` |
| Building a bundle | Integration testing needed | `bd create ... --discovered-from ...` |
| Fixing a bug | Related code needs refactoring | `bd create ... --discovered-from ...` |
| Any implementation | Follow-up work (docs, tests, polish) | `bd create ... --discovered-from ...` |

**The pattern**: If you think "we should also..." or "later we'll need to..." → FILE IT NOW.

### CRITICAL: Closing Issues

An issue with notes saying "implementation complete" is NOT closed. You must explicitly close it:

```bash
bd close bd-xyz --reason "Summary of what was done" --json
```

### Do Automatically
- Check `bd ready` at session start
- Create issues when multi-session work is identified
- Mark issues `in_progress` before starting work
- **File discovered work immediately when identified** (don't wait until session end)
- **Close issues when their specific scope is complete**
- Update notes before session ends if work is incomplete
- Run `bd sync` at end of session

### Ask User First
- Before creating issues for work the user described (confirm scope)
- When choosing between multiple ready issues (let user prioritize)

### Never
- Create beads issues for simple single-turn tasks
- Leave claimed issues without updating at session end
- Assume issue priority without user input
- **Update notes with "complete" without actually closing the issue**
- **End a session with identified follow-up work without filing it**

## Quick Reference

```bash
# See what's ready
bd ready --json

# Create new work
bd create "Title" -p 1 --json
bd create "Found while working" -p 2 --discovered-from bd-xyz --json

# Work on something
bd update bd-xyz --status in_progress --json

# Complete work
bd close bd-xyz --reason "Done" --json

# Check status
bd show bd-xyz --json
bd list --json
bd list --status in_progress --json

# Sync at end of session
bd sync
```

## Troubleshooting

```bash
# Check beads health
bd doctor

# See daemon status
bd daemons list

# Force sync
bd sync --force
```
