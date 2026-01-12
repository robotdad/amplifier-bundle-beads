---
name: beads-workflow
description: |
  Deep workflow knowledge for AI agents using beads issue tracking.
  Load when working on complex multi-session tasks, managing dependencies,
  or coordinating work across multiple issues.
version: 1.0.0
license: MIT
metadata:
  category: workflow
  complexity: medium
---

# Beads Workflow Mastery

This skill provides deep knowledge for effectively using beads in complex scenarios.

## The Ready Work Philosophy

Beads is built around one key insight: **"What can I work on right now?"**

`bd ready` returns tasks with no open blockers. This is the starting point for every work session:

1. Check what's ready
2. Pick the highest-value item
3. Claim it
4. Work on it
5. Close it or update status

This creates a pull-based workflow where work flows naturally based on dependencies.

## Dependency Patterns

### When to Use `blocks`

Use blocking dependencies when:
- Task B literally cannot start until Task A completes
- There's a technical dependency (API must exist before client)
- There's a logical sequence (design before implementation)

```
beads(operation='create', title='Implement API endpoint', blocks='bd-client-task')
```

### When to Use `discovered-from`

Use discovered-from when you find new work while working on something:
- Bug found during feature implementation
- Edge case discovered during testing
- Refactoring need identified during code review

```
beads(operation='discover', title='Handle null case in parser', parent_id='bd-feature-task')
```

This preserves the discovery context - you can trace back to understand WHY this work exists.

### When to Use Parent-Child

Use parent-child for hierarchical breakdown:
- Epic → Stories → Tasks
- Feature → Components → Sub-tasks
- Project → Phases → Items

## Landing the Plane Protocol

Before ending ANY session with beads work:

### 1. Status Check
```
beads(operation='list', filter_status='in_progress')
```

Review all in-progress issues - are any claimed by this session?

### 2. Update Each Claimed Issue

For each issue you worked on:
- If done: `beads(operation='close', issue_id='...', notes='Summary of what was done')`
- If blocked: `beads(operation='update', issue_id='...', status='blocked', notes='Blocked because...')`
- If paused: Add notes about current state and next steps

### 3. File Discovered Work

Any new work found during the session should be filed:
```
beads(operation='discover', title='...', parent_id='...')
```

### 4. Final Check
```
beads(operation='ready')
```

Confirm the task graph is in a clean state for the next session.

## Session Linking Strategies

### Tagging Convention

Issues are auto-tagged with session IDs in notes:
- `[amplifier:session:xxx]` - Created in session
- `[amplifier:claimed-by-session:xxx]` - Claimed in session
- `[amplifier:closed-in-session:xxx]` - Closed in session
- `[amplifier:discovered-in-session:xxx]` - Discovered in session
- `[amplifier:session-ended:xxx]` - Session ended with this claimed

### Finding Context

When you need to understand an issue's history:

```
beads(operation='sessions', issue_id='bd-xxx')
```

This returns all linked session IDs. You can then:
1. Resume the session for full context
2. Ask follow-up questions with complete history
3. Understand the decision-making process

### Multi-Session Work

For complex issues spanning many sessions:
1. Each session adds its tag when working on the issue
2. The session list becomes a "breadcrumb trail"
3. You can revive any point in the history

## Coordination Patterns

### Parallel Work Streams

When multiple work streams are active:
1. Create separate issues for each stream
2. Use `blocks` to encode dependencies between streams
3. `bd ready` naturally shows what can proceed in parallel

### Handoff Between Agents

When work will continue in another session/agent:
1. Update issue with detailed notes about current state
2. List any blockers or dependencies
3. Suggest next steps explicitly
4. The next session can revive context via session linking

## Anti-Patterns to Avoid

### Don't Over-Link
Not every task needs beads. Use it for:
- Multi-session work
- Work with dependencies
- Work others need to track

Simple, single-session tasks → use the todo tool instead.

### Don't Forget to Close
Claimed issues left open create confusion. Always:
- Close when done
- Update status if blocked
- Add notes if pausing

### Don't Create Circular Dependencies
If A blocks B and B blocks A, neither will ever be ready.
Review dependencies when creating issues.

## Quick Decision Tree

```
Is this work for the current session only?
├─ Yes → Use todo tool
└─ No → Use beads
    │
    Does it have dependencies?
    ├─ Yes → Create with blocks/blocked_by
    └─ No → Create standalone
        │
        Was it discovered while working on something?
        ├─ Yes → Use discover operation with parent_id
        └─ No → Use create operation
```
