#!/usr/bin/env python3
"""frontier.py — 1-shot Frontier scaffold + portable lease/compact/validate.

Stdlib only. Works on Windows/macOS/Linux. Replaces the old bash scripts
(validate-handoff.sh, compact-context.sh, lease.sh) which needed jq + GNU date.

Usage:
  python scripts/frontier.py init [target_dir]   # scaffold a repo (default: cwd)
  python scripts/frontier.py suggest <task text...>  # skills to load
  python scripts/frontier.py compact IN OUT TASK_FILE
  python scripts/frontier.py ctx <symbol...>     # codegraph w/ graceful SKIP
  python scripts/frontier.py lease acquire|... [--force]
  python scripts/frontier.py handoff TASK_FILE   # STATE/CHANGED/PROOF/NEXT/RISKS
  python scripts/frontier.py validate [tasks_dir]
  python scripts/frontier.py doctor              # machine check
  python scripts/frontier.py selftest            # end-to-end check
"""
import argparse
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[1]
LEASE_TTL = 300  # seconds
COMPACT_CAP = 300  # lines
SECRET_RE = re.compile(
    r"sk-[a-z0-9]{20,}|ghp_[a-z0-9]{20,}|xox[bpas]-[a-z0-9-]+|-----BEGIN .*PRIVATE",
    re.I,
)
KEY_RE = re.compile(r"^(symbol|component|module|file):\s*(.+)$", re.M)


def fail(msg):
    print(f"FAIL: {msg}")
    return False


# ---------------------------------------------------------------- init
def cmd_init(target):
    """Copy Frontier scaffold into target repo. Never overwrites existing files."""
    t = Path(target)
    copies = [
        ("references/router-AGENTS.md", "AGENTS.md"),
        ("references/CLAUDE.md", "CLAUDE.md"),
        ("references/GOALS.md", "docs/GOALS.md"),
        ("references/CONTEXT.md", "docs/CONTEXT.md"),
        ("references/TASK.md", "docs/TASKS/_TEMPLATE.md"),
        ("references/LEARNINGS.md", "docs/LEARNINGS.md"),
        (".agents/protocol/LEASE.md", ".agents/protocol/LEASE.md"),
        (".agents/skills/registry.json", ".agents/skills/registry.json"),
        (
            ".agents/skills/codegraph/SKILL.md",
            ".agents/skills/codegraph/SKILL.md",
        ),
    ]
    made = skipped = 0
    for src, dst in copies:
        s, d = SKILL_ROOT / src, t / dst
        if d.exists():
            skipped += 1
            continue
        if not s.exists():
            print(f"WARN: template missing, skip: {src}")
            skipped += 1
            continue
        d.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(s, d)
        made += 1
    for d in ("docs/TASKS", "memory", ".agents/leases", ".agents/signals",
              ".agents/sentinel", ".codegraph"):
        (t / d).mkdir(parents=True, exist_ok=True)
    gi = t / ".gitignore"
    want = {".agents/leases/", ".agents/signals/", ".agents/sentinel/",
            "memory/compacted.md", ".codegraph/ctx.md"}
    have = set(gi.read_text().splitlines()) if gi.exists() else set()
    if not want <= have:
        with open(gi, "a") as f:
            f.write("\n# frontier (ephemeral agent state)\n")
            f.writelines(l + "\n" for l in sorted(want - have))
    print(f"frontier init OK: {made} created, {skipped} skipped -> {t}")
    print("Next: fill AGENTS.md [brackets], run `codegraph init` if available.")


# ---------------------------------------------------------------- compact
def cmd_compact(inp, out, task_file):
    """Score context blocks by keyword overlap with task file. No recency bias.

    Ties keep file order (stable sort), never newest-first. Caps at 300 lines.
    """
    kw = [m.group(2).strip().lower() for m in
          KEY_RE.finditer(Path(task_file).read_text(errors="replace"))]
    blocks = re.split(r"\n(?:---\n|\n)", Path(inp).read_text(errors="replace"))
    if not kw:
        print("WARN: no symbol/component/module/file keys in task; "
              "keeping file order, capped.")
        Path(out).write_text("\n".join(blocks)[:8000])
        return
    scored = []
    for i, b in enumerate(blocks):
        bl = b.lower()
        score = sum(1 for k in kw if k and k in bl)
        if score:
            scored.append((score, i, b))
    scored.sort(key=lambda r: (-r[0], r[1]))  # score desc, file order on ties
    text = "\n---\n".join(b for _, _, b in scored)
    lines = text.splitlines()[:COMPACT_CAP]
    Path(out).write_text("\n".join(lines) + "\n")
    print(f"compact OK: {len(scored)}/{len(blocks)} blocks kept -> {out}")


