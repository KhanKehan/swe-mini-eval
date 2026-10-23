# -*- coding: utf-8 -*-
"""Failure taxonomy for SWE-mini runs.

Categories, checked in order:
  empty_patch     no diff returned
  unparseable     diff without file headers or hunks
  test_edit       the patch modifies test files (the harness overwrites them)
  gold_copy       the patch equals the dataset's gold patch (control leak)
  apply_fail      the diff does not apply to the base commit
  tests_fail      the patch applies but FAIL_TO_PASS does not pass
  resolved        FAIL_TO_PASS passes
  not_run         static-only run
"""

import json
import sys


def classify(result):
    c = result.get("checks") or {}
    if not c.get("nonempty"):
        return "empty_patch"
    if not c.get("parseable") or not c.get("has_hunks"):
        return "unparseable"
    if not c.get("no_test_edit"):
        return "test_edit"
    if not c.get("not_gold_copy"):
        return "gold_copy"
    if result.get("applied") is False:
        return "apply_fail"
    if "resolved" in result:
        return "resolved" if result["resolved"] else "tests_fail"
    return "not_run"


def main():
    path = sys.argv[1]
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    counts = {}
    for r in rows:
        k = classify(r)
        counts[k] = counts.get(k, 0) + 1
    n = len(rows)
    print(f"n = {n}")
    for k, v in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"{k:12s} {v:3d}  {v / n:.1%}")


if __name__ == "__main__":
    main()
