"""Trial executors: run DVOC or Naive on a given task and model."""

import os, json, time, math, random, base64, re, logging, itertools
from io import BytesIO
from dataclasses import dataclass, asdict
from typing import Optional, Callable

from PIL import Image
import litellm
litellm.suppress_debug_info = True
litellm.set_verbose = False
os.environ["LITELLM_LOG"] = "ERROR"
logging.getLogger("LiteLLM").setLevel(logging.ERROR)

from litellm import completion

from dvoc_core import Point, Vector, DVOCBackend, Geometry, ActionResult
from dvoc_core import Planner, Verifier, Corrector, Renderer, Policy
from dvoc_core._loop import LoopEngine

from .config import (
    EPSILON, MIN_HIT_RADIUS, MAX_DVAL_ITERS, MAX_NAIVE_RETRIES,
    DVAL_SYSTEM, DVAL_SYSTEM_BY_MODE, DVAL_ABSOLUTE_SYSTEM,
    NAIVE_SYSTEM_FIRST, NAIVE_SYSTEM_RETRY,
    OFFSET_TOOLS, CLICK_TOOLS,
)
from ._saver import TrialSaver

random.seed(42)

# API key rotation
_API_KEYS = [
    k for k in [
        os.environ.get("GEMINI_API_KEY"),
        os.environ.get("GEMINI_API_KEY_2"),
        os.environ.get("GEMINI_API_KEY_3"),
    ] if k
]
_OR_KEY = os.environ.get("OPENROUTER_API_KEY")
_key_cycle = itertools.cycle(_API_KEYS) if _API_KEYS else None

# Per-request timeout and backoff
_REQUEST_TIMEOUT = 120  # 2 min per completion call
_TRIAL_DELAY = 2.5  # seconds between trials to avoid rate limits


class RateLimitError(Exception):
    """Transient rate limit — model can be retried later."""

class QuotaError(Exception):
    """Quota exhausted or privacy blocked — model permanently dead this session."""


def _classify_api_error(err_str: str) -> type[Exception] | None:
    """Classify an API error. Returns None if not recoverable at model level."""
    err_lower = err_str.lower()
    # Transient rate limit / server error (check BEFORE quota text, since
    # Gemini often includes "quota" in 429 messages)
    if any(code in err_str for code in ["429", "503", "500", "ServiceUnavailable", "ResourceExhausted"]):
        return RateLimitError
    # Permanent: quota exhausted
    if "quota" in err_lower or "billing" in err_lower:
        return QuotaError
    # Permanent: privacy guardrails (OpenRouter 404)
    if "guardrail" in err_lower or "privacy" in err_lower or "no endpoints available" in err_lower:
        return QuotaError
    return None


@dataclass
class IterationRecord:
    draft: dict
    error: dict
    confidence: float
    distance_to_target: float


@dataclass
class TrialResult:
    trial_id: str
    model_key: str
    task_id: str
    method: str
    success: bool
    final_dist: float
    iterations: int
    model_calls: int
    elapsed: float
    start_position: dict | None = None
    target_position: dict | None = None
    iteration_history: list | None = None
    error: Optional[str] = None
    overlay_mode: str = "full"
    predict_mode: str = "relative"
    alpha_schedule: str = "default"


def _pick_api_key():
    if _key_cycle:
        return next(_key_cycle)
    return None


def _key_for_model(model_name: str) -> str | None:
    if "openrouter" in model_name.lower():
        return _OR_KEY
    return _pick_api_key()