# ---------------------------------------------------------------- lease
def _lease_paths(task, agent=None):
    base = Path(".agents")
    if agent:
        return base / "leases" / f"{task}.{agent}.json"
    return base / "leases"


def _alive(p):
    try:
        return json.loads(p.read_text()).get("exp", 0) > time.time()
    except (OSError, ValueError):
        return False


def _scopes_overlap(a, b):
    return any(fnmatch.fnmatchcase(x, y) or fnmatch.fnmatchcase(y, x)
               for x in a for y in b)


def cmd_lease(args):
    cmd, task = args.cmd, args.task
    Path(".agents/leases").mkdir(parents=True, exist_ok=True)
    Path(f".agents/signals/{task}").mkdir(parents=True, exist_ok=True)
    Path(".agents/sentinel").mkdir(parents=True, exist_ok=True)

    if cmd == "list":
        for p in sorted(Path(".agents/leases").glob("*.json")):
            print(p.stem, "ALIVE" if _alive(p) else "EXPIRED")
        return
    if cmd == "status":
        found = False
        for p in sorted(Path(".agents/leases").glob(f"{task}.*.json")):
            print(p.stem, json.loads(p.read_text()))
            found = True
        if not found:
            print("no leases")
        return

    agent = args.agent
    lp = _lease_paths(task, agent)
    if cmd == "acquire":
        scopes = args.rest
        for p in Path(".agents/leases").glob(f"{task}.*.json"):
            if p == lp or not _alive(p):
                continue
            other = json.loads(p.read_text())
            if _scopes_overlap(scopes, other.get("scope", [])):
                if args.force:
                    print(f"WARN: overlapping {other.get('agent')} "
                          f"scope={other.get('scope')} (forced coexistence)")
                    continue
                print(f"LEASE_HELD by {other.get('agent')} scope={other.get('scope')}")
                sys.exit(1)
        ttl = getattr(args, "ttl", LEASE_TTL)
        lp.write_text(json.dumps(
            {"agent": agent, "exp": time.time() + ttl, "scope": scopes,
             "fp": _fingerprint(scopes)}))
        print("ACQUIRED")
    elif cmd == "release":
        lp.unlink(missing_ok=True)
        # broadcast done so polling peers stop early (stopping rule)
        Path(f".agents/signals/{task}/__done__.json").write_text(json.dumps(
            {"type": "done", "payload": f"{agent} released {task}",
             "ts": int(time.time()), "from": agent}))
        print("RELEASED")
    elif cmd == "escalate":
        # stuck -> human/router or cleaner-context reviewer (Cognition: escalate up)
        reason = " ".join(args.rest[:3])
        Path(f".agents/signals/{task}/__ESCALATE__.json").write_text(json.dumps(
            {"type": "escalate", "payload": reason, "ts": int(time.time()),
             "from": agent}))
        print("ESCALATED")
    elif cmd == "noop":
        # explicit stop-condition ping: proves peer liveness, ends chatter loops
        Path(f".agents/signals/{task}/__noop__.json").write_text(json.dumps(
            {"type": "noop", "payload": f"{agent} idle, no further output",
             "ts": int(time.time()), "from": agent}))
        print("NOOP_SENT")
    elif cmd == "heartbeat":
        if not _alive(lp):
            print("LEASE_LOST")
            sys.exit(1)
        d = json.loads(lp.read_text())
        d["exp"] = time.time() + LEASE_TTL
        lp.write_text(json.dumps(d))
        print("OK")
    elif cmd == "signal":
        target, typ, payload = args.rest[0], args.rest[1], " ".join(args.rest[2:])
        Path(f".agents/signals/{task}/{target}.json").write_text(json.dumps(
            {"type": typ, "payload": payload, "ts": int(time.time()),
             "from": agent}))
        print("SENT")
    elif cmd == "lock":
        lock = Path(f".agents/sentinel/{task}.lock")
        owner = lock / "owner.json"
        if owner.exists():
            try:
                if json.loads(owner.read_text()).get("exp", 0) > time.time():
                    print("LOCKED")
                    sys.exit(1)
            except ValueError:
                pass
            shutil.rmtree(lock, ignore_errors=True)
        lock.mkdir(parents=True)
        owner.write_text(json.dumps(
            {"agent": agent, "exp": time.time() + LEASE_TTL}))
        print("LOCKED_OK")
    elif cmd == "unlock":
        lock = Path(f".agents/sentinel/{task}.lock")
        shutil.rmtree(lock, ignore_errors=True)
        print("UNLOCKED")


