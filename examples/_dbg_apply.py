# -*- coding: utf-8 -*-
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, r"C:\Users\27218\Desktop\swe-mini-eval")
from swe_mini.runner import normalize_diff

src = r"C:\Users\27218\Desktop\swe-mini-eval\examples\buggy"
work = tempfile.mkdtemp(prefix="dbg_")
repo = os.path.join(work, "repo")
shutil.copytree(src, repo)

def sh(cmd):
    r = subprocess.run(cmd, cwd=repo, capture_output=True, text=True)
    print("$", " ".join(cmd), "->", r.returncode)
    if r.stdout.strip():
        print(r.stdout[-400:])
    if r.stderr.strip():
        print("ERR:", r.stderr[-400:])
    return r

sh(["git", "init"])
sh(["git", "config", "core.autocrlf", "false"])
sh(["git", "add", "."])
sh(["git", "-c", "user.name=d", "-c", "user.email=d@d", "commit", "-m", "base"])

patch = """--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -1,4 +1,4 @@
 def add(a, b):
-    return a - b
+    return a + b
 
 def mean(xs):
     return sum(xs) / len(xs)
"""
norm = normalize_diff(patch)
print("--- normalized ---")
print(norm)
p = os.path.join(work, "x.diff")
open(p, "w", encoding="utf-8", newline="\n").write(norm)
sh(["git", "apply", "--check", "-v", p])
print(open(os.path.join(repo, "pkg", "mod.py"), encoding="utf-8").read())
