---
name: frontier
description: >
  1-shot build discipline for AI coding in any repo. Use when starting a task,
  setting up AGENTS.md/CLAUDE.md, running multi-agent work, or when agent
  repeats mistakes. Karpathy behavior + Cherny loop + ponytail minimal-diff
  ladder + caveman-lite output + CodeGraph nav + relevance compaction +
  file-based multi-agent leases. Setup: python scripts/frontier.py init
---

# Frontier build discipline v3

## 1. Behavior (always on)

- Think before coding. State assumptions, surface tradeoffs, push back when warranted.
- Simplicity first: climb the ladder in `references/ladder.md`, stop at first rung that holds. Nothing speculative.
- Surgical changes. Touch only what you must. Clean up only your own mess.
- Goal-driven. Define success criteria. Loop until verified.
- Never simplify away: trust-boundary validation, data-loss error handling, security, a11y basics, anything explicitly requested.

## 2. Loop (every task >30min)

1. Plan first in `docs/TASKS/<ID>.md` (copy `references/TASK.md`). Check in before coding. Read-down first: `references/seek.md` order (router -> task -> symbols -> entry/test -> target + all callers).
2. One slice, one branch, one PR. No dependent work before contracts merge.
3. Verify before done: run real commands, record exit codes + SHA. Mocks != integration.
4. On correction: append `symptom -> cause -> fix` to `docs/LEARNINGS.md` (max 5 lines). Never hide failed runs.
5. End with `STATE / CHANGED / PROOF / NEXT / RISKS` (`handoff` generates the skeleton). No chat-history reliance.

## 3. Output (caveman-lite, always on)

- Code first. Then ≤3 short lines: what was skipped, when to add it.
- No filler (`just/really/basically`), no pleasantries, no tool-call narration. Fragments OK.
- Code symbols, paths, error strings verbatim. Never abbreviate those.
- Drop terseness for: security warnings, destructive-action confirms, ambiguous-order sequences. Resume after.
- Full stop on `stop frontier` / `normal mode`. See `references/output.md`.

## 4. Context budget

- Router `AGENTS.md` <60 lines. Root instructions 100-150 sweet spot, hard stop 200 (past 300 gains reverse).
- Commands first with exact flags. Numbered workflows. 3-10 line real examples pointing at good files, not prose.
- Only non-inferable content: custom tooling, weird builds, project gotchas. Never: full tree, generic advice, `/init` dumps.
- Boundaries three-tier: Always / Ask first / Never (top item: secrets/prod/customer data without approval). Every boundary pairs with a do.
- Nesting: shared rules root, package rules in subdir `AGENTS.md`. Closest wins. Link, don't duplicate. Detail in `references/`, loaded on demand.
- `/clear` between unrelated tasks. Context rots ~30min — re-read router after reset.
- Skeptical review: one builder, one fresh reviewer. Reviewer challenges, never rubber-stamps.

## 5. Memory (progressive disclosure)

- Tier 0 (default): `docs/LEARNINGS.md` + `memory/YYYY-MM-DD.md`. Session start reads router + task file + compacted log only. Session end appends decisions.
- Tier 1 (if installed): claude-mem / agentmemory. `recall` before plan, `remember`/`lesson` after correction, `handoff` at slice end.
- Never memorize secrets/tokens/customer data. `<private>`-tag it out.
- Gotcha seen twice -> `Known constraints` in CONTEXT.md. Weekly: consolidate dupes, delete stale.

## 6. Scaffold (1-shot)

```bash
python scripts/frontier.py init [target_dir]   # win/mac/linux, stdlib only
```

Creates: `AGENTS.md`, `CLAUDE.md`, `docs/{GOALS,CONTEXT,TASKS/_TEMPLATE,LEARNINGS}.md`,
`.agents/{protocol/LEASE.md,skills/{registry.json,codegraph/SKILL.md}}`,
`memory/`, `.codegraph/`, `.gitignore` entries. Never overwrites. See `references/INSTALL.md`.

## 7. Validate (read-only CI gate)

```bash
python scripts/frontier.py validate [docs/TASKS]
```

Checks: frontmatter (id/status/PROOF), `AGENTS.md` ≤200 lines, secret scan,
expired-lease warnings. Gate: `status=ready` without fresh exit-0 evidence on
current SHA fails. Warnings: stale evidence, files outside every lease scope.
Exit 1 on fail. No side effects.

