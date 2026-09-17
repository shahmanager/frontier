# Frontier

**One-shot build discipline for AI coding.** One stdlib Python file that turns any repo into a
correct-context, verified, parallel-safe workplace for AI agents — human as orchestrator.

![frontier](assets/frontier.svg)

> **[ Why Frontier? ] → [ Install ] → [ Quickstart ] → [ Commands ] → [ Compared to ]**

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Deps](https://img.shields.io/badge/deps-stdlib%20only-green)](https://docs.python.org/3/library/)
[![Platform](https://img.shields.io/badge/os-win%20%7C%20mac%20%7C%20linux-blue)]()
[![CI](https://github.com/shahmanager/frontier/actions/workflows/frontier.yml/badge.svg)](https://github.com/shahmanager/frontier/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Lines](https://img.shields.io/badge/core-1%20file-important)](scripts/frontier.py)
[![Tests](https://img.shields.io/badge/selftest-23%20checks-success)](scripts/frontier.py)

---

## Why Frontier

AI agents fail on large codebases the **same ways, every time**: bloated context, recency bias,
no verification, stale reads in parallel work, infinite chat loops. Frontier fixes each failure
with **one cheap mechanism** — and proves it with a self-test before you trust it.

| Failure | Mechanism |
|---|---|
| Context bloat | Router `AGENTS.md` <60 lines · relevance compaction, **never newest-first** |
| Over-engineering | 7-rung minimal-diff ladder → `references/ladder.md` |
| Rambling output | Code first, ≤3 lines after → `references/output.md` |
| No proof of work | `validate` gate + `evidence` receipts bound to **git SHA** (`ready` needs fresh proof) |
| Stale reads in parallel work | `drift`: scope fingerprint at acquire, exit 1 when files moved under you |
| Repeating known mistakes | `recall`: tier-0 retrieval over `LEARNINGS.md` before planning |
| Rubber-stamp reviews | `review`: diff-risk checklist (large diff, deps, migrations, secrets, no tests) |
| Cold-start / `/clear` friction | `resume`: rebuild leases + signals + broadcasts; `seek.md` read-down order |
| Agent chat loops, no stop rule | `lease release` auto-broadcasts `done` · `lease noop` pings liveness |
| Stuck with no path up | `lease escalate` broadcasts to human / router / clean reviewer |
| Parallel answer collisions | File-based leases: disjoint scopes run together, overlaps block |
| Wrong skill loaded | `suggest`: match task text against trigger registry |
| Forgotten handoff format | `handoff`: prints skeleton with real git SHA |

## Install (30 seconds, no deps)

```bash
# any repo, any platform (win/mac/linux — stdlib only, no jq, no GNU tools)
cd <your-repo>
python scripts/frontier.py init .     # copy frontier.py anywhere, or use the CLI below
python scripts/frontier.py validate   # expect: frontier handoff OK
```

Or install as a repo-wide CLI (optional — the skill loop doesn't need it):

```bash
pip install .          # or: uvx frontier-ai
frontier.py selftest   # 23-check end-to-end proof, exit 0
```

Want **auto-load in your agent**? Paste `references/INSTALL.md` §2 into your agent prompt or
drop `SKILL.md` where your agent reads AGENTS.md. Done.

## Quickstart — one human, N agents

```bash
# 1. Human = orchestrator. Agent starts a task:
python scripts/frontier.py suggest "auth refactor CORS"
python scripts/frontier.py lease acquire AUTH-001 agent-1 "src/auth/*" "tests/auth/*"

# 2. Two agents, disjoint scopes, same task -> run in parallel:
python scripts/frontier.py lease acquire AUTH-001 agent-2 "docs/*" "openapi/*"

# 3. Hand off, lock a shared file, heartbeat, escalate, stop:
python scripts/frontier.py lease signal  AUTH-001 agent-1 agent-2 contracts_ready "AuthAPI v2 final"
python scripts/frontier.py lease lock    AUTH-001 agent-1   # ... write ... unlock
python scripts/frontier.py lease escalate AUTH-001 agent-1 "socket leak, need clean reviewer"  # stuck
python scripts/frontier.py lease noop     AUTH-001 agent-1   # still alive, done producing

# 4. Prove, gate, merge:
python scripts/frontier.py evidence AUTH-001 -- pytest tests/auth
python scripts/frontier.py validate              # blocks unless fresh exit-0 on this SHA
python scripts/frontier.py lease release AUTH-001 agent-1   # broadcasts done -> peers stop
```

## Commands

```
init | suggest | recall | compact | ctx | lease | drift | evidence | review |
resume | handoff | validate | doctor | selftest
```

`lease` subcommands: `acquire --force --ttl | release | heartbeat | signal |
escalate | noop | lock | unlock | status | list`

### Discipline that ships with it

- **Ladder** — minimal-diff reflex: YAGNI → reuse → stdlib → native → deps → one line → minimum code (`references/ladder.md`)
- **Debug loop** — reproduce → minimize → bisect → fix at shared node → regress test *first* (red→green)
- **Seek** — read-down order before coding (router → task → symbols → entry/test → target + all callers)
- **Git guardrails** — no commit without inspect; amend/PR/push only on explicit human request; one slice one branch; never force-push after push
- **Output** — code first, then ≤3 lines; full prose on security/destructive steps only

## Compared to

| Tool | Scope | Frontier |
|---|---|---|
| claude-mem / agentmemory | tier-1+ memory server | tier-0 `recall` (no server, stdlib); sees their signals, doesn't replace them |
| CodeGraph | semantic symbol nav | wrapped by `ctx`, SKIPs gracefully when absent; adds `drift` stale-guard |
| Task / Bureau / STORM | agent orchestration (execution) | leases are the **lock protocol underneath**; stays compatible |
| agents.md / AGILE.md | static spec/router | scaffolds + gates + validates it; not just a doc |
| gitleaks / trivy | security scanning | `validate` checks a few secret patterns; real scanning deferred to tools |
| pytest / vitest / cargo | test engines | `evidence` consumes their exit-0 + SHA |

**Rule:** absorb *opinions* (methods, text, cheap), defer *tools* (install, compute, servers).
Frontier is a discipline spine, not a tool host — see SKILL.md §14.

## Proof

`python scripts/frontier.py selftest` — real run, exit 0, and it is also your CI:

```bash
selftest OK: init, compact keep/drop, acquire, parallel disjoint, overlap blocked,
force coexistence, heartbeat, signal, escalate, noop, lock/unlock, drift detects,
recall finds, resume signals, review degrades, evidence receipt, ready-gate blocks,
validate green.   (23 checks)
```

CI is one workflow file, already included: `.github/workflows/frontier.yml`.

## Documentation

| Doc | What |
|---|---|
| [`SKILL.md`](SKILL.md) | the discipline: 14 sections, behavior/loop/output/leases/toolbelt |
| [`references/INSTALL.md`](references/INSTALL.md) | paste-ready setup + agent prompt + migration map |
| [`references/TASK.md`](references/TASK.md) | task/plan template |
| [`references/seek.md`](references/seek.md) | read-down order before coding |
| [`references/ladder.md`](references/ladder.md) | minimal-diff ladder + debug loop + test-first |
| [`references/output.md`](references/output.md) | caveman-lite output rules |
| [`.agents/protocol/LEASE.md`](.agents/protocol/LEASE.md) | full multi-agent lease protocol |

## Contributing

- Fix = code + `selftest` still green + `validate` green (CI enforces both).
- New command must ship its own selftest check (see `selftest` in `scripts/frontier.py`).
- No new dependencies — stdlib only, by law.
- Keep it lazy: if the change adds more prose than code, delete the prose.

## License

MIT. Influences: Karpathy (behavior), Cherny (loop), ponytail (ladder), caveman (output).