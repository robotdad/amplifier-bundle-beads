---
bundle:
  name: my-workspace
  version: 0.1.0
  description: Workspace with beads task tracking

includes:
  # beads bundle already includes foundation, so we only need this
  - bundle: git+https://github.com/robotdad/amplifier-bundle-beads@main
---

# My Workspace

Workspace with persistent task tracking via beads.

## Getting Started

The agent will:
- Check for ready work at session start
- Track multi-session tasks automatically
- Link sessions to issues for follow-up questions

## Customization

To use a centralized beads database (recommended for multi-project work),
override the tool config:

```yaml
tools:
  - module: tool-beads
    source: git+https://github.com/robotdad/amplifier-bundle-beads@main
    config:
      beads_dir: ~/my-beads/.beads  # Your private beads location
```

To use per-project tracking instead, remove the `beads_dir` config and
run `bd init` in your project directory.