# ---------------------------------------------------------------- validate (read-only)
def cmd_validate(tasks_dir):
    ok = True
    ag = Path("AGENTS.md")
    if ag.exists() and sum(1 for _ in open(ag)) > 200:
        ok = fail("AGENTS.md >200 lines") and False
    sk = SKILL_ROOT / "SKILL.md"
    if sum(1 for _ in open(sk)) > 200:
        print("WARN: frontier SKILL.md >200 lines (own budget)")
    for t in sorted(Path(tasks_dir).rglob("*.md")):
        if t.name.startswith("_"):
            continue
        txt = t.read_text(errors="replace")
        for key in ("^id:", "^status:", "PROOF:"):
            if not re.search(key, txt, re.M):
                ok = fail(f"{t} missing {key.strip('^:')}") and False
    for root in ("docs", "."):
        for p in Path(root).rglob("*.md"):
            if ".agents" in p.parts:
                continue
            for i, line in enumerate(p.read_text(errors="replace").splitlines(), 1):
                if SECRET_RE.search(line):
                    ok = fail(f"possible secret {p}:{i}") and False
                    break
    for p in Path(".agents/leases").glob("*.json") if Path(".agents/leases").exists() else []:
        if not _alive(p):
            print(f"WARN: expired lease {p.name}")

    # evidence gate: status=ready claims done -> require fresh exit-0 receipt
    head = _git("rev-parse", "HEAD")
    tasks = []
    for t in sorted(Path(tasks_dir).rglob("*.md")):
        if t.name.startswith("_"):
            continue
        txt = t.read_text(errors="replace")
        gid = re.search(r"^id:\s*(.+)$", txt, re.M)
        gst = re.search(r"^status:\s*(.+)$", txt, re.M)
        gsc = re.search(r"lease_scope:\s*\[(.*?)\]", txt, re.S)
        tasks.append((t, (gid.group(1).strip() if gid else ""),
                      (gst.group(1).strip() if gst else ""),
                      re.findall(r'"([^"]+)"', gsc.group(1)) if gsc else []))
    evdir = Path(".agents/evidence")
    for t, gid, gst, _sc in tasks:
        if not gid:
            continue
        recs = []
        if evdir.exists():
            for rp in evdir.glob(f"{gid}.*.json"):
                try:
                    recs.append(json.loads(rp.read_text()))
                except ValueError:
                    continue
        fresh = [r for r in recs if r.get("exit") == 0
                 and (not head or r.get("sha") == head)]
        if gst == "ready" and not fresh:
            ok = fail(f"{t} status=ready without fresh evidence "
                      f"(run: frontier evidence {gid} -- <test cmd>)") and False
        elif recs and head and not fresh:
            print(f"WARN: {gid} evidence stale (sha moved, re-run evidence)")

    # scope warnings: changed files outside every task's lease scope
    scopes = {s for _, _, _, sc in tasks for s in sc}
    if scopes:
        for line in _git("status", "--porcelain").splitlines():
            p = line[3:].strip().strip('"')
            if " -> " in p:
                p = p.split(" -> ")[-1].strip().strip('"')
            if p and not any(fnmatch.fnmatchcase(p, s) for s in scopes):
                print(f"WARN: OUT OF SCOPE: {p}")
    print("frontier handoff OK" if ok else "frontier handoff FAILED")
    sys.exit(0 if ok else 1)


# ---------------------------------------------------------------- toolbelt
def _registry():
    for p in (Path(".agents/skills/registry.json"),
              SKILL_ROOT / ".agents/skills/registry.json"):
        if p.exists():
            try:
                return json.loads(p.read_text()).get("skills", [])
            except ValueError:
                return []
    return []


