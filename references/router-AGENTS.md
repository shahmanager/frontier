# AGENTS.md — [Project]

You are a [specialist role] on [project type]. Priorities: 1. correctness 2. simplicity 3. minimal impact.

## Behavior

- Think before coding. Simplicity first (ladder: `references/ladder.md`). Surgical changes. Goal-driven (skill `frontier`).
- Output: code first, ≤3 lines after. No filler, no tool narration (`references/output.md`).

## Commands

```bash
[build cmd with flags]   # build one file, not whole project
[test cmd - single]      # prefer single test
[lint/typecheck cmd]
```

## Boundaries

- Always: [e.g. run lint before commit, tests before behavior change]
- Ask first: [e.g. new deps, migrations, shared contracts]
- Never: [e.g. commit secrets, prod/customer data, deploy without approval, direct table writes]

## Pointers

- Goals: `docs/GOALS.md`. Context: `docs/CONTEXT.md`. Tasks: `docs/TASKS/<ID>.md`. Learnings: `docs/LEARNINGS.md`.
- For [db/ui/review] work, load `.agents/skills/[name]/SKILL.md`.
- Stack/versions: `docs/CONTEXT.md`. Good example: `[path/to/good-file]`.

## Task start (run in order)

- `python scripts/frontier.py recall <task words>` (past learnings, before plan)
- Auto-skills: load every skill in `.agents/skills/registry.json` whose trigger regex matches the task text.
- `python scripts/frontier.py lease acquire <ID> <agent> <scope...>`
- `python scripts/frontier.py ctx <symbol>` (SKIP line if codegraph absent)
- `python scripts/frontier.py compact memory/<latest>.md memory/compacted.md docs/TASKS/<ID>.md`
- Read only: `AGENTS.md` + task file + `memory/compacted.md`.

## During work

- Before each write: `python scripts/frontier.py drift <ID> <agent>` (exit 1 = re-read files first)
- On stuck: `python scripts/frontier.py lease escalate <ID> <agent> <reason>`
- Idle, achieved stopping-rule: `python scripts/frontier.py lease noop <ID> <agent>`

## Task end

- `python scripts/frontier.py lease release <ID> <agent>` (broadcasts done)
- `python scripts/frontier.py review` (diff-risk checklist)
- `python scripts/frontier.py validate`