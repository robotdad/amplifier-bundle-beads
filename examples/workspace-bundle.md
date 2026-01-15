---
bundle:
  name: my-workspace
  version: 0.1.0
  description: Workspace with beads task tracking

includes:
  - bundle: git+https://github.com/robotdad/amplifier-bundle-beads@main
---

# My Workspace

Workspace with persistent task tracking via beads.

## Getting Started

The agent will:
- See ready work injected at session start
- Use `bd` commands via bash to track tasks
- File discovered work and close completed issues

## Customization

To use a different beads directory, override the hooks config:

```yaml
hooks:
  - module: beads-hooks
    source: git+https://github.com/robotdad/amplifier-bundle-beads@main
    config:
      beads_dir: ~/my-beads/.beads  # Your private beads location
```

To use per-project tracking instead, remove the `beads_dir` config and
the agent will run `bd init` in your project directory as needed.