def cmd_suggest(words):
    """Match registry triggers against task text. Prints skills to load."""
    text = " ".join(words)
    hits = [s["name"] for s in _registry()
            if re.search(s.get("trigger", "$^"), text, re.I)]
    print(" ".join(hits) if hits else "NONE")
    for h in hits:
        print(f"load skill: {h}")


def cmd_ctx(words):
    """CodeGraph explore with graceful degrade when not installed."""
    symbol = " ".join(words)
    Path(".codegraph").mkdir(exist_ok=True)
    if shutil.which("codegraph"):
        try:
            r = subprocess.run(["codegraph", "explore", symbol],
                               capture_output=True, text=True)
        except OSError:
            print("SKIP: codegraph binary broken or not executable.")
            return
        Path(".codegraph/ctx.md").write_text(r.stdout or r.stderr)
        print(f"ctx OK ({len((r.stdout or '').splitlines())} lines)")
    else:
        print("SKIP: codegraph not installed (one line).")


def cmd_doctor():
    """Machine check: python, git, codegraph, scaffold health."""
    bad = []

    def row(name, good, hint=""):
        print(f"{'OK      ' if good else 'MISSING '} {name}"
              + ("" if good else f" — {hint}"))
        if not good:
            bad.append(name)

    row("python>=3.9", sys.version_info >= (3, 9), "upgrade python")
    row("git", shutil.which("git"), "install git")
    row("codegraph", shutil.which("codegraph"),
        "optional: npm i -g @codegraph/cli")
    ag = Path("AGENTS.md")
    row("AGENTS.md<=200", ag.exists() and sum(1 for _ in open(ag)) <= 200,
        "run frontier init here")
    try:
        json.loads(Path(".agents/skills/registry.json").read_text())
        reg = True
    except (OSError, ValueError):
        reg = False
    row("registry.json", reg, "run frontier init here")
    sys.exit(1 if "python>=3.9" in bad else 0)


def cmd_handoff(task_file):
    """Print STATE/CHANGED/PROOF/NEXT/RISKS skeleton with real git data."""
    txt = Path(task_file).read_text(errors="replace")
    gid = re.search(r"^id:\s*(.+)$", txt, re.M)
    gst = re.search(r"^status:\s*(.+)$", txt, re.M)
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True).stdout.strip() or "n/a"
        ch = subprocess.run(["git", "status", "--porcelain"],
                            capture_output=True, text=True).stdout.strip().splitlines()[:10]
    except OSError:
        sha, ch = "n/a", []
    print(f"STATE: {gid.group(1) if gid else '?'} "
          f"[{gst.group(1) if gst else '?'}] @ {sha}")
    print("CHANGED:")
    for line in ch:
        print(f"  {line}")
    print("PROOF: <paste commands + exit codes>")
    print("NEXT: <next slice or 'done'>")
    print("RISKS: <what could still be wrong>")


