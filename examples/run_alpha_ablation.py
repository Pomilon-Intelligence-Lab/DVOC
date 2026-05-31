#!/usr/bin/env python3
"""Compare alpha decay schedules for DVOC.

Conditions:
  - default: 1.0 -> 0.5 -> 0.25 (current DVOC)
  - constant05: alpha = 0.5 always
  - undamped: alpha = 1.0 always

Usage:
    python examples/run_alpha_ablation.py --models gemini-3.1-flash-lite --quick
"""

import os, sys, time, argparse, json, random
from collections import defaultdict
from dataclasses import asdict

from benchmark.config import MODELS, START_POSITIONS
from benchmark.engine import DVALExecutor, RateLimitError, QuotaError
from benchmark.tasks import synthetic as synth_tasks

ALPHA_SCHEDULES = ["default", "constant05", "undamped"]
_TRIAL_DELAY = 5.0


def find_tasks(task_ids):
    lookup = {}
    for t_fn in synth_tasks.ALL:
        t = t_fn()
        lookup[t.id] = t
    return [lookup[tid] for tid in task_ids if tid in lookup]


def main():
    parser = argparse.ArgumentParser(description="Alpha schedule ablation")
    parser.add_argument("--models", nargs="+", default=["gemini-3.1-flash-lite"])
    parser.add_argument("--tasks", nargs="+", default=[f"S{i}" for i in range(1, 7)])
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--repeats", type=int, default=0)
    parser.add_argument("--initial-wait", type=float, default=0)
    args = parser.parse_args()

    if args.initial_wait > 0:
        print(f"Waiting {args.initial_wait:.0f}s...", flush=True)
        time.sleep(args.initial_wait)

    repeats = args.repeats or (1 if args.quick else 3)
    tasks = find_tasks(args.tasks)
    if not tasks:
        print(f"No tasks found for: {args.tasks}")
        sys.exit(1)

    pending = []
    for mk in args.models:
        if mk not in MODELS:
            continue
        for task_obj in tasks:
            for schedule in ALPHA_SCHEDULES:
                for pos_idx, (sx, sy) in enumerate(START_POSITIONS):
                    for rep in range(repeats):
                        pending.append((mk, task_obj, schedule, pos_idx, rep, (sx, sy)))

    random.shuffle(pending)
    total = len(pending)
    print(f"Alpha ablation: {total} trials ({len(args.models)} models x {len(tasks)} tasks x "
          f"{len(ALPHA_SCHEDULES)} schedules x {len(START_POSITIONS)} x {repeats})")

    model_dead = {}
    results = []
    backoff = 60.0
    out_path = os.path.join(os.path.dirname(__file__), "benchmark", "output", "alpha_ablation.json")

    def save_partial():
        with open(out_path, "w") as f:
            json.dump([asdict(r) for r in results], f, indent=2)

    while pending:
        pending = [p for p in pending if not model_dead.get(p[0])]
        if not pending:
            break

        mk, task_obj, schedule, pos_idx, rep, (sx, sy) = pending.pop(0)
        label = f"{schedule:12s} {mk:25s} {task_obj.id:4s} p{pos_idx+1}.{rep+1}"
        print(f"  [{len(results)}/{total}] {label}", end=" ", flush=True)

        cfg = MODELS[mk]
        model_name = cfg.get("names", [cfg["name"]]) if "names" in cfg else [cfg["name"]]

        executor = DVALExecutor(
            model_name=model_name, model_key=mk,
            capture_fn=lambda t=task_obj: t.img.copy(),
            target=task_obj.target, task_prompt=task_obj.prompt,
            task_id=task_obj.id, start_pos=(sx, sy), saver=None,
            target_w=task_obj.target_w, target_h=task_obj.target_h,
            overlay_mode="full", predict_mode="relative",
            alpha_schedule=schedule,
        )

        try:
            r = executor.run()
            results.append(r)
            save_partial()
            backoff = 60.0
            dist = r.final_dist
            status = "PASS" if r.success else "FAIL"
            print(f"{status} d={dist:.0f} i={r.iterations}", flush=True)
        except QuotaError as e:
            model_dead[mk] = True
            print(f"DEAD {str(e)[:60]}", flush=True)
        except RateLimitError:
            pending.append((mk, task_obj, schedule, pos_idx, rep, (sx, sy)))
            wait = backoff
            backoff = min(backoff * 2, 600)
            print(f"RATE_LIMIT (wait {wait:.0f}s)", flush=True)
            time.sleep(wait)
            continue
        except Exception as e:
            print(f"ERR {str(e)[:80]}", flush=True)
            save_partial()

        time.sleep(_TRIAL_DELAY)

    save_partial()
    print(f"\nSaved {len(results)} trials to {out_path}")

    print("\n" + "=" * 80)
    print("ALPHA SCHEDULE RESULTS")
    print("=" * 80)
    for mk in args.models:
        print(f"\n--- {mk} ---")
        print(f"{'Schedule':<14} {'Total':>6} {'Valid':>6} {'OK':>6} {'Raw%':>6} {'MnDist':>8} {'MnIt':>5}")
        print("-" * 51)
        for s in ALPHA_SCHEDULES:
            trials = [r for r in results if r.model_key == mk and r.alpha_schedule == s]
            if not trials:
                continue
            valid = [r for r in trials if r.final_dist < 900]
            n, nv = len(trials), len(valid)
            succ = sum(1 for r in valid if r.success)
            raw = succ / max(n, 1) * 100
            md = sum(r.final_dist for r in valid) / max(nv, 1) if nv else 0
            mi = sum(r.iterations for r in valid) / max(nv, 1) if nv else 0
            print(f"{s:<14} {n:>6} {nv:>6} {succ:>6} {raw:>5.0f}% {md:>7.0f}px {mi:>4.1f}")


if __name__ == "__main__":
    main()
