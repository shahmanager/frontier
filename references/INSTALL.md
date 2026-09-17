# INSTALL — 1-shot Frontier setup (win/mac/linux, python stdlib only)

## 0. Prereqs

- Python 3.9+ (`python --version`). No jq, no GNU date, no extra deps.

## 1. Scaffold any repo (30s)

```bash
cd <your-repo>
python <path-to-frontier>/scripts/frontier.py init .
# fills AGENTS.md [brackets], then:
python scripts/frontier.py validate   # expect: frontier handoff OK
```

`init` never overwrites existing files. Also run once per machine (optional):

```bash
npm i -g @codegraph/cli && codegraph init   # per-repo semantic index
```

## 2. Start a task (paste into agent prompt)

```markdown
Load skill `frontier`. Task text: <paste task>.
1. `python scripts/frontier.py suggest <task text>` -> load listed skills.
2. Copy `docs/TASKS/_TEMPLATE.md` -> `docs/TASKS/<ID>.md`, fill frontmatter (id/status/agent/lease_scope/symbol/component).
3. `python scripts/frontier.py lease acquire <ID> <agent> <scope...>`
4. `python scripts/frontier.py ctx <symbol>` (SKIP line if codegraph absent).
5. `python scripts/frontier.py compact memory/<latest>.md memory/compacted.md docs/TASKS/<ID>.md`
6. Read only (read-down order, `references/seek.md`): AGENTS.md -> task file -> memory/compacted.md -> `ctx` symbols -> entry + real test cmd -> target + callers. Then code per ladder (`references/ladder.md`); bug fixes ship the regress test first (`evidence` binds it).
```

## 3. Parallel agents (same task, disjoint scopes)

```bash
python scripts/frontier.py lease acquire AUTH-001 agent-1 "src/auth/*" "tests/auth/*"
python scripts/frontier.py lease acquire AUTH-001 agent-2 "docs/*" "openapi/*"
# heartbeat in bg every ~30s; signal handoffs; lock shared files:
python scripts/frontier.py lease signal AUTH-001 agent-1 agent-2 contracts_ready "AuthAPI v2 final"
python scripts/frontier.py lease lock AUTH-001 agent-1   # ... write ... unlock
python scripts/frontier.py lease release AUTH-001 agent-1
```

## 4. Finish

```bash
python scripts/frontier.py validate   # gate: frontmatter, line budget, secrets
```

## 5. CI (`.github/workflows/frontier.yml`)

```yaml
- run: python scripts/frontier.py selftest   # prove the tooling
- run: python scripts/frontier.py validate
```

## 6. Migrate from v2 (bash scripts removed)

| v2 | v3 |
|----|----|
| `scripts/validate-handoff.sh` | `python scripts/frontier.py validate` |
| `scripts/compact-context.sh IN OUT ID` | `python scripts/frontier.py compact IN OUT docs/TASKS/ID.md` |
| `.agents/protocol/lease.sh acquire ...` | `python scripts/frontier.py lease acquire ...` |
| `sentinel-lock / sentinel-unlock` | `lease lock / lease unlock` |
| `codegraph explore ...` (+manual refresh hook) | `python scripts/frontier.py ctx ...` |

## 7. Toolbelt

`suggest` (skill match) · `recall` (past learnings, run before planning) ·
`ctx` (codegraph w/ SKIP) · `handoff` (skeleton + SHA) ·
`drift` (stale-view check, run before writing) ·
`evidence` (bind proof to SHA, run instead of bare test cmds) ·
`review` (diff-risk checklist for the reviewer) ·
`resume` (leases + signals + broadcasts after `/clear`) ·
`doctor` (machine check) · `selftest` (23 checks, run after every skill upgrade).

Docs: `seek.md` (read-down order) · `ladder.md` (7-rung + debug loop + test-first) ·
`output.md` (caveman-lite) · `LEASE.md` (multi-agent protocol) · SKILL.md §13 (git guardrails) · SKILL.md §14 (deferred tools).
