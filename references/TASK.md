---
id: {{TASK_ID}}
status: planned
agent: {{AGENT_ID}}
lease_scope: ["{{SCOPE_1}}", "{{SCOPE_2}}"]
symbol: {{SYMBOL_OR_EMPTY}}
component: {{COMPONENT_OR_EMPTY}}
module: {{MODULE_OR_EMPTY}}
file: {{FILE_OR_EMPTY}}
created: {{DATE}}
---

# {{TASK_ID}}: {{TITLE}}

## Problem
{{PROBLEM_STATEMENT}}

## Success Criteria
- [ ] {{CRITERION_1}}
- [ ] {{CRITERION_2}}

## Plan
1. Recall: `python scripts/frontier.py recall {{KEYWORDS}}`
2. Lease: `python scripts/frontier.py lease acquire {{TASK_ID}} {{AGENT_ID}} {{SCOPE_1}} {{SCOPE_2}}`
3. CodeGraph: `python scripts/frontier.py ctx "{{SYMBOL_OR_EMPTY}}"` (SKIP if absent)
4. Compact: `python scripts/frontier.py compact memory/<latest>.md memory/compacted.md docs/TASKS/{{TASK_ID}}.md`
5. Read-down first (`references/seek.md`): router -> task -> `ctx` symbols -> entry/test -> target + all callers. Then implement per ladder (`references/ladder.md`); regress test written before the fix; before each write run `drift`
6. Verify: `python scripts/frontier.py evidence {{TASK_ID}} -- <test cmd>`
7. Release: `python scripts/frontier.py lease release {{TASK_ID}} {{AGENT_ID}}`

## PROOF
- PROOF: commands + exit codes + SHA (fill before handoff)
- Exit codes:
- SHA:
- Artifacts: