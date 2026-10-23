# -*- coding: utf-8 -*-
p = r"C:\Users\27218\Desktop\swe-mini-eval\swe_mini\agent_loop.py"
s = open(p, encoding="utf-8").read()

old = """        obs = dispatch(ws, name, args or {})
        traj.append({"step": step, "action": name, "ok": not str(obs).startswith("ERROR"),
                     "obs_chars": len(str(obs))})
    return patch, traj"""
new = """        obs = dispatch(ws, name, args or {})
        traj.append({"step": step, "action": name, "ok": not str(obs).startswith("ERROR"),
                     "obs_chars": len(str(obs))})
    if not patch:
        patch = git_diff(ws.root)
    return patch, traj"""
assert old in s
s = s.replace(old, new, 1)
open(p, "w", encoding="utf-8", newline="\n").write(s)
print("mock git_diff fallback added")
