---
name: codegraph
description: Local CodeGraph MCP for semantic navigation. Use for symbol tracing, call paths, dependency analysis.
---

# CodeGraph Local

## Setup (once per repo)

```bash
codegraph init          # creates .codegraph/
codegraph serve &       # starts MCP on stdio
```

## Usage in Frontier loop

```bash
# In task file, before coding:
codegraph explore "<symbol or question>" > .codegraph/ctx.md
# Read .codegraph/ctx.md as context
```

## Auto-refresh hook (add to .codegraph/refresh.sh)

```bash
#!/usr/bin/env bash
codegraph index --incremental
codegraph explore "$(grep '^symbol:' docs/TASKS/current.md | cut -d' ' -f2-)" > .codegraph/ctx.md
```