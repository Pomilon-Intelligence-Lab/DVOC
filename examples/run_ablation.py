#!/usr/bin/env python3
"""DVOC overlay-mode ablation with resilient scheduling.

Usage:
    python examples/run_ablation.py --models gemini-3.1-flash-lite --quick
    python examples/run_ablation.py --models gemini-3.1-flash-lite gemma-4-26b
"""

import os, sys, time, argparse, json, random
from collections import defaultdict
from dataclasses import asdict

from benchmark.config import MODELS, START_POSITIONS
from benchmark.engine import DVALExecutor, RateLimitError, QuotaError
from benchmark.tasks import synthetic as synth_tasks

OVERLAY_MODES = ["full", "crosshair-only", "none"]
_TRIAL_DELAY = 3.0

def find_tasks(task_ids):
    lookup = {}
    for t_fn in synth_tasks.ALL:
        t = t_fn()
        lookup[t.id] = t
    return [lookup[tid] for tid in task_ids if tid in lookup]

def main():
    parser = argparse.ArgumentParser(description="DVOC overlay-mode ablation")
    parser.add_argument("--models", nargs="+", default=["gemini-3.1-flash-lite"])
    parser.add_argument("--tasks", nargs="+", default=[f"S{i}" for i in range(1, 7)])
    parser.add_argument("--quick", action="store_true", help="1 repeat per position")
    parser.add_argument("--repeats", type=int, default=0)
    args = parser.parse_args()

    repeats = args.repeats or (1 if args.quick else 3)
    tasks = find_tasks(args.tasks)
    if not tasks:
        print(f"No tasks found for: {args.tasks}")
        sys.exit(1)

    # Build pending queue
    pending = []
    for mk in args.models:
        if mk not in MODELS:
            print(f"Skipping {mk}: not in config")
            continue
        for task_obj in tasks:
            for mode in OVERLAY_MODES:
                for pos_idx, (sx, sy) in enumerate(START_POSITIONS):
                    for rep in range(repeats):
                        pending.append((mk, task_obj, mode, pos_idx, rep, (sx, sy)))

    random.shuffle(pending)
    total = len(pending)
    print(f"Ablation: {total} trials ({len(args.models)} models × {len(tasks)} tasks × "
          f"{len(OVERLAY_MODES)} modes × {len(START_POSITIONS)} positions × {repeats} reps)")

    model_dead = {}
    results = []
    out_path = os.path.join(os.path.dirname(__file__), "benchmark", "output", "ablation_results.json")

    def save_partial():
        with open(out_path, "w") as f:
            json.dump([asdict(r) for r in results], f, indent=2)

    while pending:
        # Filter out dead models
        pending = [p for p in pending if not model_dead.get(p[0])]
        if not pending:
            break

        mk, task_obj, mode, pos_idx, rep, (sx, sy) = pending.pop(0)
        label = f"{mode:15s} {mk:25s} {task_obj.id:4s} p{pos_idx+1}.{rep+1}"
        print(f"  {label}", end=" ", flush=True)

        cfg = MODELS[mk]
        model_name = cfg.get("names", [cfg["name"]]) if "names" in cfg else [cfg["name"]]

        executor = DVALExecutor(
            model_name=model_name, model_key=mk,
            capture_fn=lambda t=task_obj: t.img.copy(),
            target=task_obj.target, task_prompt=task_obj.prompt,
            task_id=task_obj.id, start_pos=(sx, sy), saver=None,
            target_w=task_obj.target_w, target_h=task_obj.target_h,
            overlay_mode=mode,
        )

        try:
            r = executor.run()
            results.append(r)
            save_partial()
            dist = r.final_dist
            status = "PASS" if r.success else "FAIL"
            print(f"{status} d={dist:.0f} i={r.iterations}", flush=True)
        except QuotaError as e:
            model_dead[mk] = True
            print(f"DEAD {str(e)[:60]}", flush=True)
        except RateLimitError:
            pending.append((mk, task_obj, mode, pos_idx, rep, (sx, sy)))
            print("RATE_LIMIT (re-queued)", flush=True)
            time.sleep(15)
            continue
        except Exception as e:
            print(f"ERR {str(e)[:80]}", flush=True)
            # Save partial results even on error
            save_partial()

        time.sleep(_TRIAL_DELAY)

    # Report
    print("\n" + "=" * 80)
    print("ABLATION RESULTS")
    print("=" * 80)
    for mk in args.models:
        if model_dead.get(mk):
            print(f"\n  {mk}: DEAD (quota exceeded)")
        print(f"\n--- {mk} ---")
        print(f"{'Mode':<20} {'Total':>6} {'Valid':>6} {'OK':>6} {'Raw%':>6} {'Proto%':>7} {'MnDist':>8} {'MnIt':>5}")
        print("-" * 62)
        for mode in OVERLAY_MODES:
            trials = [r for r in results if r.model_key == mk and r.overlay_mode == mode]
            if not trials:
                continue
            valid = [r for r in trials if r.final_dist < 900]
            n, nv = len(trials), len(valid)
            succ = sum(1 for r in valid if r.success)
            raw = succ / max(n, 1) * 100
            proto = succ / max(nv, 1) * 100 if nv else 0
            md = sum(r.final_dist for r in valid) / max(nv, 1) if nv else 0
            mi = sum(r.iterations for r in valid) / max(nv, 1) if nv else 0
            print(f"{mode:<20} {n:>6} {nv:>6} {succ:>6} {raw:>5.0f}% {proto:>6.0f}% {md:>7.0f}px {mi:>4.1f}")

    save_partial()
    print(f"\nSaved {len(results)} trials to {out_path}")

if __name__ == "__main__":
    main()
