# swe-mini-eval

A small, reproducible SWE-bench-style evaluation harness: freeze a task subset, collect
model patches, run a layered checker, and classify failures. It is the coding-agent
counterpart of the scientific benchmark work in `CycloBench` and is built for the
AI4SE evaluation internship (Coding LLM / Agent evaluation).

## Why this project

The JD asks for: benchmark construction, a stable Checker/Judge, agent-trajectory and
failure analysis, and a reproducible harness. This repo implements those four pieces on
SWE-bench Lite:

| JD requirement | Where it lives |
|---|---|
| Task subset + evaluation set construction | `swe_mini/data.py` (deterministic 20-task freeze) |
| Checker / Judge | `swe_mini/checker.py` (static) + `swe_mini/runner.py` (apply + tests) |
| Failure analysis | `swe_mini/analyze.py` (8-way taxonomy) |
| Harness / reproducibility | JSONL outputs, frozen tasks, pytest suite |

## Status

- [x] 20 SWE-bench Lite tasks frozen (`data/tasks.jsonl`, seed 0)
- [x] Static checker with 5 checks (non-empty, parseable, no test edit, no gold copy, has hunks)
- [x] 7 pytest tests (diff parsing, each rejection case, aggregation)
- [x] Controls: gold patches pass every check except the gold-copy guard; empty and test-edit
      patches are rejected
- [ ] Execution mode on a prepared environment (clone + `git apply` + FAIL_TO_PASS)
- [ ] Single-shot patch baseline over an API
- [ ] Tool-using agent (read / search / run tests)

Control table (20 tasks):

| probe | nonempty | parseable | no_test_edit | not_gold_copy | has_hunks |
|---|---:|---:|---:|---:|---:|
| gold patch | 1.00 | 1.00 | 1.00 | 0.00 (by design) | 1.00 |
| empty patch | 0.00 | 0.00 | 1.00 | 1.00 | 0.00 |
| test-file edit | 1.00 | 1.00 | 0.00 | 1.00 | 1.00 |

## Quick start

```bash
pip install -r requirements.txt

# 1) freeze the task subset (HF mirror in mainland)
HF_ENDPOINT=https://hf-mirror.com python swe_mini/data.py 20 data/tasks.jsonl

# 2) static evaluation of a patch file (JSONL: {"instance_id", "patch"})
python -m swe_mini.run_static --tasks data/tasks.jsonl --patches out/gold.jsonl

# 3) propose patches with any OpenAI-compatible API
SILICONFLOW_API_KEY=... python -m swe_mini.agent \
  --tasks data/tasks.jsonl --model Qwen/Qwen3-32B --out out/qwen3.jsonl
```

## Design notes

- **Test-file guard.** The official harness overwrites tests with the test patch; a model
  patch that edits tests is rejected rather than rewarded.
- **Gold-copy guard.** For our own runs the dataset's gold patch must never count as a
  correct answer; the control table uses it only to validate the parser.
- **Layered checking.** Static checks are cheap and run on every patch; execution
  (`runner.evaluate(..., mode="execute")`) clones the repo, applies the patch and runs
  FAIL_TO_PASS. Environment preparation is intentionally left to the caller.
- **Failure taxonomy.** `empty_patch → unparseable → test_edit → gold_copy → apply_fail →
  tests_fail → resolved`, so the report separates agent capability from harness errors.

## Limitations

Static checks do not prove correctness; they only filter malformed or cheating patches.
Execution mode is scaffolded but not yet run at scale on this machine (no Docker
environment for the repos). The single-shot baseline is a floor, not a competitive agent.

## Smoke run (2026-10-22)

- Single-shot DeepSeek-V3.2 on 2 of the 20 tasks: both returned a parseable diff
  (2191 and 1166 characters); the static checker accepted both (no test-file edits).
- Static acceptance over the full 20-task set with only those two patches: 10%.
- The gold control passes 4/5 checks (the gold-copy guard fires by design); the empty
  control passes 0/3 of the content checks.

## Baseline results (20 tasks, single-shot DeepSeek-V3.2)

| metric | value |
|---|---:|
| non-empty, parseable patches | 16/20 (80%) |
| empty patches | 4/20 (20%) |
| test-file edits | 0 |
| gold copies | 0 |
| static acceptance | **80%** |

Execution mode (apply + FAIL_TO_PASS) is not run yet; the static acceptance is an upper
bound on what the same patches could resolve.