def complete_with_backoff(model, messages, tools, timeout=_REQUEST_TIMEOUT, model_key="unknown"):
    models = model if isinstance(model, list) else [model]
    model_idx = 0
    wait = 2.0
    attempt = 0
    retries_on_current = 0
    while retries_on_current < 3:  # max 3 retries per call before giving up
        current = models[model_idx]
        t0 = time.time()
        kwargs = dict(model=current, messages=messages, tools=tools, timeout=timeout)
        api_key = _key_for_model(current)
        if api_key:
            kwargs["api_key"] = api_key
        try:
            resp = completion(**kwargs)
            return resp, time.time() - t0
        except Exception as e:
            err_str = str(e)
            err_class = _classify_api_error(err_str)
            if err_class is QuotaError:
                print(f"    ⛔ {current}: quota/privacy blocked", flush=True)
                # Try next model in list before giving up
                if model_idx < len(models) - 1:
                    model_idx += 1
                    retries_on_current = 0
                    wait = 2.0
                    print(f"    ↪ switching to {models[model_idx]}", flush=True)
                    continue
                raise QuotaError(f"{current}: {err_str[:200]}") from e
            if err_class is not RateLimitError:
                raise
            # Rate-limited — try next provider if available
            if model_idx < len(models) - 1:
                model_idx += 1
                retries_on_current = 0
                wait = 2.0
                print(f"    ↪ rate-limited, switching to {models[model_idx]}", flush=True)
            else:
                retries_on_current += 1
                m = re.search(r"retry (in )?([\d.]+)s?", err_str, re.IGNORECASE)
                suggested = float(m.group(2)) if m else 0
                wait = max(suggested, min(wait * 2, 30.0), 2.0)
                print(f"    ⏳ rate-limited, retry {retries_on_current}/3 — waiting {wait:.0f}s", flush=True)
                time.sleep(wait)
    raise RateLimitError(f"All providers rate-limited for {model_key}")


class CaptureBackend(DVOCBackend):
    def __init__(self, capture_fn: Callable):
        self._capture_fn = capture_fn

    def capture(self) -> Image.Image:
        return self._capture_fn()

    def execute(self, action) -> ActionResult:
        return ActionResult(success=True)

    def get_screen_geometry(self) -> Geometry:
        img = self.capture()
        return Geometry(img.width, img.height)


