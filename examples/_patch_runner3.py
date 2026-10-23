# -*- coding: utf-8 -*-
p = r"C:\Users\27218\Desktop\swe-mini-eval\swe_mini\runner.py"
s = open(p, encoding="utf-8").read()

start = s.find("def normalize_diff")
end = s.find("def apply_patch", start)
assert start >= 0 and end > start

new_fn = '''def normalize_diff(patch):
    """Repair hunk counts and add `diff --git` headers when they are missing."""
    patch = repair_hunks(patch)
    lines = patch.splitlines()
    out, i = [], 0
    has_header = False
    while i < len(lines):
        line = lines[i]
        if line.startswith("diff --git "):
            has_header = True
            out.append(line)
            i += 1
            continue
        if line.startswith("--- a/") and i + 1 < len(lines) and lines[i + 1].startswith("+++ b/"):
            if not has_header:
                path = line[6:].strip()
                out.append(f"diff --git a/{path} b/{path}")
            has_header = False
        out.append(line)
        i += 1
    return "\\n".join(out) + "\\n"


'''

s = s[:start] + new_fn + s[end:]
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("normalize_diff rewritten")