def cmd_selftest():
    """End-to-end check of init/compact/lease/validate in a temp dir."""
    import tempfile
    fails = []

    def check(name, cond):
        print(f"{'PASS' if cond else 'FAIL'} {name}")
        if not cond:
            fails.append(name)

    def ns(cmd, task="T-001", agent="a1", rest=None, force=False):
        return argparse.Namespace(cmd=cmd, task=task, agent=agent,
                                  rest=rest or [], force=force)

    cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as td:
        os.chdir(td)
        try:
            cmd_init(".")
            check("init AGENTS", Path("AGENTS.md").exists())
            Path("docs/TASKS/T-001.md").write_text(
                "id: T-001\nstatus: planned\nagent: a1\nsymbol: Widget\n"
                "component: shop\n---\n# T\n\n## PROOF\n- PROOF: x\n")
            Path("memory/2026-01-01.md").write_text(
                "Widget renders shop cart.\n\n---\n\nLunch notes.\n")
            cmd_compact("memory/2026-01-01.md", "memory/compacted.md",
                        "docs/TASKS/T-001.md")
            out = Path("memory/compacted.md").read_text()
            check("compact keeps relevant", "Widget" in out)
            check("compact drops stale", "Lunch" not in out)
            cmd_lease(ns("acquire", rest=["src/*"]))
            check("acquire a1", Path(".agents/leases/T-001.a1.json").exists())
            cmd_lease(ns("acquire", agent="a2", rest=["docs/*"]))
            check("parallel disjoint", Path(".agents/leases/T-001.a2.json").exists())
            try:
                cmd_lease(ns("acquire", agent="a3", rest=["src/x.ts"]))
                check("overlap blocked", False)
            except SystemExit as e:
                check("overlap blocked", e.code == 1)
            cmd_lease(ns("acquire", agent="a3", rest=["src/x.ts"], force=True))
            check("force coexistence",
                  Path(".agents/leases/T-001.a3.json").exists())
            cmd_lease(ns("heartbeat"))
            check("heartbeat", True)
            cmd_lease(ns("signal", rest=["a2", "ready", "go"]))
            check("signal", Path(".agents/signals/T-001/a2.json").exists())
            cmd_lease(ns("signal", rest=["a2", "ready", "go"]))
            check("signal", Path(".agents/signals/T-001/a2.json").exists())
            cmd_lease(ns("escalate", rest=["stuck on socket leak"]))
            check("escalate",
                  Path(".agents/signals/T-001/__ESCALATE__.json").exists())
            cmd_lease(ns("noop"))
            check("noop",
                  Path(".agents/signals/T-001/__noop__.json").exists())
            cmd_lease(ns("lock"))
            check("lock", Path(".agents/sentinel/T-001.lock").exists())
            cmd_lease(ns("unlock"))
            check("unlock", not Path(".agents/sentinel/T-001.lock").exists())
            import contextlib
            import io
            Path("src").mkdir(exist_ok=True)
            Path("src/app.ts").write_text("v1")
            try:
                cmd_drift("T-001", "a1")
                check("drift detects", False)
            except SystemExit as e:
                check("drift detects", e.code == 1)
            Path("docs/LEARNINGS.md").write_text(
                "# L\n\n- 2026-01-02 Widget cache stampede "
                "-> missing lock -> add lock\n")
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cmd_recall(["Widget", "cache"])
            check("recall finds", "stampede" in buf.getvalue())
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cmd_resume("a2")
            check("resume signals", "go" in buf.getvalue())
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                cmd_review()
            check("review degrades", "SKIP" in buf.getvalue())
            try:
                cmd_evidence("T-001", [sys.executable, "-c", "pass"])
                check("evidence exit", False)
            except SystemExit as e:
                check("evidence exit", e.code == 0)
            check("evidence receipt",
                  len(list(Path(".agents/evidence").glob("T-001.*.json"))) == 1)
            for a in ("a1", "a2", "a3"):
                cmd_lease(ns("release", agent=a))
            Path("docs/TASKS/T-002.md").write_text(
                "id: T-002\nstatus: ready\n---\n# T2\n\n## PROOF\n- PROOF: x\n")
            try:
                cmd_validate("docs/TASKS")
                check("ready-gate blocks", False)
            except SystemExit as e:
                check("ready-gate blocks", e.code == 1)
            Path("docs/TASKS/T-002.md").unlink()
            try:
                cmd_validate("docs/TASKS")
                check("validate green", True)
            except SystemExit as e:
                check("validate green", e.code == 0)
        finally:
            os.chdir(cwd)
    print(f"selftest {'OK' if not fails else 'FAILED: ' + ','.join(fails)}")
    sys.exit(1 if fails else 0)


# ---------------------------------------------------------------- research-backed
def _git(*args):
    try:
        r = subprocess.run(["git", *args], capture_output=True, text=True)
        return r.stdout.strip() if r.returncode == 0 else ""
    except OSError:
        return ""


def _scope_files(scopes):
    out = set()
    for s in scopes:
        if Path(s).is_dir():
            out.update(f for f in Path(s).rglob("*") if f.is_file())
        else:
            out.update(f for f in Path(".").glob(s) if f.is_file())
    return out


def _fingerprint(scopes):
    """sha1 snapshot of scope files at acquire time (optimistic concurrency)."""
    fp = {}
    for f in _scope_files(scopes):
        try:
            if f.stat().st_size > 2_000_000:
                continue
            fp[f.as_posix()] = hashlib.sha1(f.read_bytes()).hexdigest()[:12]
        except OSError:
            continue
    return fp


