# -*- coding: utf-8 -*-
p = r"C:\Users\27218\Desktop\swe-mini-eval\swe_mini\agent_loop.py"
s = open(p, encoding="utf-8").read()

old = '''    try:
        subprocess.run(["git", "add", "-N", "--", "."], cwd=root, capture_output=True, text=True, timeout=60)
        r = subprocess.run(["git", "diff"], cwd=root, capture_output=True, text=True, timeout=60)
        return (r.stdout or "").strip()
    except Exception:
        return ""'''
new = '''    try:
        subprocess.run(["git", "add", "-N", "--", "."], cwd=root, capture_output=True, text=True, timeout=60)
        r = subprocess.run(["git", "diff"], cwd=root, capture_output=True, text=True, timeout=60)
        diff = r.stdout or ""
        keep = []
        for chunk in re.split(r"(?=^diff --git )", diff, flags=re.M):
            if not chunk.strip():
                continue
            head = chunk.splitlines()[0]
            if any(x in head for x in ("__pycache__", ".pyc", ".pytest_cache")):
                continue
            keep.append(chunk)
        return "".join(keep).strip()
    except Exception:
        return ""'''
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("git_diff filters caches")
