# -*- coding: utf-8 -*-
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from swe_mini.checker import is_test_path, parse_diff, static_checks, static_passes, summary
from swe_mini.runner import apply_patch

TASK = {"instance_id": "demo__demo-1", "patch": "diff --git a/gold.py b/gold.py\n--- a/gold.py\n+++ b/gold.py\n@@ -1 +1 @@\n-x\n+y\n"}

GOOD = """diff --git a/pkg/mod.py b/pkg/mod.py
--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -10,3 +10,3 @@ def f():
-    return None
+    return 0
"""

TEST_EDIT = """diff --git a/tests/test_mod.py b/tests/test_mod.py
--- a/tests/test_mod.py
+++ b/tests/test_mod.py
@@ -1 +1 @@
-x
+y
"""


def test_parse_diff_files_and_counts():
    info = parse_diff(GOOD)
    assert info.files == ["pkg/mod.py"]
    assert info.hunks == 1
    assert info.added == 1 and info.removed == 1
    assert info.error == ""


def test_empty_patch_fails():
    checks, info = static_checks(TASK, "")
    assert checks["nonempty"] is False
    assert info.error == "empty"
    assert static_passes(TASK, "") is False


def test_good_patch_passes_static():
    checks, _ = static_checks(TASK, GOOD)
    assert all(checks.values()), checks
    assert static_passes(TASK, GOOD)


def test_test_file_edit_is_rejected():
    checks, _ = static_checks(TASK, TEST_EDIT)
    assert checks["no_test_edit"] is False
    assert is_test_path("tests/test_mod.py")


def test_gold_copy_is_rejected():
    checks, _ = static_checks(TASK, TASK["patch"])
    assert checks["not_gold_copy"] is False


def test_unparseable_diff():
    checks, info = static_checks(TASK, "this is not a diff")
    assert checks["parseable"] is False
    assert info.error == "unparseable"
    assert checks["has_hunks"] is False


def test_summary_aggregates():
    rows = [{"checks": static_checks(TASK, GOOD)[0], "static_pass": True},
            {"checks": static_checks(TASK, "")[0], "static_pass": False}]
    s = summary(rows)
    assert s["n"] == 2
    assert s["all_static_pass"] == 0.5
