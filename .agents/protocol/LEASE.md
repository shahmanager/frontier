# Multi-Agent Lease Protocol (v3 — per-agent leases, `frontier.py`)

## Files

- `.agents/leases/<task>.<agent>.json` — `{agent, exp, scope[], fp}`, 5-min TTL
- `.agents/signals/<task>/<agent>.json` — direct `{type, payload, ts, from}`
- `.agents/signals/<task>/__<type>__.json` — broadcasts (`done`, `escalate`, `noop`)
- `.agents/sentinel/<task>.lock/owner.json` — `{agent, exp}` mutex

Same task + disjoint scopes run in parallel. Overlapping scopes block.

## Lease Lifecycle

1. **Acquire**: fail if a live lease on same task has overlapping scope (glob match). Stale (>TTL) ignored.
2. **Heartbeat**: refresh `exp` every ~30s. `LEASE_LOST` = re-acquire.
3. **Signal**: async handoff, non-blocking. Peer polls `status` or its signal file.
4. **Release**: delete own lease file, auto-broadcast `__done__` so polling peers stop (stopping rule).
5. **Escalate**: stuck → broadcast `__ESCALATE__` for human/router or clean-context reviewer.
6. **Noop**: idle agent pings `__noop__` to prove liveness and stop conversation loops.
7. **Lock**: mutex dir before writing a shared file. Stale lock (owner lease dead) is stolen with warning.

## Scope Examples

- `scope: ["src/auth/*", "docs/TASKS/AUTH-*.md"]` — owns auth slice
- `scope: ["*"]` — full repo (architect only)

## Usage in Task Frontmatter

```yaml
---
id: AUTH-001
status: planned
agent: agent-1
lease_scope: ["src/auth/*", "docs/TASKS/AUTH-*.md"]
symbol: connectToServer
component: auth-service
---
```

## Per-Agent Workflow

```bash
python scripts/frontier.py lease acquire AUTH-001 agent-1 "src/auth/*" "tests/auth/*"
python scripts/frontier.py lease heartbeat AUTH-001 agent-1   # bg loop, ~30s
python scripts/frontier.py lease signal AUTH-001 agent-1 agent-2 contracts_ready "API v2 final"
python scripts/frontier.py lease lock AUTH-001 agent-1        # ... write ... unlock
python scripts/frontier.py lease unlock AUTH-001 agent-1
python scripts/frontier.py lease release AUTH-001 agent-1
python scripts/frontier.py lease status AUTH-001  # list holders
```

## Parallel Work Example

```
Task: AUTH-001 (auth refactor)
├─ agent-1: lease_scope ["src/auth/*", "tests/auth/*"]
│   └─ writes: src/auth/login.ts, src/auth/token.ts
└─ agent-2: lease_scope ["docs/TASKS/AUTH-*.md", "openapi/auth.yaml"]
    └─ writes: docs/TASKS/AUTH-001.md, openapi/auth.yaml

Both run simultaneously. Leases prevent overlap. Signals coordinate handoffs.
```