"""Per-trial iteration-saving utility.

Saves annotated frames (PNG) and model interaction records (JSON)
for each iteration of a DVOC or Naive trial.

Directory layout:
  output/artifacts/<model_key>/<task_id>/<method>/pos<N>_rep<M>/
    trial.json            # full trial metadata
    iter_000.png          # annotated frame (rendered crosshair + circle)
    iter_000.json         # model request/response data for this iteration
    iter_001.png
    iter_001.json
    ...
"""

import os, json, time
from io import BytesIO
from PIL import Image
from dataclasses import asdict


class TrialSaver:
    def __init__(self, base_dir: str, model_key: str, task_id: str,
                 method: str, pos_idx: int, repeat: int):
        self.dir = os.path.join(
            base_dir, "artifacts", model_key, task_id, method,
            f"pos{pos_idx}_rep{repeat}",
        )
        os.makedirs(self.dir, exist_ok=True)

    def save_trial_meta(self, trial_result):
        with open(os.path.join(self.dir, "trial.json"), "w") as f:
            json.dump(asdict(trial_result), f, indent=2, default=str)

    def save_iteration(self, iteration: int, frame: Image.Image, model_data: dict | None = None):
        frame.save(os.path.join(self.dir, f"iter_{iteration:03d}.png"))
        if model_data:
            with open(os.path.join(self.dir, f"iter_{iteration:03d}.json"), "w") as f:
                json.dump(model_data, f, indent=2, default=str)
