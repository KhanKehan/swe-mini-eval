# -*- coding: utf-8 -*-
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swe_mini.agent_loop import parse_action, run_mock
from swe_mini.tools import Workspace


@pytest.fixture()
def repo(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "mod.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text(
        "from pkg.mod import add\n\ndef test_add():\n    assert add(2, 3) == 5\n", encoding="utf-8")
    return tmp_path


def test_read_write_list(repo):
    ws = Workspace(repo)
    text = ws.read_file("pkg/mod.py")
    assert "return a - b" in text
    assert "pkg/mod.py" in ws.list_files()
    assert "add" in ws.search("def add")


def test_path_escape_rejected(repo):
    ws = Workspace(repo)
    with pytest.raises(ValueError):
        ws.read_file("../outside.txt")


def test_run_tests_reports_failure(repo):
    ws = Workspace(repo)
    out = ws.run_tests("tests/test_mod.py")
    assert "exit=1" in out


def test_run_tests_rejects_shell(repo):
    ws = Workspace(repo)
    assert ws.run_tests("; rm -rf /").startswith("ERROR")


def test_parse_action():
    assert parse_action('{"action": "read_file", "args": {"path": "a.py"}}')["action"] == "read_file"
    assert parse_action("no json") is None
    assert parse_action('{"args": {}}') is None


def test_mock_loop(repo):
    patch, traj = run_mock(
        {"instance_id": "t", "repo": "x/y", "base_commit": "0", "problem_statement": "fix"},
        str(repo),
        [("list_files", {}), ("read_file", {"path": "pkg/mod.py"}),
         ("submit", {"patch": "diff --git a/pkg/mod.py b/pkg/mod.py\n"})],
    )
    assert patch.startswith("diff --git")
    assert [t["action"] for t in traj] == ["list_files", "read_file", "submit"]
