# -*- coding: utf-8 -*-
"""Patch-level checks for SWE-bench-style tasks.

Two layers:

* static checks (no environment): the patch is non-empty, parses as a unified diff,
  does not edit test files (the official harness overwrites tests with the test patch),
  and does not copy the gold patch;
* optional execution: apply the patch to a repo checkout and run the FAIL_TO_PASS /
  PASS_TO_PASS commands (requires a prepared environment; see runner.py).

The static layer is the one used by the CI tests and by the report on this machine.
"""

import re
from dataclasses import dataclass, field


@dataclass
class PatchInfo:
    files: list = field(default_factory=list)
    added: int = 0
    removed: int = 0
    hunks: int = 0
    error: str = ""


def parse_diff(patch):
    info = PatchInfo()
    if not patch or not patch.strip():
        info.error = "empty"
        return info
    lines = patch.splitlines()
    for line in lines:
        if line.startswith("diff --git "):
            m = re.match(r"diff --git a/(\S+) b/(\S+)", line)
            if m:
                info.files.append(m.group(2))
        elif line.startswith("+++ b/") and (not info.files or info.files[-1] != line[6:].strip()):
            info.files.append(line[6:].strip())
        elif line.startswith("@@"):
            info.hunks += 1
        elif line.startswith("+") and not line.startswith("+++"):
            info.added += 1
        elif line.startswith("-") and not line.startswith("---"):
            info.removed += 1
    if not info.files:
        info.error = "unparseable"
    return info


def is_test_path(path):
    p = path.lower()
    return (
        "/test" in p
        or p.startswith("test")
        or "/tests/" in p
        or p.endswith("_test.py")
        or p.startswith("testing/")
    )


def static_checks(task, patch):
    info = parse_diff(patch)
    checks = {
        "nonempty": bool(patch and patch.strip()),
        "parseable": info.error == "",
        "no_test_edit": all(not is_test_path(f) for f in info.files),
        "not_gold_copy": (patch or "").strip() != (task.get("patch") or "").strip(),
        "has_hunks": info.hunks > 0,
    }
    return checks, info


def static_passes(task, patch):
    checks, _ = static_checks(task, patch)
    return all(checks.values())


def summary(rows):
    """Aggregate a list of per-task result dicts."""
    n = len(rows)
    if not n:
        return {}
    keys = ["nonempty", "parseable", "no_test_edit", "not_gold_copy", "has_hunks"]
    out = {"n": n}
    for k in keys:
        out[k] = round(sum(1 for r in rows if r["checks"].get(k)) / n, 3)
    out["all_static_pass"] = round(sum(1 for r in rows if r["static_pass"]) / n, 3)
    return out
