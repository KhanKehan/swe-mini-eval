# -*- coding: utf-8 -*-
"""Load SWE-bench Lite tasks and freeze a deterministic subset."""

import json
import os
import random

from datasets import load_dataset

DEFAULT_N = 20


def load_tasks(n=DEFAULT_N, seed=0, split="test"):
    ds = load_dataset("princeton-nlp/SWE-bench_Lite", split=split)
    ids = sorted(ds["instance_id"])
    rng = random.Random(seed)
    pick = set(rng.sample(ids, min(n, len(ids))))
    rows = [dict(r) for r in ds if r["instance_id"] in pick]
    rows.sort(key=lambda r: r["instance_id"])
    for r in rows:
        r["FAIL_TO_PASS"] = json.loads(r["FAIL_TO_PASS"]) if isinstance(r["FAIL_TO_PASS"], str) else r["FAIL_TO_PASS"]
        r["PASS_TO_PASS"] = json.loads(r["PASS_TO_PASS"]) if isinstance(r["PASS_TO_PASS"], str) else r["PASS_TO_PASS"]
    return rows


def save_tasks(rows, path):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_frozen(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


if __name__ == "__main__":
    import sys

    n = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_N
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "..", "data", "tasks.jsonl")
    rows = load_tasks(n=n)
    save_tasks(rows, out)
    print(f"wrote {len(rows)} tasks to {out}")
    for r in rows[:5]:
        print(r["instance_id"], r["repo"], len(r["FAIL_TO_PASS"]))
