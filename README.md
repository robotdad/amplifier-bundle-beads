# amplifier-bundle-beads

Beads integration for Amplifier - persistent, dependency-aware task tracking with session linking.

## What is Beads?

[Beads](https://github.com/steveyegge/beads) is a distributed, git-backed issue tracker designed for AI agents. It provides:

- **Dependency-aware task selection**: `bd ready` returns tasks with no open blockers
- **Git-native storage**: Issues stored in `.beads/`, versioned with your code
- **Hash-based IDs**: Collision-resistant IDs for parallel agent work
- **Fast queries**: ~10ms offline queries via embedded SQLite

## What This Bundle Adds

This bundle integrates beads with Amplifier's session model:

| Component | Description |
|-----------|-------------|
| **beads tool** | CLI wrapper with all bd operations as tool actions |
| **session linking** | Issues tagged with session IDs for follow-up questions |
| **lifecycle hooks** | Auto-inject ready work on session start, update issues on session end |
| **slash commands** | Shortcuts for common operations *(planned - when command bundling lands)* |
| **workflow skill** | Deep knowledge for complex multi-session work *(planned - when skill bundling lands)* |

## Prerequisites

The `bd` CLI (beads) is required. You can install it automatically or manually:

### Automatic Installation (Recommended)

Let the agent install it for you:
```
beads(operation='setup', action='install')
```

Or install and initialize in one step:
```
beads(operation='setup', action='both')
```

### Manual Installation

```bash
# Homebrew (macOS/Linux) - recommended
brew tap steveyegge/beads && brew install bd

# npm
npm install -g @beads/bd

# go install
go install github.com/steveyegge/beads/cmd/bd@latest

# Shell script
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
```

Verify installation:
```bash
bd version
```

See [beads installation docs](https://github.com/steveyegge/beads/blob/main/docs/INSTALLING.md) for more options.

## Installation

### Use the Bundle Directly

```bash
# Add the bundle
amplifier bundle add git+https://github.com/robotdad/amplifier-bundle-beads@main

# Use it
amplifier bundle use beads
```

### Include in Your Bundle

```yaml
---
bundle:
  name: my-bundle
  version: 1.0.0

includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/robotdad/amplifier-bundle-beads@main
---

# My Bundle

Your instructions here...
```

### Include Just the Behavior

```yaml
includes:
  - bundle: git+https://github.com/microsoft/amplifier-foundation@main
  - bundle: git+https://github.com/robotdad/amplifier-bundle-beads@main#subdirectory=behaviors/beads.yaml
```

## Configuration

### Centralized Tracking (Recommended)

Use a single beads database across all your projects:

```yaml
tools:
  - module: tool-beads
    source: git+https://github.com/robotdad/amplifier-bundle-beads@main
    config:
      beads_dir: ~/my-beads/.beads  # All projects share this database
      hooks:
        ready:
          enabled: true
        session_end:
          enabled: true
```

This approach:
- Keeps all your work in one place
- Works across multiple projects without per-repo setup
- Can be backed by a private git repo for sync/backup
- Lets the agent track cross-project work

### Per-Project Tracking

For project-specific issue tracking (traditional mode):

```bash
cd your-project
bd init
```

Issues are stored in `.beads/` within that project and committed with the code.

## Usage

### Tool Operations

| Operation | Description | Example |
|-----------|-------------|---------|
| `setup` | Install bd CLI and/or initialize beads | `beads(operation='setup', action='both')` |
| `status` | Check prerequisites and initialization | `beads(operation='status')` |
| `ready` | List tasks with no blockers | `beads(operation='ready')` |
| `show` | Show issue details | `beads(operation='show', issue_id='bd-a1b2')` |
| `create` | Create new issue | `beads(operation='create', title='...')` |
| `update` | Update issue | `beads(operation='update', issue_id='bd-a1b2', status='in_progress')` |
| `close` | Close issue | `beads(operation='close', issue_id='bd-a1b2', notes='Done')` |
| `claim` | Claim for session | `beads(operation='claim', issue_id='bd-a1b2')` |
| `discover` | File discovered work | `beads(operation='discover', title='...', parent_id='bd-a1b2')` |
| `list` | List all issues | `beads(operation='list', filter_status='open')` |
| `sessions` | Get linked sessions | `beads(operation='sessions', issue_id='bd-a1b2')` |

### Setup Actions

The `setup` operation supports these actions:

| Action | Description |
|--------|-------------|
| `install` | Download and install the bd CLI |
| `init` | Run `bd init` in current directory |
| `both` | Install bd then initialize (default if bd not installed) |

### Session Linking

Issues are automatically tagged with session IDs when you create, claim, close, or discover work. This enables:

1. **Find sessions for an issue**:
   ```
   beads(operation='sessions', issue_id='bd-a1b2')
   → {linked_sessions: ['abc123', 'def456']}
   ```

2. **Revive context for follow-up**:
   ```bash
   amplifier session resume abc123
   ```

3. **Ask questions with full history**:
   The resumed session has complete context from when the work was done.

### Automatic Context Injection

On session start, if there are ready tasks, they're automatically injected into the agent's context:

```
## Ready Work (beads)

Tasks with no open blockers, ready to work on:

- **bd-a1b2**: Implement caching layer [high]
- **bd-c3d4**: Fix parser edge case

Use `beads(operation='claim', issue_id='...')` to claim a task.
```

## Slash Commands (Future)

When command bundling support lands, these will be available:

| Command | Description |
|---------|-------------|
| `/bd-ready` | Show ready work |
| `/bd-claim <id>` | Claim an issue |
| `/bd-done <id> [summary]` | Close an issue |
| `/bd-ask <id> <question>` | Ask about an issue (revives session) |
| `/bd-discover <parent-id> <title>` | File discovered work |

## Workflow Skill (Future)

When skill bundling support lands, load the `beads-workflow` skill for deep knowledge about:
- Dependency patterns (when to use blocks vs discovered-from)
- Landing the plane protocol
- Session linking strategies
- Multi-agent coordination

## Architecture

```
amplifier-bundle-beads/
├── bundle.md                    # Main bundle definition
├── amplifier_module_tool_beads/
│   ├── tool.py                  # beads tool (CLI wrapper + hook registration)
│   └── hooks.py                 # Session lifecycle hooks
├── behaviors/
│   └── beads.yaml               # Includable behavior
├── context/
│   └── beads-instructions.md    # Agent instructions
├── commands/                    # Slash commands (planned)
└── skills/
    └── beads-workflow/          # Workflow skill (planned)
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Type checking
uv run pyright

# Linting
uv run ruff check .
uv run ruff format .
```

## How It Works

### Tool Module

The tool wraps the `bd` CLI, providing:
- All standard bd operations as tool actions
- Automatic session ID tagging on create/claim/close/discover
- Graceful handling when bd is not installed (shows install instructions)
- JSON parsing of bd output for structured responses

### Hook Module

Hooks are registered when the tool mounts, subscribing to session lifecycle events:
- **session:start** (`beads-ready` hook): Runs `bd ready` and injects results into context
- **session:end** (`beads-session-end` hook): Updates claimed issues with session-end marker

Configure via bundle config:
```yaml
tools:
  - module: tool-beads
    source: git+https://github.com/robotdad/amplifier-bundle-beads@main
    config:
      # Optional: centralized beads directory (omit for per-project .beads/)
      beads_dir: ~/my-beads/.beads
      hooks:
        ready:
          enabled: true      # Inject ready tasks on session start
          max_issues: 10     # Max issues to show
        session_end:
          enabled: true      # Update issues on session end
```

### Session Linking

Session IDs are stored in issue notes using tags:
- `[amplifier:session:xxx]` - Created in session
- `[amplifier:claimed-by-session:xxx]` - Claimed in session
- `[amplifier:closed-in-session:xxx]` - Closed in session
- `[amplifier:discovered-in-session:xxx]` - Discovered in session

The `sessions` operation parses these tags to return linked session IDs.

## Contributing

See [CONTRIBUTING.md](https://github.com/microsoft/amplifier/blob/main/CONTRIBUTING.md) for guidelines.

## License

MIT
