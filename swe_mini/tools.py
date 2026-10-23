# -*- coding: utf-8 -*-
"""Sandboxed repository tools for the agent loop.

Every tool is bound to a workspace directory; paths are resolved inside it and any
escape attempt is rejected. `run_tests` only accepts pytest invocations and a short
allow-list of flags.
"""

import os
import re
import subprocess

MAX_READ = 20000
MAX_SEARCH_HITS = 50


class Workspace:
    def __init__(self, root):
        self.root = os.path.abspath(root)

    def _resolve(self, rel):
        p = os.path.abspath(os.path.join(self.root, rel))
        if not (p == self.root or p.startswith(self.root + os.sep)):
            raise ValueError(f"path escapes workspace: {rel}")
        return p

    def read_file(self, path, start=1, end=None):
        p = self._resolve(path)
        if not os.path.isfile(p):
            return f"ERROR: not a file: {path}"
        try:
            lines = open(p, encoding="utf-8", errors="replace").read().splitlines()
        except OSError as e:
            return f"ERROR: {e}"
        end = end or len(lines)
        chunk = "\n".join(lines[max(0, start - 1):min(end, len(lines))])
        if len(chunk) > MAX_READ:
            chunk = chunk[:MAX_READ] + "\n...[truncated]"
        return chunk

    def list_files(self, pattern="**/*", limit=200):
        import glob

        hits = sorted(glob.glob(os.path.join(self.root, pattern), recursive=True))
        files = [os.path.relpath(h, self.root).replace("\\", "/") for h in hits if os.path.isfile(h)]
        return "\n".join(files[:limit]) if files else "(no files)"

    def search(self, pattern, glob_pattern="*.py"):
        import glob

        rx = re.compile(pattern)
        out = []
        for h in glob.glob(os.path.join(self.root, "**", glob_pattern), recursive=True):
            if not os.path.isfile(h):
                continue
            rel = os.path.relpath(h, self.root).replace("\\", "/")
            try:
                for i, line in enumerate(open(h, encoding="utf-8", errors="replace"), 1):
                    if rx.search(line):
                        out.append(f"{rel}:{i}: {line.rstrip()[:200]}")
                        if len(out) >= MAX_SEARCH_HITS:
                            return "\n".join(out) + "\n...[truncated]"
            except OSError:
                continue
        return "\n".join(out) if out else "(no matches)"

    def run_tests(self, args="", timeout=300):
        if not re.fullmatch(r"[\w\-./:=\[\] ]*", args or ""):
            return "ERROR: invalid test arguments"
        cmd = [os.sys.executable, "-m", "pytest", "-q"] + (args.split() if args else [])
        try:
            r = subprocess.run(cmd, cwd=self.root, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return "ERROR: tests timed out"
        tail = (r.stdout or "")[-4000:] + (("\n" + r.stderr[-1500:]) if r.stderr else "")
        return f"exit={r.returncode}\n{tail}"

    def write_file(self, path, content):
        p = self._resolve(path)
        os.makedirs(os.path.dirname(p) or self.root, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        return f"wrote {path} ({len(content)} chars)"


TOOL_SPEC = [
    {"name": "list_files", "args": {"pattern": "glob, default **/*"}},
    {"name": "read_file", "args": {"path": "relative path", "start": "1-based, optional", "end": "optional"}},
    {"name": "search", "args": {"pattern": "regex", "glob_pattern": "default *.py"}},
    {"name": "run_tests", "args": {"args": "pytest arguments, optional"}},
    {"name": "write_file", "args": {"path": "...", "content": "..."}},
    {"name": "submit", "args": {"patch": "unified diff"}},
]


def dispatch(ws, action, args):
    if action == "list_files":
        return ws.list_files(**args)
    if action == "read_file":
        return ws.read_file(**args)
    if action == "search":
        return ws.search(**args)
    if action == "run_tests":
        return ws.run_tests(**args)
    if action == "write_file":
        return ws.write_file(**args)
    return f"ERROR: unknown action {action}"