class DVALExecutor:
    def __init__(self, model_name: str, model_key: str,
                 capture_fn: Callable, target: tuple,
                 task_prompt: str, task_id: str,
                 start_pos: tuple, saver: TrialSaver | None = None,
                 target_w: float = 0, target_h: float = 0,
                 overlay_mode: str = "full",
                 predict_mode: str = "relative",
                 alpha_schedule: str = "default"):
        self.model_name = model_name
        self.model_key = model_key
        self.capture_fn = capture_fn
        self.tx, self.ty = target
        self.task_prompt = task_prompt
        self.task_id = task_id
        self.start_pos = start_pos
        self.saver = saver
        self.target_w = target_w
        self.target_h = target_h
        self.overlay_mode = overlay_mode
        self.predict_mode = predict_mode
        self.alpha_schedule = alpha_schedule

    def _hit_success(self, dist: float) -> bool:
        radius = max(self.target_w / 2, self.target_h / 2, MIN_HIT_RADIUS)
        return dist < radius

    def run(self) -> TrialResult:
        sx, sy = self.start_pos
        start = Point(sx, sy)
        history_records = []
        model_calls = 0
        t0 = time.time()

        iteration_raw = []

        def model_verify(frame, draft, task, history=None):
            nonlocal model_calls
            model_calls += 1
            buf = BytesIO()
            frame.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()
            hist_str = ""
            if history:
                lines = ["Previous iterations:"]
                for i, (pt, err, conf) in enumerate(history):
                    corr = Point(pt.x + err.dx, pt.y + err.dy)
                    lines.append(
                        f"  iter {i}: at ({pt.x:.0f},{pt.y:.0f}) "
                        f"said dx={err.dx:.0f} dy={err.dy:.0f} conf={conf:.2f} "
                        f"-> ({corr.x:.0f},{corr.y:.0f})"
                    )
                hist_str = "\n".join(lines)

            if self.predict_mode == "absolute":
                from .config import DVAL_ABSOLUTE_SYSTEM
                mode_prompt = DVAL_ABSOLUTE_SYSTEM
                tools = CLICK_TOOLS
                suffix = "Call click_at()."
            else:
                mode_prompt = DVAL_SYSTEM_BY_MODE.get(self.overlay_mode, DVAL_SYSTEM)
                tools = OFFSET_TOOLS
                suffix = "Call report_offset()."
            user_text = f"{mode_prompt}\n\nTask: {self.task_prompt}\n{hist_str}\n{suffix}"
            messages = [{"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}]

            resp, _ = complete_with_backoff(self.model_name, messages, tools, model_key=self.model_key)
            msg = resp.choices[0].message

            dx, dy, conf = 0.0, 0.0, 0.0
            if msg.tool_calls:
                args = json.loads(msg.tool_calls[0].function.arguments)
                if self.predict_mode == "absolute":
                    px = float(args.get("x", 0))
                    py = float(args.get("y", 0))
                    dx = px - float(draft.x)
                    dy = py - float(draft.y)
                    conf = min(max(float(args.get("confidence", 0)), 0.0), 1.0)
                else:
                    dx = float(args.get("dx", 0))
                    dy = float(args.get("dy", 0))
                    conf = min(max(float(args.get("confidence", 0)), 0.0), 1.0)

            iteration_raw.append({
                "iteration": model_calls - 1,
                "draft": {"x": float(draft.x), "y": float(draft.y)},
                "model_input": user_text,
                "model_output": {
                    "raw_message": msg.model_dump() if hasattr(msg, "model_dump") else str(msg),
                    "dx": dx,
                    "dy": dy,
                    "confidence": conf,
                },
            })

            return Vector(dx=dx, dy=dy), conf

        verifier = Verifier(mode="model", model_client=_wrap_verify(model_verify))
        backend = CaptureBackend(self.capture_fn)

        engine = LoopEngine(
            backend=backend,
            planner=Planner(mode="manual", manual_target=start),
            verifier=verifier,
            corrector=Corrector(epsilon=EPSILON, threshold=0.5,
                                 alpha_schedule=self.alpha_schedule),
            renderer=Renderer(overlay_mode=self.overlay_mode),
            policy=Policy(epsilon=EPSILON, threshold=0.5, convergence_window=2),
            max_iterations=MAX_DVAL_ITERS,
        )

        try:
            result = engine.run(self.task_prompt)
            fd = math.hypot(self.tx - result.final_point.x, self.ty - result.final_point.y)
            for snap in result.history:
                d = math.hypot(self.tx - snap.draft_point.x, self.ty - snap.draft_point.y)
                history_records.append(IterationRecord(
                    draft={"x": round(snap.draft_point.x, 1), "y": round(snap.draft_point.y, 1)},
                    error={"dx": round(snap.error_vector.dx, 1), "dy": round(snap.error_vector.dy, 1)},
                    confidence=snap.confidence,
                    distance_to_target=round(d, 1),
                ))

            trial_result = TrialResult(
                trial_id=f"{self.model_key}-{self.task_id}-{self.overlay_mode}-{self.predict_mode}-{self.alpha_schedule}",
                model_key=self.model_key, task_id=self.task_id,
                method=f"dvoc_{self.overlay_mode}_{self.predict_mode}_{self.alpha_schedule}",
                success=self._hit_success(fd), final_dist=round(fd, 1),
                iterations=result.iterations, model_calls=model_calls,
                overlay_mode=self.overlay_mode,
                predict_mode=self.predict_mode,
                alpha_schedule=self.alpha_schedule,
                elapsed=round(time.time() - t0, 1),
                start_position={"x": round(sx, 1), "y": round(sy, 1)},
                target_position={"x": round(self.tx, 1), "y": round(self.ty, 1)},
                iteration_history=[asdict(r) for r in history_records],
            )

            self._save_artifacts(result, iteration_raw, trial_result)
            return trial_result

        except (RateLimitError, QuotaError):
            raise
        except Exception as e:
            trial_result = TrialResult(
                trial_id=f"{self.model_key}-{self.task_id}-{self.overlay_mode}-{self.predict_mode}-{self.alpha_schedule}",
                model_key=self.model_key, task_id=self.task_id,
                method=f"dvoc_{self.overlay_mode}_{self.predict_mode}_{self.alpha_schedule}",
                success=False, final_dist=999, iterations=0, model_calls=model_calls,
                overlay_mode=self.overlay_mode,
                predict_mode=self.predict_mode,
                alpha_schedule=self.alpha_schedule,
                elapsed=round(time.time() - t0, 1),
                start_position={"x": round(sx, 1), "y": round(sy, 1)},
                target_position={"x": round(self.tx, 1), "y": round(self.ty, 1)},
                error=str(e)[:300],
            )
            self._save_error(trial_result)
            return trial_result

    def _save_artifacts(self, result, iteration_raw, trial_result):
        if not self.saver:
            return
        for snap in result.history:
            model_data = None
            it = snap.iteration
            if it < len(iteration_raw):
                model_data = iteration_raw[it]
            self.saver.save_iteration(it, snap.annotated_frame, model_data)
        self.saver.save_trial_meta(trial_result)

    def _save_error(self, trial_result):
        if self.saver:
            self.saver.save_trial_meta(trial_result)


def _wrap_verify(fn):
    class Wrapper:
        def verify(self, frame, draft, task, history=None):
            return fn(frame, draft, task, history)
    return Wrapper()


class NaiveExecutor:
    def __init__(self, model_name: str, model_key: str,
                 capture_fn: Callable, target: tuple,
                 task_prompt: str, task_id: str,
                 saver: TrialSaver | None = None,
                 target_w: float = 0, target_h: float = 0):
        self.model_name = model_name
        self.model_key = model_key
        self.capture_fn = capture_fn
        self.tx, self.ty = target
        self.task_prompt = task_prompt
        self.task_id = task_id
        self.saver = saver
        self.target_w = target_w
        self.target_h = target_h

    def _hit_success(self, dist: float) -> bool:
        radius = max(self.target_w / 2, self.target_h / 2, MIN_HIT_RADIUS)
        return dist < radius

    def run(self) -> TrialResult:
        t0 = time.time()
        calls = 0
        last_x, last_y = 0, 0
        iteration_raw = []

        for i in range(MAX_NAIVE_RETRIES):
            calls += 1
            frame = self.capture_fn()
            buf = BytesIO()
            frame.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode()

            if i == 0:
                sys_prompt = NAIVE_SYSTEM_FIRST
            else:
                sys_prompt = NAIVE_SYSTEM_RETRY.format(x=last_x, y=last_y, task=self.task_prompt)

            user_text = f"{sys_prompt}\n\nCall click_at()."
            messages = [{"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]}]

            try:
                resp, _ = complete_with_backoff(self.model_name, messages, CLICK_TOOLS, model_key=self.model_key)
            except (RateLimitError, QuotaError):
                raise
            except Exception as e:
                trial_result = TrialResult(
                    trial_id=f"{self.model_key}-{self.task_id}-naive",
                    model_key=self.model_key, task_id=self.task_id, method="naive",
                    success=False, final_dist=999, iterations=i + 1, model_calls=calls,
                    elapsed=round(time.time() - t0, 1), error=str(e)[:300],
                )
                self._save_error(trial_result, frame, i, iteration_raw, user_text)
                return trial_result

            msg = resp.choices[0].message
            last_x, last_y = 0, 0
            raw_response = None
            if msg.tool_calls:
                args = json.loads(msg.tool_calls[0].function.arguments)
                last_x, last_y = float(args.get("x", 0)), float(args.get("y", 0))
                raw_response = {"x": last_x, "y": last_y, "confidence": float(args.get("confidence", 0))}

            iteration_raw.append({
                "iteration": i,
                "model_input": user_text,
                "model_output": {
                    "raw_message": msg.model_dump() if hasattr(msg, "model_dump") else str(msg),
                    "x": last_x,
                    "y": last_y,
                },
            })

            if self.saver:
                frame_rgb = frame.convert("RGB")
                self.saver.save_iteration(i, frame_rgb, iteration_raw[-1])

            d = math.hypot(self.tx - last_x, self.ty - last_y)
            if self._hit_success(d):
                trial_result = TrialResult(
                    trial_id=f"{self.model_key}-{self.task_id}-naive",
                    model_key=self.model_key, task_id=self.task_id, method="naive",
                    success=True, final_dist=round(d, 1), iterations=i + 1, model_calls=calls,
                    elapsed=round(time.time() - t0, 1),
                    target_position={"x": round(self.tx, 1), "y": round(self.ty, 1)},
                    iteration_history=[{"iteration": i, "response": raw_response, "distance": round(d, 1)}],
                )
                if self.saver:
                    self.saver.save_trial_meta(trial_result)
                return trial_result

        trial_result = TrialResult(
            trial_id=f"{self.model_key}-{self.task_id}-naive",
            model_key=self.model_key, task_id=self.task_id, method="naive",
            success=False, final_dist=round(d, 1), iterations=MAX_NAIVE_RETRIES,
            model_calls=calls, elapsed=round(time.time() - t0, 1),
            target_position={"x": round(self.tx, 1), "y": round(self.ty, 1)},
            iteration_history=[{"response": r} for r in iteration_raw],
        )
        if self.saver:
            self.saver.save_trial_meta(trial_result)
        return trial_result

    def _save_error(self, trial_result, frame, iteration, iteration_raw, user_text):
        if self.saver:
            self.saver.save_iteration(iteration, frame, {
                "iteration": iteration,
                "model_input": user_text,
                "model_output": {"error": trial_result.error},
            })
            self.saver.save_trial_meta(trial_result)
