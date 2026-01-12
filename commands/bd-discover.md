---
description: File discovered work linked to a parent issue
allowed-tools: [beads]
argument-hint: <parent-id> <title>
---

Create a new beads issue discovered while working on {{$1}}.

1. Create the issue with discovered-from link:
   beads(operation='discover', title='{{$2}}', parent_id='{{$1}}')

2. Confirm creation and show the new issue ID

3. Ask if the user wants to add any additional notes or dependencies