def cmd_drift(task, agent):
    """Exit 1 if scope files changed since acquire (stale-view detector)."""
    lp = _lease_paths(task, agent)
    if not lp.exists() or not _alive(lp):
        print("NO_LEASE: acquire first")
        sys.exit(2)
    d = json.loads(lp.read_text())
    if d.get("fp") is None:
        print("NO_BASELINE: re-acquire lease")
        sys.exit(2)
    now = _fingerprint(d.get("scope", []))
    mods = [k for k in d["fp"] if k in now and now[k] != d["fp"][k]]
    dels = [k for k in d["fp"] if k not in now]
    news = [k for k in now if k not in d["fp"]]
    if not (mods or dels or news):
        print("CLEAN")
        return
    for k in mods:
        print(f"M {k}")
    for k in dels:
        print(f"D {k}")
    for k in news:
        print(f"N {k}")
    print("drift found: re-read files before writing")
    sys.exit(1)


def cmd_evidence(task, cmd):
    """Run cmd, bind exit code to git SHA. Passthrough exit code."""
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    Path(".agents/evidence").mkdir(parents=True, exist_ok=True)
    sha = _git("rev-parse", "HEAD") or "n/a"
    r = subprocess.run(cmd)
    n = len(list(Path(".agents/evidence").glob(f"{task}.*.json")))
    Path(f".agents/evidence/{task}.{n}.json").write_text(json.dumps(
        {"task": task, "cmd": cmd, "exit": r.returncode, "sha": sha,
         "ts": int(time.time())}))
    print(f"evidence {task}.{n}: exit={r.returncode} sha={sha[:12]}")
    sys.exit(r.returncode)


STOPWORDS = set("the and for with from that this have has are was were will "
                "would can not but you your our their they them then than into "
                "over under again once here there when what which while about "
                "after before between with".split())


def _words(s):
    return set(re.findall(r"[a-z0-9_]{4,}", s.lower())) - STOPWORDS


def cmd_recall(words):
    """Tier-0 memory retrieval: top-5 overlapping lines from LEARNINGS/memory."""
    q = _words(" ".join(words))
    if not q:
        print("NONE")
        return
    srcs = []
    if Path("docs/LEARNINGS.md").exists():
        srcs.append(Path("docs/LEARNINGS.md"))
    if Path("memory").exists():
        srcs += [p for p in sorted(Path("memory").glob("*.md"))
                 if p.name != "compacted.md"]
    hits = []
    for p in srcs:
        for i, line in enumerate(
                p.read_text(errors="replace").splitlines(), 1):
            s = len(q & _words(line))
            if s:
                hits.append((s, f"{p}:{i}", line.strip()[:160]))
    hits.sort(key=lambda h: -h[0])
    if not hits:
        print("NONE")
        return
    for s, loc, line in hits[:5]:
        print(f"[{s}] {loc}: {line}")


def cmd_resume(agent):
    """Session bundle: live leases + pending signals + read list."""
    print(f"resume {agent}: read AGENTS.md + memory/compacted.md first")
    for p in sorted(Path(".agents/leases").glob(f"*.{agent}.json")):
        try:
            d = json.loads(p.read_text())
        except ValueError:
            continue
        task = p.stem.rsplit(".", 1)[0]
        state = f"{int(d.get('exp', 0) - time.time())}s left" if _alive(p) else "EXPIRED"
        print(f"lease {task} {state} scope={d.get('scope')}")
    for sp in sorted(Path(".agents/signals").rglob(f"{agent}.json")):
        try:
            d = json.loads(sp.read_text())
        except ValueError:
            continue
        print(f"signal {sp.parent.name} [{d.get('type')}] "
              f"from {d.get('from')}: {d.get('payload')}")
    for sp in sorted(Path(".agents/signals").rglob("__*.json")):
        try:
            d = json.loads(sp.read_text())
        except ValueError:
            continue
        print(f"broadcast {sp.parent.name} [{d.get('type')}] "
              f"from {d.get('from')}: {d.get('payload')}")


