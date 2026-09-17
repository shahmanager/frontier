# Frontier

**Build discipline for AI coding — one stdlib Python file.** Stops AI agents from repeating the
same 5 failures (bloated context, no proof, stale reads, colliding parallel edits, chat loops) with
file-based mechanisms you can see and test — no daemon, no DB, no server.

![frontier](assets/frontier.svg)

> Severity is honest: read `## 80% of AI failures` first. Then `## When to use what`.
> `## Proof` shows the self-test that makes all of this verifiable.

[![Python](https://img.shields.io/badge/python-3.9%2B-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Deps](https://img.shields.io/badge/deps-stdlib%20only-green)](https://docs.python.org/3/library/)
[![Platform](https://img.shields.io/badge/os-win%20%7C%20mac%20%7C%20linux-blue)]()
[![CI](https://github.com/shahmanager/frontier/actions/workflows/frontier.yml/badge.svg)](https://github.com/shahmanager/frontier/actions)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Core](https://img.shields.io/badge/core-1%20file-important)](scripts/frontier.py)
[![Tests](https://img.shields.io/badge/selftest-24%20checks-success)](scripts/frontier.py)
[![Bench](https://img.shields.io/badge/compact-keeps%204%25%20context-8b5cf6)](scripts/frontier.py#L)

---

## Who this is for (and who it's not)

| You are… | Frontier helps | You need it |
|---|---|---|
| Solo dev vibe-coding with an AI agent | Keep context correct, force proof, stop re-committing the same mistake | ✅ every task |
| Running 2-5 agents on one repo (human = orchestrator) | File-based leases: parallel-safe work, no collisions | ✅ required |
| Building a CI gate that agents must pass | `validate` is read-only, prints "PROOF" gate — call it in CI | ✅ one line |
| Building your own memory/orchestration infra | Don't use Frontier's lightweight layer; bring your own (deferred tools) | ❌ different job |

## 80% of AI failures (the honest why)

Agents fail the same ways on every codebase. Frontier's whole point is: **each failure gets one
cheap mechanism, and that mechanism is provable.** This table is the pitch — everything below it
exists to make these rows true.

| # | Failure | Mechanism that fixes it |
|---|---|---|
| 1 | **Context bloat / recency bias** — agent only "remembers" the last 20 lines, and a `compact` that keeps newest-first just amplifies noise | `compact`: scores blocks by keyword overlap with the **task file**, keeps file order on ties — **never newest-first** |
| 2 | **No proof** — agent says "done", but nothing verified on the merge SHA | `evidence <task> -- pytest …` binds **exit code + git SHA** to a receipt; `validate` **blocks** any `status: ready` task without a fresh one |
| 3 | **Stale reads in parallel work** — agent A read `src/x.ts`, agent B edited it, A keeps writing to a ghost | `drift`: fingerprint at lease-acquire; exit 1 when scope files moved under you → re-read before writing |
| 4 | **Colliding parallel edits** | `lease acquire T AGENT "src/auth/*"` — overlapping scope → **second agent blocked** |
| 5 | **Infinite chat loops / no stopping rule** | `lease release` auto-broadcasts `done`; `lease noop` proves liveness — peers stop waiting |
| 6 | **Repeating known mistakes** | `recall "stampede cache"` pulls past `LEARNINGS.md` lines before you plan |
| 7 | **Rubber-stamp reviews** | `review` prints a diff-risk checklist (big diff / deps / migration / secrets / no tests) a real reviewer uses |
| 8 | **Wrong skill / tool loaded** | `suggest "<task text>"` matches registry triggers → loads the right skill |
| 9 | **Cold resume after `/clear`** | `resume <agent>`: leases + signals + broadcasts still on disk — context rebuilds in one command |
| 10 | **Over-engineering** | `references/ladder.md`: 7-rung minimal-diff reflex, nothing speculative |
| 11 | **Rambling output** | `references/output.md`: code first, ≤3 lines after (caveman-lite) |
| 12 | **Forgotten handoff format** | `handoff TASK.md` prints STATE/CHANGED/PROOF/NEXT/RISKS with real git SHA |

## When to use what (the actual workflow)

### Scenario A — solo agent, one task (everyday)

```bash
# 1. BEFORE coding — plan + lease + knowns
python scripts/frontier.py suggest "fix cart total overflow"     # which skills to load
python scripts/frontier.py lease acquire CART-9 me "src/cart/*" "tests/cart/*"
python scripts/frontier.py recall "cart total overflow"          # past mistakes?
python scripts/frontier.py compact memory/latest.md memory/compacted.md docs/TASKS/CART-9.md

# 2. DURING — read-down, then one guardrail before every write
# ... read AGENTS.md -> task -> ctx symbols -> entry/test -> target+callers (skip verbose unless tracing)
python scripts/frontier.py drift CART-9 me                       # exit 1 = someone moved scope files; re-read

# 3. DONE — prove + gate + report
python scripts/frontier.py evidence CART-9 -- pytest tests/cart   # exit-0 bound to SHA
python scripts/frontier.py validate                               # blocks if proof missing/stale
python scripts/frontier.py review                                 # risk checklist for the human
python scripts/frontier.py lease release CART-9 me                # broadcasts done
```

That's it. Five commands, zero servers, all state visible in `.agents/`.

### Scenario B — human orchestrates N agents on one repo

```bash
# human: define scopes, agents work in parallel (same task, disjoint globs)
python scripts/frontier.py lease acquire AUTH-1 agent-1 "src/auth/*" "tests/auth/*"
python scripts/frontier.py lease acquire AUTH-1 agent-2 "docs/*" "openapi/*"   # OK: disjoint

# collisions? an agent wanting src/auth/* gets blocked + holder name
# hand off, escalate, halt:
python scripts/frontier.py lease signal  AUTH-1 agent-1 agent-2 contracts_ready "v2 final"
python scripts/frontier.py lease lock    AUTH-1 agent-1   # shared-file mutex ... unlock
python scripts/frontier.py lease escalate AUTH-1 agent-2 "need clean reviewer"   # stuck
python scripts/frontier.py lease noop     AUTH-1 agent-1   # liveness, ends chat loops

# merge gate is the same as solo: evidence + validate, then release
```

### Scenario C — you (or CI) gate a merge

`validate` is **read-only** — safe in CI. Run the two lines in `.github/workflows/frontier.yml`
and a PR can't land with "ready" but unproven.

### When NOT to use Frontier commands

- **`lease`**: skip for single-threaded solo tasks — it's overhead until you have 2+ writers.
- **`compact`**: skip for small memory files (it's a no-op >300 lines cap). Run it when memory grows.
- **`recall`**: tier-0 heuristic. If you need semantic retrieval → bring claude-mem/agentmemory (never bundled here).
- **`ctx`**: needs `codegraph` installed (optional). Prints `SKIP` cleanly otherwise — never blocks you.

## How `suggest` + deferred tools actually work (the decision layer)

Frontier is a **spine, not a tool host**. A "skill" in your setup is a *trigger*:

```json
// .agents/skills/registry.json — word patterns -> skill to load
{ "name": "embedded-systems",
  "trigger": "firmware|rtos|bare.?metal|stm32|esp32|mcu|interrupt|dma" }
```

```bash
python scripts/frontier.py suggest "ESP32 firmware watchdog hung"
# -> embedded-systems        <- loads the real hardware skill, not Frontier
```

`defer` = Frontier *reads their signals, never replaces their job*:

| Capability | External tool | Frontier's hook (deferred, minimal) |
|---|---|---|
| Tier-1+ memory | claude-mem / agentmemory | `recall` = tier-0 only (5% of memory, no server) |
| Semantic indexing | codegraph | `ctx` wraps it, SKIPs if absent |
| Orchestration (spawn/queue/retry) | Task / Bureau / STORM | leases are the lock protocol **underneath** |
| Security scanning | gitleaks / trivy | `validate` checks a few secret regexes only |
| Test engines | pytest / vitest / cargo | `evidence` consumes their exit code + SHA |

So Frontier **never becomes the thing you outgrow** — it's the discipline layer that stays, while
you slot in real tools when the need outgrows its tier.

## SE practices covered

| SE practice | Frontier mechanism |
|---|---|
| Code review | `review` checklist + human is always the reviewer (never self-merge) |
| Test-driven regression | ladder: regress test first, `evidence` binds it to SHA |
| Context isolation | read-down order (seek.md) + tiered context budget |
| Concurrency control | file-based leases (optimistic, stale-view drift) |
| Continuous verification | CI `validate` gate, exit-code-proofed |
| Known-issue memory | `LEARNINGS.md` + `recall` |
| Minimal diff / grep-before-edit | ladder 7 rungs, root-cause rule |
| Secret hygiene | `validate` secret scan; git guardrails (§13) |
| **Locked/limits**: Frontier *guides*, never *run* tests, *execute* migrations, or *scan* your whole repo — those stay with real tools | |

## Commands (17)

```
init | compact | lease | validate | suggest | ctx | doctor | selftest | bench |
handoff | drift | evidence | recall | resume | review
```

`lease`: `acquire --force --ttl | release | heartbeat | signal | escalate | noop | lock | unlock | status | list`

## Proof — 24-check self-test + real benchmarks

`selftest` runs in a temp dir, exit 0 only if every check passes. It's the CI too:

```bash
PASS init, compact keep/drop, acquire, parallel disjoint, overlap blocked,
force coexistence, heartbeat, signal, escalate, noop, lock/unlock,
drift detects, recall finds, resume signals, review degrades, bench runs,
evidence receipt, ready-gate blocks, validate green.   (24 checks)
```

`bench` — measured on this machine, real numbers (reproduce with `python scripts/frontier.py bench`):

| bench | what was measured | result | ms avg |
|---|---|---|---|
| compact | 159-line log → 7 relevant lines | **4% kept** | ~1 |
| recall | tier-0 retrieval over LEARNINGS+memory | top-5 hits | ~3 |
| lease acquire+fp | sha1 fingerprint of 200 files | 1 lease | ~80 |
| drift | re-fingerprint 200 files + compare | clean / exit1 | ~90 |

Figures are single-run medians from this machine (`python scripts/frontier.py bench`); lease/drift
cost scales with scope file count — that's the fingerprint trade you buy stale-read protection with.

That compact row is the pitch in numbers: **96% of stale context dropped, no recency bias, ~1 ms.**
No server needs to be warm, nothing to configure.

## Install (30s, no deps)

```bash
cd <your-repo>
python scripts/frontier.py init .     # scaffold: AGENTS.md, router, docs/, .agents/, memory/
python scripts/frontier.py validate   # expect: frontier handoff OK
```

Or install as a CLI (optional):

```bash
pip install .          # or: uvx frontier-ai
frontier.py selftest   # 24-check proof, repo-wide
```

Agent auto-load: drop `SKILL.md` where your agent reads AGENTS.md, or paste `references/INSTALL.md` §2.

## Documentation

| Doc | What |
|---|---|
| [`SKILL.md`](SKILL.md) | the discipline: 14 sections — behavior, loop, output, context, memory, leases, toolbelt |
| [`references/INSTALL.md`](references/INSTALL.md) | paste-ready setup, agent prompt, migration map |
| [`references/seek.md`](references/seek.md) | read-down order before coding |
| [`references/ladder.md`](references/ladder.md) | minimal-diff ladder + debug loop + test-first |
| [`references/output.md`](references/output.md) | caveman-lite output |
| [`references/TASK.md`](references/TASK.md) | task/plan template |
| [`.agents/protocol/LEASE.md`](.agents/protocol/LEASE.md) | full multi-agent lease protocol |

## Compared to

| Tool | Scope | Frontier |
|---|---|---|
| claude-mem / agentmemory | tier-1+ memory server | tier-0 `recall`, no server; stays compatible, doesn't replace |
| CodeGraph | semantic navigation | `ctx` wraps it + `drift` stale-guard; SKIPs if absent |
| Task / Bureau / STORM | agent orchestration | leases = lock protocol underneath, compatible |
| agents.md / AGILE.md | static spec/router | scaffolds + gates + validates it |
| gitleaks / trivy | security scanning | `validate` checks a few regexes; real scanning deferred |

## Contributing

- Fix = code + `selftest` green + `validate` green (CI enforces both).
- New command ships its own selftest check. Stdlib only. Keep it lazy (delete prose > code).

## License

MIT. Influences: Karpathy (behavior), Cherny (loop), ponytail (ladder), caveman (output).