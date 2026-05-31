#!/usr/bin/env python3
"""DVOC Benchmark Runner — smart scheduler.

Builds a flat task queue, tracks per-model quota/rate-limit state,
and cycles through available models until all tasks complete.

Usage:
    python -m examples.benchmark.run [--synthetic] [--web] [--models KEY ...] [--quick] [--resume]
"""

import os, sys, time, argparse, random, math
from io import BytesIO
from PIL import Image
from dataclasses import asdict

_TRIAL_DELAY = 2.5

from .config import MODELS, START_POSITIONS, REPEATS_PER_POSITION, OUT_DIR
from .engine import DVALExecutor, NaiveExecutor, RateLimitError, QuotaError, TrialResult
from ._saver import TrialSaver
from .reporter import build_report
from .tasks import synthetic as synth_tasks
from .tasks import web as web_tasks


def _trial_done(mk, tid, method, pos_idx, rep):
    path = os.path.join(OUT_DIR, "artifacts", mk, tid, method, f"pos{pos_idx}_rep{rep}", "trial.json")
    return os.path.exists(path)


def main():
    parser = argparse.ArgumentParser(description="DVOC Benchmark Runner")
    parser.add_argument("--synthetic", action="store_true", help="Run synthetic tasks")
    parser.add_argument("--web", action="store_true", help="Run web tasks")
    parser.add_argument("--models", nargs="+", help="Model keys to run (default: all non-skipped)")
    parser.add_argument("--quick", action="store_true", help="1 repeat per position instead of 3")
    parser.add_argument("--resume", action="store_true", help="Skip already-completed trials")
    args = parser.parse_args()

    if not args.synthetic and not args.web:
        args.synthetic = True
        args.web = True

    repeats = 1 if args.quick else REPEATS_PER_POSITION

    model_keys = args.models or [k for k, v in MODELS.items() if not v.get("skip")]
    active_models = {k: MODELS[k] for k in model_keys if k in MODELS and not MODELS[k].get("skip")}

    gemini_key = os.environ.get("GEMINI_API_KEY")
    or_key = os.environ.get("OPENROUTER_API_KEY")

    available = {}
    for k, v in active_models.items():
        prov = v["provider"]
        if prov == "gemini" and not gemini_key:
            print(f"  Skipping {k}: no GEMINI_API_KEY")
            continue
        if prov == "openrouter" and not or_key:
            print(f"  Skipping {k}: no OPENROUTER_API_KEY")
            continue
        if prov == "hybrid" and (not gemini_key or not or_key):
            print(f"  Skipping {k}: hybrid needs both GEMINI_API_KEY and OPENROUTER_API_KEY")
            continue
        available[k] = v

    if not available:
        print("ERROR: No models available. Set GEMINI_API_KEY or OPENROUTER_API_KEY")
        sys.exit(1)

    # ── Build task descriptors ──
    # Each task_desc: (task_id, prompt, target_xy, target_w, target_h, capture_fn_or_html, is_web)
    task_descs = []

    if args.synthetic:
        for task_fn in synth_tasks.ALL:
            task = task_fn()
            task_descs.append((task.id, task.prompt, task.target,
                               task.target_w, task.target_h, task.img.copy, False))

    web_task_descs = []
    if args.web:
        try:
            from dvoc_web import WebBackend
        except ImportError:
            print("  Skipping web tasks: dvoc-web not installed")
            args.web = False

    if args.web:
        for wt in web_tasks.TASKS:
            try:
                b = WebBackend(headless=True, viewport={"width": 1280, "height": 720})
                b.start()
                b.page.set_content(wt.html)
                box = b.page.evaluate(f"""(() => {{
                    const el = document.querySelector('{wt.target_selector}');
                    const r = el.getBoundingClientRect();
                    return {{x: r.left + r.width/2, y: r.top + r.height/2, w: r.width, h: r.height}};
                }})()""")
                b.stop()
                target = (box["x"], box["y"])
                target_w, target_h = box["w"], box["h"]
            except Exception as e:
                print(f"  Skipping {wt.id}: failed to get target — {e}")
                continue
            web_task_descs.append((wt.id, wt.prompt, target, target_w, target_h, wt.html))

    print(f"\n{'='*80}")
    print(f"DVOC BENCHMARK — SCHEDULER")
    print(f"{'='*80}")
    print(f"Models: {', '.join(available.keys())}")
    print(f"Tasks: {len(task_descs)} synthetic + {len(web_task_descs)} web")
    print(f"Starting positions: {len(START_POSITIONS)} fixed")
    print(f"Repeats per position: {repeats}")
    if args.resume:
        print(f"Resume mode: skipping completed trials")
    print()

    # ── Build flat pending queue ──
    # Each item: (model_key, model_cfg, task_id, prompt, target, tw, th, method, pos_idx, rep, start_pos)
    pending = []
    for mk, cfg in available.items():
        for tid, prompt, target, tw, th, _, _ in task_descs:
            for method in ("dvoc", "naive"):
                for pos_idx, (sx, sy) in enumerate(START_POSITIONS):
                    for rep in range(repeats):
                        if args.resume and _trial_done(mk, tid, method, pos_idx + 1, rep + 1):
                            continue
                        pending.append((mk, cfg, tid, prompt, target, tw, th, method, pos_idx, rep, (sx, sy)))
        for tid, prompt, target, tw, th, _ in web_task_descs:
            for method in ("dvoc", "naive"):
                for pos_idx, (sx, sy) in enumerate(START_POSITIONS):
                    for rep in range(repeats):
                        if args.resume and _trial_done(mk, tid, method, pos_idx + 1, rep + 1):
                            continue
                        pending.append((mk, cfg, tid, prompt, target, tw, th, method, pos_idx, rep, (sx, sy)))

    random.shuffle(pending)
    print(f"Pending trials: {len(pending)}")
    if not pending:
        print("All trials already completed!")
        sys.exit(0)
    print()

    # ── Scheduler state ──
    model_state: dict[str, str] = {mk: "active" for mk in available}
    model_cooldown_until: dict[str, float] = {}
    all_results: list = []
    t0 = time.time()

    def reactivate_cooldowns():
        now = time.time()
        for mk in list(model_state):
            if model_state.get(mk) == "cooldown" and now >= model_cooldown_until.get(mk, 0):
                model_state[mk] = "active"
                print(f"  {mk}: cooldown expired, reactivated", flush=True)

    def make_synthetic_capture(fn):
        return lambda: fn()

    def make_web_capture(html):
        wb = WebBackend(headless=True, viewport={"width": 1280, "height": 720})
        wb.start()
        wb.page.set_content(html)
        return lambda: Image.open(BytesIO(wb.page.screenshot(type="png"))), wb.stop

    def build_failed_result(mk, task_id, prompt, target, start_pos, method, error_msg, elapsed):
        return TrialResult(
            trial_id=f"{mk}-{task_id}-{method}",
            model_key=mk, task_id=task_id, method=method,
            success=False, final_dist=999, iterations=0, model_calls=0,
            elapsed=round(elapsed, 1),
            start_position={"x": round(start_pos[0], 1), "y": round(start_pos[1], 1)},
            target_position={"x": round(target[0], 1), "y": round(target[1], 1)},
            error=error_msg[:300],
        )

    while pending:
        reactivate_cooldowns()

        active_count = sum(1 for s in model_state.values() if s == "active")
        if active_count == 0:
            cooldowns = [v for k, v in model_cooldown_until.items()
                         if model_state.get(k) == "cooldown"]
            if cooldowns:
                wait = max(0, min(cooldowns) - time.time())
                if wait > 0:
                    print(f"\n  All models cooling down — waiting {min(wait, 60):.0f}s", flush=True)
                    time.sleep(min(wait, 60))
                    continue
            else:
                print("\n  All models permanently blocked. Stopping.", flush=True)
                break

        # Pick a pending task for an active model
        random.shuffle(pending)
        picked_idx = next((i for i, p in enumerate(pending) if model_state.get(p[0]) == "active"), None)
        if picked_idx is None:
            time.sleep(15)
            continue

        mk, cfg, tid, prompt, target, tw, th, method, pos_idx, rep, start_pos = pending.pop(picked_idx)

        # Build capture function
        is_web = any(t[0] == tid for t in web_task_descs)
        web_cleanup = None

        if is_web:
            html = next(t[5] for t in web_task_descs if t[0] == tid)
            capture_fn, web_cleanup = make_web_capture(html)
        else:
            img_copy_fn = next(t[5] for t in task_descs if t[0] == tid)
            capture_fn = make_synthetic_capture(img_copy_fn)

        print(f"\n{method.upper()} {mk} — {tid} (pos{pos_idx + 1}.{rep + 1})", flush=True)

        model_name = cfg["names"] if "names" in cfg else cfg["name"]
        saver = TrialSaver(OUT_DIR, mk, tid, method, pos_idx + 1, rep + 1)

        if method == "dvoc":
            executor = DVALExecutor(
                model_name=model_name, model_key=mk,
                capture_fn=capture_fn, target=target,
                task_prompt=prompt, task_id=tid,
                start_pos=start_pos, saver=saver,
                target_w=tw, target_h=th,
            )
        else:
            executor = NaiveExecutor(
                model_name=model_name, model_key=mk,
                capture_fn=capture_fn, target=target,
                task_prompt=prompt, task_id=tid,
                saver=saver, target_w=tw, target_h=th,
            )

        try:
            r = executor.run()
            all_results.append(r)
            model_state[mk] = "active"
            status = "PASS" if r.success else "FAIL"
            print(f"  → {status} dist={r.final_dist:.0f}px iters={r.iterations} [{r.elapsed:.0f}s]", flush=True)
        except QuotaError as e:
            model_state[mk] = "dead"
            print(f"  ⛔ {mk}: quota/privacy blocked — permanently skipping", flush=True)
            pending = [p for p in pending if p[0] != mk]
            err_r = build_failed_result(mk, tid, prompt, target, start_pos, method,
                                        str(e)[:300], time.time() - t0)
            all_results.append(err_r)
        except RateLimitError:
            model_state[mk] = "cooldown"
            model_cooldown_until[mk] = time.time() + 30
            print(f"  ⏸ {mk}: rate-limited, cooling down 30s, re-queued", flush=True)
            pending.append((mk, cfg, tid, prompt, target, tw, th, method, pos_idx, rep, start_pos))
        except Exception as e:
            err_r = build_failed_result(mk, tid, prompt, target, start_pos, method,
                                        str(e)[:300], time.time() - t0)
            all_results.append(err_r)
            print(f"  ✗ FAIL — {str(e)[:120]}", flush=True)
        finally:
            if web_cleanup:
                web_cleanup()

        time.sleep(_TRIAL_DELAY)

    print(f"\n{'='*80}")
    print(f"SCHEDULER COMPLETE")
    print(f"{'='*80}")
    active_final = [mk for mk in available if model_state.get(mk) != "dead"]
    build_report(all_results, time.time() - t0, active_final, MODELS)


if __name__ == "__main__":
    main()