def cmd_review():
    """Diff-risk checklist. SKIP outside git. Reviewer reads this, not raw diff."""
    if not _git("rev-parse", "--git-dir"):
        print("SKIP: not a git repo.")
        return
    names = _git("diff", "HEAD", "--name-only").splitlines()
    names += [l[3:].strip().strip('"')
              for l in _git("status", "--porcelain").splitlines()
              if l.startswith("??")]
    print(_git("diff", "HEAD", "--stat") or "(no tracked changes)")
    flags = []
    if len(names) > 10:
        flags.append(f"large diff ({len(names)} files) — split slice?")
    deps = {"package.json", "requirements.txt", "pyproject.toml", "go.mod",
            "Cargo.toml", "Gemfile", "package-lock.json"}
    if deps & {Path(n).name for n in names}:
        flags.append("dependency change — lockfile + audit?")
    if any("migrat" in n or "schema" in n for n in names):
        flags.append("migration/schema — rollback plan?")
    if SECRET_RE.search(_git("diff", "HEAD")):
        flags.append("possible secret in diff — remove before merge")
    src = [n for n in names if n.startswith(("src/", "lib/", "app/"))
           or n.endswith((".py", ".ts", ".js", ".go", ".rs", ".java"))]
    tst = [n for n in names if "test" in n or "spec" in n]
    if src and not tst:
        flags.append("no test changes — add one (ladder: one check)")
    print("Checklist:")
    print("1. PROOF commands re-run green on this SHA?")
    print("2. Changes inside lease scope only?")
    for i, f in enumerate(flags, 3):
        print(f"{i}. RISK: {f}")
    if not flags:
        print("3. No risk flags. Verify behavior, merge.")


def main():
    ap = argparse.ArgumentParser(prog="frontier")
    sub = ap.add_subparsers(dest="sub", required=True)
    p = sub.add_parser("init")
    p.add_argument("target", nargs="?", default=".")
    p = sub.add_parser("compact")
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("task_file")
    p = sub.add_parser("lease")
    p.add_argument("cmd", choices=["acquire", "release", "heartbeat", "signal",
                                  "lock", "unlock", "status", "list",
                                  "escalate", "noop"])
    p.add_argument("task", nargs="?", default="")
    p.add_argument("agent", nargs="?", default="")
    p.add_argument("rest", nargs="*")
    p.add_argument("--force", action="store_true",
                   help="acquire despite overlap (forced coexistence, warns)")
    p.add_argument("--ttl", type=int, default=LEASE_TTL,
                   help="lease lifetime seconds (default 300)")
    p = sub.add_parser("validate")
    p.add_argument("tasks_dir", nargs="?", default="docs/TASKS")
    p = sub.add_parser("suggest")
    p.add_argument("text", nargs="+")
    p = sub.add_parser("ctx")
    p.add_argument("symbol", nargs="+")
    p = sub.add_parser("doctor")
    p = sub.add_parser("selftest")
    p = sub.add_parser("handoff")
    p.add_argument("task_file")
    p = sub.add_parser("drift")
    p.add_argument("task")
    p.add_argument("agent")
    p = sub.add_parser("evidence")
    p.add_argument("task")
    p.add_argument("cmd", nargs=argparse.REMAINDER)
    p = sub.add_parser("recall")
    p.add_argument("words", nargs="+")
    p = sub.add_parser("resume")
    p.add_argument("agent")
    p = sub.add_parser("review")
    a = ap.parse_args()
    if a.sub == "init":
        cmd_init(a.target)
    elif a.sub == "compact":
        cmd_compact(a.input, a.output, a.task_file)
    elif a.sub == "lease":
        cmd_lease(a)
    elif a.sub == "validate":
        cmd_validate(a.tasks_dir)
    elif a.sub == "suggest":
        cmd_suggest(a.text)
    elif a.sub == "ctx":
        cmd_ctx(a.symbol)
    elif a.sub == "doctor":
        cmd_doctor()
    elif a.sub == "selftest":
        cmd_selftest()
    elif a.sub == "handoff":
        cmd_handoff(a.task_file)
    elif a.sub == "drift":
        cmd_drift(a.task, a.agent)
    elif a.sub == "evidence":
        cmd_evidence(a.task, a.cmd)
    elif a.sub == "recall":
        cmd_recall(a.words)
    elif a.sub == "resume":
        cmd_resume(a.agent)
    elif a.sub == "review":
        cmd_review()


if __name__ == "__main__":
    main()
