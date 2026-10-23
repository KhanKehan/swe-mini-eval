# -*- coding: utf-8 -*-
"""End-to-end demo of the tool-using loop on a tiny synthetic repository.

    SILICONFLOW_API_KEY=... python examples/run_demo.py          # model-driven
    python examples/run_demo.py --mock                          # scripted, no API

The agent works in `work/repo`; its final patch is applied to a fresh copy in
`work/verify` so the evaluation does not depend on the agent's workspace state.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from swe_mini.agent_loop import run_loop, run_mock
from swe_mini.checker import static_checks
from swe_mini.runner import apply_patch

FIX = """def add(a, b):
    return a + b


def mean(xs):
    return sum(xs) / len(xs)
"""


def sh(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def init_repo(path):
    sh(["git", "init"], path)
    sh(["git", "config", "core.autocrlf", "false"], path)
    sh(["git", "add", "."], path)
    sh(["git", "-c", "user.name=demo", "-c", "user.email=demo@local", "commit", "-m", "base"], path)


def main():
    mock = "--mock" in sys.argv
    work = tempfile.mkdtemp(prefix="swe_demo_")
    repo = os.path.join(work, "repo")
    verify = os.path.join(work, "verify")
    shutil.copytree(os.path.join(ROOT, "examples", "buggy"), repo)
    init_repo(repo)

    task = {
        "instance_id": "demo__add-1",
        "repo": "demo/local",
        "base_commit": "0",
        "problem_statement": "add(2, 3) returns -1 instead of 5. Read pkg/mod.py, fix add, then call submit. Do not change the tests.",
        "hints_text": "",
    }

    if mock:
        patch, traj = run_mock(task, repo, [
            ("read_file", {"path": "pkg/mod.py"}),
            ("write_file", {"path": "pkg/mod.py", "content": FIX}),
            ("submit", {"patch": ""}),
        ])
    else:
        key = os.environ.get("SILICONFLOW_API_KEY", "")
        model = os.environ.get("MODEL", "deepseek-ai/DeepSeek-V3.2")
        patch, traj = run_loop(task, repo, model, "https://api.siliconflow.cn/v1", key, max_steps=6)

    print(json.dumps(traj, indent=1))
    print("patch chars:", len(patch))
    print("patch head:", patch[:400])

    checks, _ = static_checks(task, patch)
    print("static:", checks)

    shutil.copytree(os.path.join(ROOT, "examples", "buggy"), verify)
    init_repo(verify)
    applied = apply_patch(verify, patch) if patch else False
    print("applied to fresh copy:", applied)
    if applied:
        r = sh([sys.executable, "-m", "pytest", "-q"], verify)
        print("pytest exit:", r.returncode)
        print("resolved:", r.returncode == 0)


if __name__ == "__main__":
    main()
