"""Results aggregation, summary tables, and JSON export."""

import json, os
from dataclasses import dataclass, asdict
from typing import Optional

from .config import OUT_DIR


def build_report(all_results: list, elapsed: float, model_keys: list[str], models_cfg: dict):
    agg = ResultAggregator(all_results)
    agg.print_summary(elapsed)
    agg.save_json(elapsed)
    return agg


class ResultAggregator:
    def __init__(self, all_results: list):
        self.results = all_results

    @staticmethod
    def _mean(vals):
        return sum(vals) / len(vals) if vals else 0

    def _group(self, model_key=None, task_id=None, method=None):
        return [r for r in self.results
                if (model_key is None or r.model_key == model_key)
                and (task_id is None or r.task_id == task_id)
                and (method is None or r.method == method)]

    def print_summary(self, elapsed):
        print(f"\n{'='*80}")
        print(f"BENCHMARK COMPLETE ({elapsed:.0f}s)")
        print(f"{'='*80}")

        model_keys = sorted(set(r.model_key for r in self.results))
        task_ids = sorted(set(r.task_id for r in self.results))

        # Per-model summary
        for mk in model_keys:
            dvals = self._group(model_key=mk, method="dvoc")
            naives = self._group(model_key=mk, method="naive")

            print(f"\n── {mk} ──")
            if dvals:
                ds = sum(1 for r in dvals if r.success)
                dm = self._mean([r.final_dist for r in dvals])
                di = self._mean([r.iterations for r in dvals])
                dc = sum(r.model_calls for r in dvals)
                print(f"  DVOC:   {ds:>2}/{len(dvals):<2} = {ds/len(dvals)*100:>3.0f}%  "
                      f"mean dist={dm:>4.0f}px  mean iters={di:.1f}  total calls={dc}")
            if naives:
                ns = sum(1 for r in naives if r.success)
                nm = self._mean([r.final_dist for r in naives])
                nc = sum(r.model_calls for r in naives)
                print(f"  Naive:  {ns:>2}/{len(naives):<2} = {ns/len(naives)*100:>3.0f}%  "
                      f"mean dist={nm:>4.0f}px  total calls={nc}")

        # Per-task × per-model table
        print(f"\n{'─'*80}")
        print(f"{'Task':<20} {'Model':<20} {'DVOC %':<10} {'Naive %':<10} {'DVOC dist':<12} {'Naive dist':<12}")
        print(f"{'─'*80}")
        for tid in task_ids:
            first = True
            for mk in model_keys:
                dvals = self._group(model_key=mk, task_id=tid, method="dvoc")
                naives = self._group(model_key=mk, task_id=tid, method="naive")
                ds = sum(1 for r in dvals if r.success) / len(dvals) * 100 if dvals else 0
                ns = sum(1 for r in naives if r.success) / len(naives) * 100 if naives else 0
                dm = self._mean([r.final_dist for r in dvals]) if dvals else 0
                nm = self._mean([r.final_dist for r in naives]) if naives else 0
                label = tid if first else ""
                first = False
                print(f"{label:<20} {mk:<20} {ds:>6.0f}%    {ns:>6.0f}%    {dm:>6.0f}px     {nm:>6.0f}px")

        # Per-task detail
        print(f"\n{'─'*80}")
        print("PER-TASK DETAIL")
        print(f"{'─'*80}")
        for tid in task_ids:
            dvals = self._group(task_id=tid, method="dvoc")
            naives = self._group(task_id=tid, method="naive")
            ds = sum(1 for r in dvals if r.success)
            ns = sum(1 for r in naives if r.success)
            dm = self._mean([r.final_dist for r in dvals])
            nm = self._mean([r.final_dist for r in naives])
            dv_str = f"{ds:>2}/{len(dvals):<2} = {ds/len(dvals)*100:>3.0f}%" if dvals else "no data"
            nv_str = f"{ns:>2}/{len(naives):<2} = {ns/len(naives)*100:>3.0f}%" if naives else "no data"
            print(f"  {tid:<16} DVOC: {dv_str}  dist={dm:.0f}px  |  Naive: {nv_str}  dist={nm:.0f}px")

    def save_json(self, elapsed):
        path = os.path.join(OUT_DIR, "benchmark_results.json")
        with open(path, "w") as f:
            json.dump({
                "elapsed_seconds": round(elapsed),
                "config": {
                    "epsilon": 30.0,
                    "max_dval_iters": 15,
                    "max_naive_retries": 5,
                    "repeats_per_position": 3,
                },
                "results": [asdict(r) for r in self.results],
            }, f, indent=2)
        print(f"\nResults saved: {path}")
