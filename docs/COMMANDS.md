# Frontier Command Reference

Every command, its exact syntax, what it does, when to run it, and real output.

All commands run from the repo root. None of them is a daemon — every one reads or
writes plain files under `.agents/` and prints to stdout. Exit code `0` = success,
`1` = check failed (blocks the step), `2` = precondition missing.

- [`init`](#init) · [`suggest`](#suggest) · [`recall`](#recall) · [`compact`](#compact) ·
  [`ctx`](#ctx) · [`lease`](#lease) · [`drift`](#drift) · [`evidence`](#evidence) ·
  [`validate`](#validate) · [`review`](#review) · [`resume`](#resume) · [`handoff`](#handoff) ·
  [`doctor`](#doctor) · [`selftest`](#selftest) · [`bench`](#bench)

---

## init

Scaffold the laptop-protocol into a repo: router `AGENTS.md`, task/learnings/goals
templates, the multi-agent `.agents/` layout, a symlinked `CLAUDE.md`, and `.gitignore`
entries for the ephemeral state. **Never overwrites an existing file.**

```bash
python scripts/frontier.py init [target_dir]     # default: current directory
```

Creates (9 files + dirs):

```
AGENTS.md                   router: boundaries, gotchas, build/test commands
CLAUDE.md                   same router for Claude Code
docs/GOALS.md               measurable outcomes, done-means
docs/CONTEXT.md             stack, boundaries, known constraints, gotchas
docs/TASKS/_TEMPLATE.md     task/plan template (frontmatter + PROOF)
docs/LEARNINGS.md           append-only mistake log
.agents/protocol/LEASE.md   multi-agent lease spec
.agents/skills/registry.json  task-keyword -> skill trigger map
.agents/skills/codegraph/SKILL.md  optional semantic-nav hook
memory/  .agents/{leases,signals,sentinel,evidence}/  .codegraph/
```

Real output:

```
frontier init OK: 9 created, 0 skipped -> .
Next: fill AGENTS.md [brackets], run `codegraph init` if available.
```

Run once per repo, or once per machine and copy the files. Idempotent.

---

## suggest

Decide **which skills to load for a task** by matching the task text against each
skill's trigger regex in `.agents/skills/registry.json`. Prints `NONE` when nothing
matches — that's a valid answer (load no skill).

```bash
python scripts/frontier.py suggest <task text...>
python scripts/frontier.py suggest "ESP32 firmware watchdog keeps hanging"
```

Real output:

```
embedded-systems
load skill: embedded-systems
```

Run at task start, before planning. If your agent framework auto-loads skills by
description, this is what tells it which other skill is relevant — Frontier itself
is one entry in that same registry with trigger `new task|multi-agent|lease|handoff|AGEN`.

---

## recall

Tier-0 memory: retrieve the **top-5 most relevant lines** from `docs/LEARNINGS.md`
and `memory/*.md` by word-overlap with your query. Stopword-filtered, case-insensitive,
scores are printed in `[n]`.

```bash
python scripts/frontier.py recall <words...>
python scripts/frontier.py recall "cart total overflow rounding"
```

Real output:

```
[2] docs\LEARNINGS.md:3: 2026-05-12 floating cents in total -> round at edge, not accumulate
[1] memory\2026-05-14.md:7: cart total overflow reproduced with 3 items + discount
```

```
NONE                                        # when nothing matches
```

Run before planning on any task you suspect you've hit before. It's a heuristic —
if you need semantic similarity, bring a tier-1+ memory server (`recall` stays
compatible; see FAQ).

---

## compact

Context compaction **without recency bias**. Scores text blocks in `IN` by keyword
overlap with the keys in `TASK_FILE` (`symbol:` / `component:` / `module:` / `file:`),
keeps only scoring blocks, ties keep **file order** (never newest-first), caps at
300 lines. Writes result to `OUT`.

```bash
python scripts/frontier.py compact <in.md> <out.md> <task-file>
python scripts/frontier.py compact memory/2026-05-14.md memory/compacted.md docs/TASKS/CART-9.md
```

Real output:

```
compact OK: 4/37 blocks kept -> memory/compacted.md
WARN: no symbol/component/module/file keys in task; keeping file order, capped.
```

Run when memory logs grow: after task end, or before a fresh slice.

---

## ctx

Run CodeGraph semantic exploration on one symbol/question and write the result to
`.codegraph/ctx.md`. **Degrades gracefully**: if `codegraph` isn't installed it prints
one line and exits 0 — it never blocks your flow.

```bash
python scripts/frontier.py ctx <symbol...>
python scripts/frontier.py ctx "RequestHandler.handle"
```

Real output:

```
ctx OK (42 lines)                          # codegraph installed
SKIP: codegraph not installed (one line).  # codegraph absent
```

Run during read-down, before editing a symbol that crosses files. Requires the
optional `codegraph` index (`codegraph init` per repo).

---

## lease

Multi-agent coordination: **file-based, scope-split leases**. Two agents on the same
task with **disjoint glob scopes run in parallel**; an agent whose scope **overlaps
a live lease is blocked** (exit 1) with the holder's name. No server, no DB — leases
are JSON files in `.agents/leases/` with a 5-minute TTL.

```bash
python scripts/frontier.py lease <command> [task] [agent] [args...]
python scripts/frontier.py lease acquire --force --ttl 900 TASK AGENT "src/auth/**" "tests/auth/**"
```

| Subcommand | Syntax | What it does | Output |
|---|---|---|---|
| `acquire` | `lease acquire T A S...` | Claim task `T` scope `S...` for agent `A`; blocked if live lease overlaps. `--force` allows coexistence with a WARN. `--ttl N` overrides 300s default | `ACQUIRED` / `LEASE_HELD by <agent>` (exit 1) / `WARN: overlapping` |
| `release` | `lease release T A` | Delete lease + **broadcast `done`** so polling peers stop | `RELEASED` |
| `heartbeat` | `lease heartbeat T A` | Refresh lease expiry (~every 30s in bg). `LEASE_LOST` = re-acquire | `OK` / `LEASE_LOST` (exit 1) |
| `signal` | `lease signal T FROM TO TYPE MSG` | Async handoff to a peer (non-blocking) | `SENT` |
| `escalate` | `lease escalate T A REASON` | Broadcast **stuck** to human/router/clean reviewer | `ESCALATED` |
| `noop` | `lease noop T A` | Liveness ping — proves agent alive, ends chat loops | `NOOP_SENT` |
| `lock` | `lease lock T A` | Save-and-release mutex before writing a shared file; steals stale locks | `LOCKED_OK` / `LOCKED` (held) |
| `unlock` | `lease unlock T A` | Release the mutex | `UNLOCKED` |
| `status` | `lease status T` | Show all leases for task `T` (expiry, scope, fingerprint) | `T.a1 <json>` / `no leases` |
| `list` | `lease list` | All leases repo-wide | `T.a1 ALIVE` / `T.a1 EXPIRED` |

Parallel example (2 agents, disjoint scopes):

```bash
python scripts/frontier.py lease acquire AUTH-1 agent-1 "src/auth/**" "tests/auth/**"   # ACQUIRED
python scripts/frontier.py lease acquire AUTH-1 agent-2 "docs/**" "openapi/**"          # ACQUIRED (disjoint)
python scripts/frontier.py lease acquire AUTH-1 agent-3 "src/auth/**"                   # LEASE_HELD by agent-1 (exit 1)
```

---

## drift

**Stale-view detector.** At `acquire`, Frontier fingerprints every file in your scope.
`drift` re-fingerprints and exits `1` if anything changed, moved, or appeared — so you
re-read before writing instead of clobbering a peer's work.

```bash
python scripts/frontier.py drift <task> <agent>
```

Real output:

```
CLEAN                                # exit 0, keep going
N src/app.ts                         # new file (exit 1: re-read first)
M src/auth/token.go                  # modified (exit 1)
D src/legacy.ts                      # deleted (exit 1)
drift found: re-read files before writing
NO_LEASE: acquire first              # exit 2
NO_BASELINE: re-acquire lease        # exit 2
```

Run **before every write** during a multi-agent session. In solo sessions it still
catches edits by other humans/tools.

---

## evidence

**Bind proof to the current git SHA.** Runs your test command, records `{exit, sha}`
in `.agents/evidence/<task>.<n>.json`, then **exits with the test's exit code**. This
is what makes `validate`'s ready-gate meaningfully "proven" — a receipt is only fresh
if it was recorded against the current HEAD.

```bash
python scripts/frontier.py evidence <task> -- <test command...>
python scripts/frontier.py evidence CART-9 -- pytest tests/cart -q
```

Real output:

```
evidence CART-9.3: exit=0 sha=3fa9c1e2b7a0   # exit 0 => step green
evidence CART-9.3: exit=1 sha=3fa9c1e2b7a0   # test failed => evidence records the FAILURE
```

Use it **instead of running bare test commands at the end of a task**. Do not use it
for commands you don't want to gate on (lint with warnings, etc.).

---

## validate

Read-only CI gate. Checks: task frontmatter (`id`/`status`/`PROOF`), `AGENTS.md`
≤200 lines, secret-pattern scan, expired-lease warnings, out-of-scope changed-file
warnings. **Hard gate:** a `status: ready` task without a fresh `evidence` receipt on
the current SHA **fails** (exit 1). Then prints `frontier handoff OK` / `FAILED`.

```bash
python scripts/frontier.py validate [tasks_dir]        # default docs/TASKS
```

Real output:

```
FAIL: docs\TASKS/CART-9.md status=ready without fresh evidence (run: frontier evidence CART-9 -- <test cmd>)
frontier handoff FAILED     # exit 1
```

```
frontier handoff OK         # exit 0, safe to merge
```

Safe to run in CI — it has no side effects. This is the merge gate.

---

## review

Diff-risk checklist for **the human reviewer** (never self-merge). Prints `git diff
--stat`, then flags: >10 files, dependency changes, migrations/schemas, possible
secrets, source-without-tests. Your reviewer reads *this*, not the raw diff.

```bash
python scripts/frontier.py review
```

Real output:

```
 src/cart/total.ts | 14 +-
 1 file changed, 13 insertions(+), 2 deletions(-)
Checklist:
1. PROOF commands re-run green on this SHA?
2. Changes inside lease scope only?
3. RISK: no test changes — add one (ladder: one check)
```

```
SKIP: not a git repo.
```

Run at task end, before the human approves the merge.

---

## resume

Bring an agent's state back after `/clear` or a cold start. Prints: unexpired leases
per agent, direct signals, and broadcasts (`done`/`escalate`/`noop`).

```bash
python scripts/frontier.py resume <agent>
```

Real output:

```
resume agent-1: read AGENTS.md + memory/compacted.md first
lease AUTH-1 198s left scope=['src/auth/**']
signal AUTH-1 [contracts_ready] from agent-1: AuthAPI v2 final
broadcast AUTH-1 [done] from agent-1: agent-1 released AUTH-1
```

Run on every cold start — it's the "where was I?" command.

---

## handoff

Print the handoff skeleton (STATE/CHANGED/PROOF/NEXT/RISKS) with the **real git SHA**
filled in, so the next agent or the human gets a deterministic handoff instead of a
chat-history summary.

```bash
python scripts/frontier.py handoff <task-file>
```

Real output:

```
STATE: CART-9 [in_progress] @ 3fa9c1e
CHANGED:
  M src/cart/total.ts
  M tests/cart/test_total.py
PROOF: <paste commands + exit codes>
NEXT: <next slice or 'done'>
RISKS: <what could still be wrong>
```

Run at slice end, before releasing the lease.

---

## doctor

Machine health check: python ≥3.9, git, optional `codegraph`, scaffold sanity
(`AGENTS.md` ≤200, parseable registry). Exit 1 only if python is missing/too old.

```bash
python scripts/frontier.py doctor
```

Real output:

```
OK       python>=3.9
OK       git
MISSING  codegraph — optional: npm i -g @codegraph/cli
OK       AGENTS.md<=200
OK       registry.json
```

Run once per machine, or when something feels off.

---

## selftest

End-to-end proof: runs `init`, `compact`, every lease subcommand, `drift`, `recall`,
`resume`, `review`, `bench`, `evidence`, and the `validate` ready-gate in a temp dir.
**Exit 0 only if every check passes.** This is also your CI job.

```bash
python scripts/frontier.py selftest
```

Real output (24 checks, summary):

```
PASS init AGENTS
PASS compact keeps relevant
PASS compact drops stale
PASS acquire a1
PASS parallel disjoint
PASS overlap blocked
PASS force coexistence
PASS heartbeat
PASS signal
PASS escalate
PASS noop
PASS lock
PASS unlock
PASS drift detects
PASS recall finds
PASS resume signals
PASS review degrades
PASS bench runs
PASS evidence exit
PASS evidence receipt
PASS ready-gate blocks
PASS validate green
selftest OK              # exit 0
```

Run after any upgrade to the tool, and in CI.

---

## bench

Measure real numbers on your machine: `compact` reduction %, `recall` latency,
`lease acquire+fingerprint` cost, `drift` re-fingerprint cost over a 200-file scope.
Stdlib-only, runs in a temp dir.

```bash
python scripts/frontier.py bench
```

Real output:

```
bench              what                                         result         ms avg
-------------------------------------------------------------------------------------
compact            context kept: big->compacted                 7/159 lines (4%)    1.2
recall             tier-0 retrieval (LEARNINGS+memory)          top-5 hits      4.6
lease acquire+fp   200-file sha1 scope fingerprint              1 lease       335.2
drift              200-file re-fingerprint + compare            clean|exit1   199.2
bench OK
```

Running it in CI tells you when the fingerprint cost of your verified workflow
outgrows what the codebase justifies.

---

## Exit-code summary

| Code | Meaning |
|---|---|
| `0` | command succeeded / check passed |
| `1` | staged check failed — **this blocks the step** (overlap, drift, missing evidence) |
| `2` | precondition missing (no lease for `drift`, no baseline) |

Every output line is stable text your agent, CI, or scripts can grep. No ANSI, no
tables, no ambiguity.