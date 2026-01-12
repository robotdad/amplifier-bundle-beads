---
description: Ask a follow-up question about a beads issue by reviving its session
allowed-tools: [beads, task]
argument-hint: <issue-id> <question>
---

Answer a follow-up question about beads issue {{$1}} by finding and reviving linked sessions.

1. Get linked sessions: beads(operation='sessions', issue_id='{{$1}}')

2. If sessions are found, use the task tool to spawn a sub-agent that resumes the most recent session:
   - Pass the session_id to resume
   - Ask it: "{{$2}}"
   - The resumed session has full context from when the work was done

3. If no sessions are linked, show the issue details and answer based on available information:
   beads(operation='show', issue_id='{{$1}}')

4. Present the answer with context about where the information came from (which session, when)
