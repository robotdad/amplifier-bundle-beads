# amplifier-bundle-beads

Persistent task tracking for Amplifier that survives across sessions.

## What is Beads?

[Beads](https://github.com/steveyegge/beads) is a task tracker designed for AI agents. It tracks:
- What work is ready (no blockers)
- Dependencies between tasks
- Which sessions worked on what (so you can ask follow-up questions later)

## Getting Started

**Step 1**: Create `.amplifier/bundle.md` in your workspace:

```bash
mkdir -p .amplifier
curl -o .amplifier/bundle.md https://raw.githubusercontent.com/robotdad/amplifier-bundle-beads/main/examples/workspace-bundle.md
```

**Step 2**: Add and activate the bundle:

```bash
amplifier bundle add file://.amplifier/bundle.md
amplifier bundle use my-workspace
```

**Step 3**: Start Amplifier and work:

```bash
amplifier
```

The agent handles the rest.

### What Happens on First Run

When you first start a session with this bundle:

1. If `bd` (the beads CLI) isn't installed, the agent will offer to install it
2. If beads isn't initialized, the agent will set it up
3. Once ready, the agent automatically:
   - Shows you available work at session start
   - Tracks multi-session tasks as you work
   - Links sessions to issues for follow-up questions

You don't need to learn beads commands - just work naturally and the agent handles the tracking.

## Configuration

### Default: Centralized Tracking

By default, this bundle uses `~/Work/.beads` as a shared database across all your projects. This means:
- All your work tracked in one place
- No per-project setup needed
- Works across multiple workspaces

### Alternative: Per-Project Tracking

If you prefer issues stored with each project (in `.beads/`), edit your bundle to remove the `beads_dir` config. The agent will then initialize beads in each project as needed.

### Private Tracking

The default `~/Work/.beads` location can be backed by a private git repo if you want to sync/backup your task history. The agent can help set this up.

## What the Agent Does

| Situation | Agent Action |
|-----------|--------------|
| Session starts | Shows ready work (if any) |
| You describe multi-session work | Creates issues to track it |
| You start on something | Claims the issue |
| You find related work | Files it linked to current work |
| Work completes | Closes the issue |
| You ask about old work | Finds linked sessions for context |

## Example Conversation

```
You: "I need to refactor the auth module, but it depends on finishing the config changes first"

Agent: [Creates two issues, links them with a dependency]

You: "Let's work on the config changes"

Agent: [Claims that issue, works on it]

You: "That's done, what's next?"

Agent: [Closes config issue, shows auth refactor is now unblocked]
```

## Including in Your Own Bundle

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/robotdad/amplifier-bundle-beads@main
```

## Advanced Configuration

Override the tool config in your bundle for custom settings:

```yaml
tools:
  - module: tool-beads
    source: git+https://github.com/robotdad/amplifier-bundle-beads@main
    config:
      beads_dir: ~/my-custom-path/.beads  # Custom location
      hooks:
        ready:
          enabled: true       # Show ready work on session start
          max_issues: 10      # Max issues to display
        session_end:
          enabled: true       # Update issues when session ends
```

## Learn More

- [Beads documentation](https://github.com/steveyegge/beads)
- [Example workspace bundle](examples/workspace-bundle.md)

## License

MIT
