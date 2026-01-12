---
description: Close a beads issue with a summary
allowed-tools: [beads]
argument-hint: <issue-id> [summary]
---

Close the beads issue {{$1}} with an optional summary.

1. Show the current issue state: beads(operation='show', issue_id='{{$1}}')
2. Close it with notes: beads(operation='close', issue_id='{{$1}}', notes='{{$2}}')
3. Check if there are any issues that were blocked by this one that are now ready
4. Suggest next work if appropriate
