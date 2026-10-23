# -*- coding: utf-8 -*-
"""Optional execution layer: clone, apply a patch, run the task's tests.

The official SWE-bench harness builds a Docker image per task. This runner keeps the
same interface but leaves environment preparation to the caller: pass a prepared
repository checkout (or let it shallow-clone at the base commit) and a command
template. It is used for the test-mode evaluation; the CI only exercises the parsers.
"""

import os
import shutil
import subprocess
import tempfile


def _run(cmd, cwd=None, timeout=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)


def prepare_repo(repo, base_commit, workdir=None, depth=50):
    workdir = workdir or tempfile.mkdtemp(prefix="swe_mini_")
    dest = os.path.join(workdir, repo.split("/")[-1])
    if not os.path.isdir(dest):
        url = f"https://github.com/{repo}.git"
        r = _run(["git", "clone", "--filter=blob:none", "--no-checkout", url, dest], timeout=1200)
        if r.returncode:
            raise RuntimeError(f"clone failed: {r.stderr[-400:]}")
        r = _run(["git", "-C", dest, "fetch", "--depth", str(depth), "origin", base_commit], timeout=1200)
        if r.returncode:
            raise RuntimeError(f"fetch failed: {r.stderr[-400:]}")
    r = _run(["git", "-C", dest, "checkout", "-f", base_commit], timeout=600)
    if r.returncode:
        raise RuntimeError(f"checkout failed: {r.stderr[-400:]}")
    return dest


def apply_patch(repo_dir, patch, check_only=False):
    if check_only:
        return _run(["git", "-C", repo_dir, "apply", "--check", "-"], timeout=120).returncode == 0
    with tempfile.NamedTemporaryFile("w", suffix=".diff", delete=False, encoding="utf-8") as f:
        f.write(patch)
        path = f.name
    try:
        ok = _run(["git", "-C", repo_dir, "apply", "--check", path], timeout=120).returncode == 0
        if not ok:
            return False
        r = _run(["git", "-C", repo_dir, "apply", path], timeout=120)
        return r.returncode == 0
    finally:
        os.unlink(path)


def run_tests(repo_dir, tests, timeout=1800):
    """Run a list of pytest node ids; returns (passed, failed, output tail)."""
    if not tests:
        return [], [], ""
    r = _run(["python", "-m", "pytest", "-q"] + list(tests), cwd=repo_dir, timeout=timeout)
    tail = (r.stdout or "")[-3000:] + (("\n" + r.stderr[-1000:]) if r.stderr else "")
    passed, failed = [], []
    for line in (r.stdout or "").splitlines():
        if " PASSED" in line:
            passed.append(line.split("::")[-1].split()[0])
        if " FAILED" in line:
            failed.append(line.split("::")[-1].split()[0])
    return passed, failed, tail


def evaluate(task, patch, mode="static", timeout=1800):
    """mode='static' checks only the diff; mode='execute' also runs the tests."""
    from .checker import static_checks

    checks, info = static_checks(task, patch)
    result = {"instance_id": task["instance_id"], "checks": checks, "static_pass": all(checks.values()),
              "patch_info": {"files": info.files, "added": info.added, "removed": info.removed,
                             "hunks": info.hunks, "error": info.error}}
    if mode != "execute" or not result["static_pass"]:
        return result
    repo_dir = prepare_repo(task["repo"], task["base_commit"])
    applied = apply_patch(repo_dir, patch)
    result["applied"] = applied
    if not applied:
        return result
    passed, failed, tail = run_tests(repo_dir, task.get("FAIL_TO_PASS", []), timeout=timeout)
    result.update({"fail_to_pass_passed": len(passed), "fail_to_pass_total": len(task.get("FAIL_TO_PASS", [])),
                   "output_tail": tail})
    result["resolved"] = len(failed) == 0 and len(task.get("FAIL_TO_PASS", [])) > 0
    shutil.rmtree(os.path.dirname(repo_dir), ignore_errors=True)
    return result
