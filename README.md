# amplifier-bundle-beads

Persistent task tracking for Amplifier using the [beads](https://github.com/steveyegge/beads) `bd` CLI.

## What is Beads?

[Beads](https://github.com/steveyegge/beads) is a task tracker designed for AI agents. It tracks:
- What work is ready (no blockers)
- Dependencies between tasks
- Audit trails of changes

This bundle integrates beads with Amplifier by:
- Injecting ready work at session start (so agents know what's available)
- Providing periodic workflow reminders (to file discovered work and close completed issues)
- Including context that teaches agents how to use `bd` commands

**Agents use `bd` directly via bash** - no wrapper tool needed.

## Getting Started

**Step 1**: Register the beads bundle:

```bash
amplifier bundle add git+https://github.com/robotdad/amplifier-bundle-beads@main
```

**Step 2**: Create `.amplifier/bundle.md` in your workspace:

```bash
mkdir -p .amplifier
curl -o .amplifier/bundle.md https://raw.githubusercontent.com/robotdad/amplifier-bundle-beads/main/examples/workspace-bundle.md
```

**Step 3**: Register and use your workspace bundle:

```bash
amplifier bundle add ./.amplifier/bundle.md
amplifier bundle use my-workspace --project
```

**Step 4**: Start Amplifier:

```bash
amplifier
```

The `--project` flag saves the setting, so future sessions in this directory automatically use the bundle.

### What Happens on First Run

When you first start a session with this bundle:

1. The agent sees ready work (if any exists) injected into context
2. If `bd` isn't installed, the agent can install it via: `curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash`
3. If beads isn't initialized, the agent runs `bd init`

The agent uses `bd` commands directly via bash - the bundle provides context explaining how.

## Configuration

### Default: Centralized Tracking

By default, this bundle uses `~/Work/.beads` as a shared database across all your projects:
- All your work tracked in one place
- Cross-project dependencies work naturally
- Set `BEADS_DIR` environment variable to use a different location

### Alternative: Per-Project Tracking

To store issues with each project (in `.beads/`), override the hooks config to remove `beads_dir`:

```yaml
includes:
  - bundle: foundation
  - bundle: git+https://github.com/robotdad/amplifier-bundle-beads@main

hooks:
  - module: beads-hooks
    source: git+https://github.com/robotdad/amplifier-bundle-beads@main
    config:
      # No beads_dir = per-project .beads/ directories
      hooks:
        ready:
          enabled: true
```

## What the Agent Does

| Situation | Agent Action |
|-----------|--------------|
| Session starts | Sees ready work injected into context |
| Multi-session work identified | Creates issues with `bd create ...` |
| Starting on something | Claims with `bd update <id> --status in_progress` |
| Finds related work | Files with `bd create ... --discovered-from <parent>` |
| Work completes | Closes with `bd close <id> --reason "..."` |
| Session ends | Runs `bd sync` to persist changes |

## Hooks Provided

| Hook | Event | Purpose |
|------|-------|---------|
| `beads-ready` | `provider:request` | Injects ready work at session start |
| `beads-workflow-reminder` | `provider:request` | Periodic nudges about discovered work |
| `beads-workflow-tracker` | `tool:post` | Tracks bd usage to avoid over-reminding |
| `beads-session-end` | `session:end` | Marks session end on active issues |

## Including in Your Own Bundle

Beads is an add-on bundle - include it alongside your base bundle:

```yaml
includes:
  - bundle: foundation  # or amplifier-dev, exp-delegation, etc.
  - bundle: git+https://github.com/robotdad/amplifier-bundle-beads@main
```

## Advanced Configuration

Override hook config in your bundle:

```yaml
hooks:
  - module: beads-hooks
    source: git+https://github.com/robotdad/amplifier-bundle-beads@main
    config:
      beads_dir: ~/my-custom-path/.beads
      hooks:
        ready:
          enabled: true
          max_issues: 10
        session_end:
          enabled: true
        workflow_reminder:
          enabled: true
          reminder_interval: 8  # Tool calls between reminders
```

## Learn More

- [Beads documentation](https://github.com/steveyegge/beads)
- [Example workspace bundle](examples/workspace-bundle.md)

## License

MIT
