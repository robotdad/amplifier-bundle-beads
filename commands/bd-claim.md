---
description: Claim a beads issue for the current session
allowed-tools: [beads]
argument-hint: <issue-id>
---

Claim the beads issue {{$1}} for the current session.

1. First show the issue details using beads(operation='show', issue_id='{{$1}}')
2. Then claim it using beads(operation='claim', issue_id='{{$1}}')
3. Confirm the claim and ask what aspect of the issue to work on first
