# -*- coding: utf-8 -*-
p = r"C:\Users\27218\Desktop\swe-mini-eval\swe_mini\agent_loop.py"
s = open(p, encoding="utf-8").read()

old = """    if not patch:
        patch = git_diff(ws.root)
    return patch, traj"""
new = """    ws_patch = git_diff(ws.root)
    if ws_patch:
        # the agent's direct edits are the ground truth; their context always matches
        patch = ws_patch
    return patch, traj"""
assert old in s, "anchor not found"
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("prefer workspace diff")
