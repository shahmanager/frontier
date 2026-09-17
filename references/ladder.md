# Ladder (borrowed from ponytail — the minimal-diff reflex)

Run AFTER understanding the problem, not instead of it. Trace the real flow
end to end first, then climb. Stop at the first rung that holds.

1. **Exist at all?** Speculative need = skip, say so in one line. (YAGNI)
2. **Already in codebase?** Helper/util/pattern a few files over → reuse it.
3. **Stdlib does it?** Use it.
4. **Native platform feature covers it?** `<input type=date>` over picker lib, CSS over JS, DB constraint over app code.
5. **Installed dependency solves it?** Use it. Never add a new one for a few lines.
6. **One line?** One line.
7. **Only then:** minimum code that works.

## Bug fixes

Symptom report ≠ root cause. Grep every caller of the function first. One guard
in the shared function beats a guard per caller.

## Debug loop (root cause, not symptom)

1. **Reproduce**: real command, not asserted. Record exit code + output shape.
2. **Minimize**: strip the repro to the smallest case that still fails.
3. **Bisect**: binary / `git blame` / caller sweep. Grep every caller of the touched function.
4. **Fix at the shared node**: one guard in the shared function > a guard per caller.
5. **Prove**: write the regress test FIRST — it must fail on the bug, then the fix flips it green (`evidence` binds exit-0 + SHA).

## Test-first green loop

- A bug fix ships its regress test written **before** the fix: red → green.
- Non-trivial logic (branch/loop/parser/money path) leaves ONE runnable check.
- Trivial one-liners need no test — YAGNI applies to tests too.

## Rules

- No unrequested abstractions (one-impl interface, one-product factory, never-changing config). No "for later" scaffolding.
- Deletion over addition. Boring over clever. Fewest files, shortest diff — in the right place.
- Mark deliberate ceilings: `# ponytail: global lock, per-account locks if throughput matters`.
- Non-trivial logic (branch/loop/parser/money path) leaves ONE runnable check: assert-based `demo()`/`__main__` or one small `test_*.py`. Trivial one-liners need no test.
- Complex request: ship lazy version, ask in same response: "Did X; Y covers it. Need full X? Say so."
