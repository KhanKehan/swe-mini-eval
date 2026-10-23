# -*- coding: utf-8 -*-
"""Evaluate patch files against a frozen task set.

Patches file: JSONL with {"instance_id": str, "patch": str}. Missing ids are treated
as empty patches so the denominator stays fixed.
"""

import argparse
import json
import os

from .checker import summary
from .runner import evaluate


def load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True)
    ap.add_argument("--patches", required=True)
    ap.add_argument("--mode", default="static", choices=["static", "execute"])
    ap.add_argument("--out", default="")
    args = ap.parse_args()

    tasks = load_jsonl(args.tasks)
    patch_map = {r["instance_id"]: r.get("patch", "") for r in load_jsonl(args.patches)}
    rows = []
    for t in tasks:
        patch = patch_map.get(t["instance_id"], "")
        r = evaluate(t, patch, mode=args.mode)
        rows.append(r)
        print(f"{t['instance_id']:40s} static_pass={r['static_pass']} "
              f"files={len(r['patch_info']['files'])} hunks={r['patch_info']['hunks']}")
    print(json.dumps(summary(rows), indent=2))
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
