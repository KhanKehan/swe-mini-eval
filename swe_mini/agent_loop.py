# -*- coding: utf-8 -*-
"""Tool-using agent loop (ReAct-style) over a repository workspace.

The model answers with a JSON object per step:

    {"action": "read_file", "args": {"path": "pkg/mod.py"}}
    ...
    {"action": "submit", "args": {"patch": "diff --git ..."}}

Every observation is appended to the conversation and to a trajectory log, which is
what `analyze` uses to separate capability failures from harness failures.
"""

import json
import re
import time

from .agent import _chat, extract_diff
from .tools import TOOL_SPEC, Workspace, dispatch

SYSTEM = """You are a coding agent fixing a GitHub issue in a repository checkout.
You can call tools. Reply with exactly one JSON object per turn:
  {"action": "<tool>", "args": {...}}
Tools: {tools}
Prefer editing the repository directly with write_file; the harness captures your edits.
When the fix is in place, call submit with the final unified diff (it may be empty if the
files are already edited). Never modify tests. Do not write anything outside the JSON object."""

OBS_MAX = 4000


def _tool_text():
    return "; ".join(f"{t['name']}({', '.join(t['args'].keys())})" for t in TOOL_SPEC)


def parse_action(text):
    if not text:
        return None
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or "action" not in obj:
        return None
    obj.setdefault("args", {})
    if not isinstance(obj["args"], dict):
        return None
    return obj


def run_loop(task, workspace, model, base_url, api_key, max_steps=8, max_tokens=1500, log=print):
    ws = Workspace(workspace)
    messages = [
        {"role": "system", "content": SYSTEM.replace("{tools}", _tool_text())},
        {"role": "user", "content": f"Repository: {task['repo']} at {task['base_commit']}\n\nIssue:\n{task.get('problem_statement','')}\n\nHints:\n{task.get('hints_text') or '(none)'}"},
    ]
    traj = []
    patch = ""
    for step in range(max_steps):
        t0 = time.time()
        text = _chat(base_url, api_key, model, messages, max_tokens=max_tokens)
        action = parse_action(text)
        if action is None:
            # allow a bare diff as the final answer
            patch = extract_diff(text)
            traj.append({"step": step, "action": "freeform", "ok": bool(patch), "secs": round(time.time() - t0, 1)})
            break
        name, args = action["action"], action.get("args", {})
        if name == "submit":
            patch = (args.get("patch") or "").strip() or extract_diff(text)
            traj.append({"step": step, "action": "submit", "ok": bool(patch), "secs": round(time.time() - t0, 1)})
            break
        try:
            obs = dispatch(ws, name, args)
            ok = not str(obs).startswith("ERROR")
        except Exception as e:  # noqa: BLE001
            obs, ok = f"ERROR: {e!r}", False
        traj.append({"step": step, "action": name, "args": {k: str(v)[:60] for k, v in args.items()},
                     "ok": ok, "obs_chars": len(str(obs)), "secs": round(time.time() - t0, 1)})
        log(f"step {step}: {name} ok={ok} obs={len(str(obs))} chars")
        messages.append({"role": "assistant", "content": text})
        messages.append({"role": "user", "content": f"Observation:\n{str(obs)[:OBS_MAX]}"})
    if not patch:
        messages.append({"role": "user", "content": "No more tool calls. Return the final patch now as {\"action\": \"submit\", \"args\": {\"patch\": \"...diff...\"}}."})
        try:
            text = _chat(base_url, api_key, model, messages, max_tokens=max_tokens)
            action = parse_action(text)
            if action and action.get("action") == "submit":
                patch = (action.get("args") or {}).get("patch", "") or extract_diff(text)
            else:
                patch = extract_diff(text)
        except Exception:
            patch = ""
    ws_patch = git_diff(ws.root)
    if ws_patch:
        # the agent's direct edits are the ground truth; their context always matches
        patch = ws_patch
    return patch, traj




def git_diff(root):
    """Fallback: turn direct file edits into a unified diff."""
    import subprocess

    try:
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
        return ""

def run_mock(task, workspace, script, max_steps=8):
    """Test the loop without an API: `script` is a list of (action, args) tuples."""
    ws = Workspace(workspace)
    traj = []
    patch = ""
    for step, (name, args) in enumerate(script[:max_steps]):
        if name == "submit":
            patch = (args.get("patch", "") if isinstance(args, dict) else "")
            traj.append({"step": step, "action": "submit", "ok": bool(patch)})
            break
        obs = dispatch(ws, name, args or {})
        traj.append({"step": step, "action": name, "ok": not str(obs).startswith("ERROR"),
                     "obs_chars": len(str(obs))})
    if not patch:
        patch = git_diff(ws.root)
    return patch, traj