## 8. Auto-skills

`.agents/skills/registry.json` maps task keywords → skill names. At task start, agent loads every skill whose trigger matches the task text (see `references/INSTALL.md`). Trigger descriptions must be precise so auto-invoke fires.

## 9. CodeGraph nav

Prefer over grep for cross-file work: `codegraph explore "<symbol or question>" > .codegraph/ctx.md`, read that file. Per-repo index (`codegraph init`), incremental refresh. Skill wrapper: `.agents/skills/codegraph/SKILL.md`.

## 10. Compaction (no recency bias)

```bash
python scripts/frontier.py compact <in.md> <out.md> <task-file>
```

Scores blocks by keyword overlap with task's `symbol:/component:/module:/file:` keys (case-insensitive). Ties keep file order via stable sort — never newest-first. Caps at 300 lines.

## 11. Multi-agent leases

```bash
python scripts/frontier.py lease acquire TASK AGENT SCOPE...   # fail on scope overlap
python scripts/frontier.py lease heartbeat TASK AGENT          # every ~30s, bg
python scripts/frontier.py lease signal TASK FROM TO TYPE MSG  # async handoff
python scripts/frontier.py lease escalate TASK AGENT REASON    # stuck -> escalate up
python scripts/frontier.py lease noop TASK AGENT               # stopping-rule ping
python scripts/frontier.py lease lock|unlock TASK AGENT        # shared-file mutex
python scripts/frontier.py lease release TASK AGENT            # broadcasts done
python scripts/frontier.py lease status TASK | list            # discovery
```

Leases are per-agent (`.agents/leases/<task>.<agent>.json`, 5-min TTL). Same task + disjoint scopes run in parallel; overlapping scopes block. Release auto-writes a `done` broadcast so polling peers stop (stopping rule). Full protocol: `.agents/protocol/LEASE.md`.

## 12. Toolbelt (single file, stdlib only)

```bash
python scripts/frontier.py suggest <task text...>  # which skills to load
python scripts/frontier.py recall <words...>       # past learnings, before plan
python scripts/frontier.py ctx <symbol...>         # codegraph, SKIP if absent
python scripts/frontier.py handoff <task-file>     # handoff skeleton + git SHA
python scripts/frontier.py drift <task> <agent>    # scope changed? exit 1 = re-read
python scripts/frontier.py evidence <task> -- <cmd>  # bind exit code to git SHA
python scripts/frontier.py review                  # diff-risk checklist
python scripts/frontier.py resume <agent>          # leases + signals + broadcasts
python scripts/frontier.py doctor                  # machine check
python scripts/frontier.py selftest                # 24-check end-to-end proof
python scripts/frontier.py bench                   # measured numbers (compact/recall/lease/drift)
python scripts/frontier.py lease acquire T A S... --force --ttl N  # forced coexistence
```

## 13. Git guardrails (never violate for any AI)

- Inspect `git status` + `git diff` before commit/push; stage only intended files. Never commit secrets.
- Commit, amend, push, force-push, PR only when explicitly requested by the human. Post-push force-push is off.
- Hooks that reject a commit: fix and make a NEW commit, never amend the failed one.
- One slice, one branch, one PR. No dependents before contracts merge. No self-merge.

## 14. Deferred tools (defer, never absorb)

Frontier is a discipline spine, not a tool host. It sets up its own files and
delegates the rest:

| Capability | Tool (external) | Frontier hook |
|---|---|---|
| Tier-1 memory | claude-mem / agentmemory | `recall` = tier-0 only (5% coop), stays compatible |
| Semantic nav | codegraph | `ctx` runs it, SKIPs if absent |
| Orchestration | Task / Bureau / STORM | leases are the lock protocol *underneath* |
| Security scan | gitleaks / trivy | `validate` checks a few secret patterns only |
| Test engines | pytest / vitest / cargo | `evidence` consumes their exit code + SHA |

DM those tools directly; Frontier only reads their signals and stays out of their job.

## Anti-patterns

Bible AGENTS.md, diary CLAUDE.md, task without verifiable criteria, mock claimed as integration, giant PR, self-merge, force-push after push, prompt pollution in router, manual skill loading, grep for cross-file nav, recency-biased context, single lease file per task, validator with side effects, prose longer than the code.
