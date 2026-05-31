"""DVOC web model-based test.

Creates a realistic HTML page with multiple UI elements, runs DVOC through
a real vision model (Gemini/GeMMA), and tracks every refinement step.

This validates DVOC's ability to ground UI elements on real web pages
(rather than synthetic screenshots).

Usage:
    export GEMINI_API_KEY="your-key-here"
    python examples/test_web_model.py
"""

import os, sys

from dvoc_core import (
    Point, Vector, Geometry, Action, ActionResult,
    DVOCBackend, Planner, Verifier, Corrector, Renderer, Policy,
    LoopEngine, LoopResult,
)
from dvoc_core._model import ModelClient
from dvoc_web import WebBackend


WRAPPER_HTML = """
<html>
<head><style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: #1a1b26; font-family: system-ui; padding: 40px; color: #fff; }
  .card { background: #24253a; border-radius: 12px; padding: 24px; margin-bottom: 20px; }
  h1 { font-size: 24px; margin-bottom: 20px; }
  .btn { display:inline-block; padding:12px 24px; border-radius:8px;
         border:none; font-size:16px; cursor:pointer; margin-right:12px; margin-bottom:12px; }
  .btn-primary { background:#7c5cfc; color:#fff; }
  .btn-success { background:#34d399; color:#1a1b26; }
  .btn-danger  { background:#f87171; color:#1a1b26; }
  .input-group { margin-bottom:16px; }
  .input-group label { display:block; margin-bottom:6px; font-size:14px; color:#a0a2b8; }
  .input-group input { width:100%; padding:10px 14px; border-radius:8px;
                       border:1px solid #3a3b52; background:#1e1f32;
                       color:#fff; font-size:15px; }
  select { width:100%; padding:10px 14px; border-radius:8px;
           border:1px solid #3a3b52; background:#1e1f32; color:#fff; font-size:15px; }
  .checkbox-group { margin:12px 0; }
  .checkbox-group label { margin-left:8px; font-size:15px; color:#c0c2d8; }
  a { color:#7c5cfc; text-decoration:none; font-size:15px; }
  a:hover { text-decoration:underline; }
</style></head>
<body>
  <h1>Dashboard</h1>
  <div class="card">
    <div class="input-group">
      <label for="email">Email</label>
      <input id="email" type="email" placeholder="your@email.com">
    </div>
    <div class="input-group">
      <label for="password">Password</label>
      <input id="password" type="password" placeholder="••••••••">
    </div>
    <div class="checkbox-group">
      <input id="remember" type="checkbox"> <label for="remember">Remember me</label>
    </div>
    <button class="btn btn-primary" id="login-btn">Sign In</button>
    <a href="#" id="forgot-link">Forgot password?</a>
  </div>
  <div class="card">
    <button class="btn btn-success" id="save-btn">Save Changes</button>
    <button class="btn btn-danger" id="delete-btn">Delete Account</button>
    <select id="theme-select">
      <option>Light</option>
      <option selected>Dark</option>
      <option>System</option>
    </select>
  </div>
</body></html>
"""


def print_result(result: LoopResult, target: Point | None = None):
    fx = result.final_point.x if result.final_point else 0
    fy = result.final_point.y if result.final_point else 0
    print(f"  Iterations: {result.iterations}")
    print(f"  Decision: {result.decision}")
    print(f"  Final draft: ({fx:.0f}, {fy:.0f})")
    if target:
        d = ((target.x - fx) ** 2 + (target.y - fy) ** 2) ** 0.5
        print(f"  Target: ({target.x:.0f}, {target.y:.0f})")
        print(f"  Distance: {d:.0f}px")
        print(f"  Success: {d < 30}")
    print(f"  Result: {'PASS' if result.success else 'FAIL'}")


def run_test(api_key: str, model_name: str, page_url: str,
             target_description: str, task: str, manual_target: Point | None = None,
             epsilon: float = 30.0, max_iterations: int = 15) -> bool:
    print(f"\n{'='*70}")
    print(f"Task: {task}")
    print(f"Model: {model_name}")
    print(f"{'='*70}")

    b = WebBackend(headless=True)
    b.start()
    b.goto(page_url, wait_until="load")

    model = ModelClient(api_key=api_key, model_name=model_name)
    planner = Planner(mode="manual" if manual_target else "model",
                      manual_target=manual_target,
                      model_client=model if not manual_target else None)
    verifier = Verifier(mode="model", model_client=model)
    corrector = Corrector(epsilon=epsilon, threshold=0.5)
    renderer = Renderer()
    policy = Policy(epsilon=epsilon, threshold=0.5, convergence_window=2,
                    max_iterations=max_iterations)

    engine = LoopEngine(
        backend=b, planner=planner, verifier=verifier,
        corrector=corrector, renderer=renderer, policy=policy,
    )

    try:
        result = engine.run(task)
        print_result(result, target=manual_target)
        passed = result.success
    except Exception as e:
        print(f"  ERROR: {e}")
        passed = False
    finally:
        b.stop()

    return passed


def main():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: Set GEMINI_API_KEY environment variable")
        sys.exit(1)

    model_name = os.environ.get("DVAL_MODEL", "gemini/gemini-3.1-flash-lite")

    # Serve the HTML via data URI (no server needed)
    page_url = f"data:text/html,{WRAPPER_HTML.replace(chr(10),'').replace('  ','')}"

    # Each task: what to click, task description, approximate target center
    tasks = [
        {
            "name": "Sign In button",
            "task": "Click the Sign In button",
            "target": None,  # use model-based planning
        },
        {
            "name": "Delete Account button",
            "task": "Click the Delete Account button",
            "target": None,
        },
    ]

    passed = 0
    for t in tasks:
        try:
            if run_test(api_key, model_name, page_url, t["name"], t["task"], t.get("target")):
                passed += 1
        except Exception as e:
            print(f"\nERROR on '{t['name']}': {e}")

    print(f"\n{'='*70}")
    print(f"Results: {passed}/{len(tasks)} tasks passed")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
