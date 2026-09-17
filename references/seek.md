# Seek — read-down order before touching code

Never edit from a cold read. Read in this order until the change is local:

1. `AGENTS.md` (router) — boundaries, gotchas, how this repo builds.
2. Task file + `memory/compacted.md` — what, why, prior attempts.
3. Repo shape via symbols, not the full tree: `frontier.py ctx "<symbol>"`.
4. Entry file + the real test command — how it runs, how it's verified.
5. The file(s) you will change + **every caller** — read fully, then decide.

Stop reading when the change is local. Reading past that point is research; write it to `memory/` instead of holding it.

## Cross-file work

Grep is a fallback, `ctx`/`codegraph explore` is first. If a symbol is touched from
N call sites, read all N before editing the shared function (one guard there beats
a guard per caller).