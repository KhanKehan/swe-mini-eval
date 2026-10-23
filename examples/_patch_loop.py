# -*- coding: utf-8 -*-
p = r"C:\Users\27218\Desktop\swe-mini-eval\swe_mini\agent_loop.py"
s = open(p, encoding="utf-8").read()

old = '''        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": f"Observation:\\n{str(obs)[:OBS_MAX]}"})
    return patch, traj'''
new = '''        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": f"Observation:\\n{str(obs)[:OBS_MAX]}"})
    if not patch:
        messages.append({"role": "user", "content": "No more tool calls. Return the final patch now as {\\"action\\": \\"submit\\", \\"args\\": {\\"patch\\": \\"...diff...\\"}}."})
        try:
            text = _chat(base_url, api_key, model, messages, max_tokens=max_tokens)
            action = parse_action(text)
            if action and action.get("action") == "submit":
                patch = (action.get("args") or {}).get("patch", "") or extract_diff(text)
            else:
                patch = extract_diff(text)
        except Exception:
            patch = ""
    if not patch:
        patch = git_diff(ws.root)
    return patch, traj'''
assert old in s
s = s.replace(old, new)

helper = '''

def git_diff(root):
    """Fallback: turn direct file edits into a unified diff."""
    import subprocess

    try:
        r = subprocess.run(["git", "diff"], cwd=root, capture_output=True, text=True, timeout=60)
        return (r.stdout or "").strip()
    except Exception:
        return ""
'''
if "def git_diff" not in s:
    s = s.replace("def run_mock(", helper + "\ndef run_mock(", 1)

open(p, "w", encoding="utf-8", newline="\n").write(s)
print("forced final + git diff fallback added")
