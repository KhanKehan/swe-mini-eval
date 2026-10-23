# -*- coding: utf-8 -*-
"""Patch-proposal baseline over an OpenAI-compatible API.

Single-shot by design: the model receives the issue text and returns a unified diff.
Tool use (read_file / search / run_tests) is the natural next iteration; the hook is
`TOOLS` below so the loop can be extended without touching the CLI.
"""

import json
import os
import re
import time

import requests

PROMPT = """You are fixing a GitHub issue in the repository {repo} at commit {commit}.

Issue:
{problem}

Hints:
{hints}

Return ONLY a unified diff (git format) that resolves the issue. Do not modify tests.
Start the diff with `diff --git`."""

DIFF_RE = re.compile(r"```(?:diff)?\s*(diff --git .*?)```", re.S)
TOOLS = ("read_file", "search", "run_tests")


def extract_diff(text):
    if not text:
        return ""
    m = DIFF_RE.search(text)
    if m:
        return m.group(1).strip()
    i = text.find("diff --git")
    if i >= 0:
        return text[i:].strip()
    return ""


def _chat(base_url, api_key, model, messages, max_tokens=2000, temperature=0.0):
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {"model": model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    last = None
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, headers=headers, timeout=240)
            if r.status_code == 200:
                return r.json()["choices"][0]["message"].get("content") or ""
            last = f"HTTP {r.status_code}: {r.text[:200]}"
        except Exception as e:  # noqa: BLE001
            last = repr(e)
        time.sleep(2 ** attempt)
    raise RuntimeError(last)


def propose_patch(task, model, base_url, api_key, max_tokens=2000):
    prompt = PROMPT.format(repo=task["repo"], commit=task["base_commit"],
                           problem=task.get("problem_statement", ""), hints=task.get("hints_text", "") or "(none)")
    text = _chat(base_url, api_key, model, [{"role": "user", "content": prompt}], max_tokens=max_tokens)
    return extract_diff(text), text


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--base-url", default="https://api.siliconflow.cn/v1")
    ap.add_argument("--api-key-env", default="SILICONFLOW_API_KEY")
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    key = os.environ.get(args.api_key_env, "")
    rows = [json.loads(l) for l in open(args.tasks, encoding="utf-8") if l.strip()]
    if args.limit:
        rows = rows[: args.limit]
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for i, task in enumerate(rows):
            try:
                patch, raw = propose_patch(task, args.model, args.base_url, key)
            except Exception as e:  # noqa: BLE001
                patch, raw = "", f"ERROR {e!r}"
            f.write(json.dumps({"instance_id": task["instance_id"], "patch": patch, "raw": raw[:4000]}, ensure_ascii=False) + "\n")
            f.flush()
            print(f"[{i + 1}/{len(rows)}] {task['instance_id']} patch_chars={len(patch)}", flush=True)


if __name__ == "__main__":
    main()
