# -*- coding: utf-8 -*-
"""Add hunk-count repair and git headers so model diffs apply reliably."""

p = r"C:\Users\27218\Desktop\swe-mini-eval\swe_mini\runner.py"
s = open(p, encoding="utf-8").read()

helper = '''
import re as _re

_HUNK = _re.compile(r"^@@ -(\\d+)(?:,(\\d+))? \\+(\\d+)(?:,(\\d+))? @@(.*)$")


def repair_hunks(patch):
    """Recompute hunk line counts when a model writes them inconsistently."""
    lines = patch.splitlines()
    out, i = [], 0
    while i < len(lines):
        m = _HUNK.match(lines[i])
        if not m:
            out.append(lines[i]); i += 1; continue
        start_old, _, start_new, _, tail = m.groups()
        body, j = [], i + 1
        while j < len(lines) and not _HUNK.match(lines[j]) and not lines[j].startswith("diff --git "):
            body.append(lines[j]); j += 1
        old = sum(1 for l in body if (l.startswith(" ") or l.startswith("-")) and not l.startswith("---"))
        new = sum(1 for l in body if (l.startswith(" ") or l.startswith("+")) and not l.startswith("+++"))
        out.append(f"@@ -{start_old},{old} +{start_new},{new} @@{tail}")
        out.extend(body)
        i = j
    return "\\n".join(out) + "\\n"


def normalize_diff(patch):
    """Repair hunk counts and add `diff --git` headers (git apply is strict)."""
    patch = repair_hunks(patch)
    lines = patch.splitlines()
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("--- a/") and i + 1 < len(lines) and lines[i + 1].startswith("+++ b/"):
            path = line[6:].strip()
            if not out or not out[-1].startswith("diff --git "):
                out.append(f"diff --git a/{path} b/{path}")
        out.append(line)
        i += 1
    return "\\n".join(out) + "\\n"
'''

# replace the old normalize_diff block if present
if "def repair_hunks" not in s:
    start = s.find("def normalize_diff")
    if start >= 0:
        s = s[:start] + helper.strip() + "\n\n" + s[s.find("def apply_patch", start):]
    else:
        s = s.replace("def apply_patch(", helper.strip() + "\n\n\ndef apply_patch(", 1)

s = s.replace(
    'def apply_patch(repo_dir, patch, check_only=False):\n    patch = normalize_diff(patch)\n    if check_only:',
    'def apply_patch(repo_dir, patch, check_only=False):\n    patch = normalize_diff(patch)\n    if check_only:',
)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("repair_hunks added")
