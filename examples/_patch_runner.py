# -*- coding: utf-8 -*-
p = r"C:\Users\27218\Desktop\swe-mini-eval\swe_mini\runner.py"
s = open(p, encoding="utf-8").read()

helper = '''
def normalize_diff(patch):
    """Add `diff --git` headers to plain unified diffs (git apply is strict)."""
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

if "def normalize_diff" not in s:
    s = s.replace("def apply_patch(", helper + "\ndef apply_patch(", 1)

s = s.replace(
    'def apply_patch(repo_dir, patch, check_only=False):\n    if check_only:',
    'def apply_patch(repo_dir, patch, check_only=False):\n    patch = normalize_diff(patch)\n    if check_only:',
)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("normalize_diff added")
