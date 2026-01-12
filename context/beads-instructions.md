# Beads Task Tracking

You have access to **beads**, a persistent, dependency-aware task tracker that survives across sessions.

## When to Use Beads

Use beads when:
- Work will span multiple sessions
- Tasks have dependencies (one blocks another)
- You discover new work while working on something else
- You want to track what's ready to work on

Do NOT use beads for:
- Simple, single-session tasks (use the todo tool instead)
- Temporary scratch work

## Core Workflow

### 1. Check What's Ready

At session start, you'll see ready work injected into context (if any exists).
You can also explicitly check:

```
beads(operation='ready')
```

This shows tasks with **no open blockers** - work that can be done now.

### 2. Claim Before Working

Before starting on an issue, claim it:

```
beads(operation='claim', issue_id='bd-a1b2')
```

This marks it `in_progress` and tags it with your session ID.

### 3. Discover New Work

If you find new work while working on something, file it with a link:

```
beads(operation='discover', title='Fix edge case in parser', parent_id='bd-a1b2')
```

This creates a `discovered-from` dependency, preserving context about how the work was found.

### 4. Close When Done

```
beads(operation='close', issue_id='bd-a1b2', notes='Implemented caching with Redis')
```

## Dependency Types

Beads tracks four types of relationships:

| Type | Meaning | Use When |
|------|---------|----------|
| `blocks` | A blocks B | B cannot start until A is done |
| `blocked_by` | A is blocked by B | A cannot start until B is done |
| `discovered-from` | A was found while working on B | Preserves discovery context |
| `parent-child` | A is part of epic B | Hierarchical breakdown |

## Session Linking

Every beads operation automatically tags issues with your session ID. This enables:

1. **Finding related sessions**: `beads(operation='sessions', issue_id='bd-a1b2')`
2. **Reviving context**: `amplifier session resume <session_id>`
3. **Answering follow-up questions**: Resume the session where work was done

### Example: Follow-up Question

```
User: "What was the decision on bd-a1b2?"

1. beads(operation='sessions', issue_id='bd-a1b2')
   → Returns: linked_sessions: ['abc123', 'def456']

2. Use task tool to spawn sub-session resuming abc123:
   "Summarize what was decided and implemented for this issue"

3. The resumed session has full context from when the work was done
```

## Landing the Plane

Before ending a session with open beads work:

1. **Update status** on any claimed issues
2. **Add notes** about current state and next steps
3. **File discovered work** with proper links
4. **Don't leave claimed issues** without status update

This ensures the next session (or agent) can pick up seamlessly.

## Quick Reference

| Operation | Required Params | Optional Params |
|-----------|-----------------|-----------------|
| `ready` | - | - |
| `show` | `issue_id` | - |
| `create` | `title` | `notes`, `blocks`, `blocked_by` |
| `update` | `issue_id` | `title`, `status`, `notes`, `blocks`, `blocked_by` |
| `close` | `issue_id` | `notes` |
| `claim` | `issue_id` | - |
| `discover` | `title`, `parent_id` | `notes` |
| `list` | - | `filter_status` |
| `sessions` | `issue_id` | - |
