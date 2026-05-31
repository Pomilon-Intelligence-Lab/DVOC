# DVOC — Damped Visual Offset Correction

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Paper](https://img.shields.io/badge/Paper-research.pomilon.xyz-blue)](https://research.pomilon.xyz/papers/dvoc-damped-visual-offset-correction-enables-weak-model-ui-grounding-via-kinematic-control)

> **Making weak vision models viable for pixel-precise UI grounding through iterative visual feedback.**

DVOC is a training-free recursive refinement protocol for pixel-accurate UI grounding with weak VLMs. Instead of one-shot coordinate prediction, it runs a closed kinematic loop: render a visual overlay (crosshair + uncertainty circle) at the model's previous estimate, ask for a relative offset, apply the correction with exponential damping, and repeat.

**Key result:** 53–67% raw success (63–100% protocol) vs. 0–14% for naive one-shot prediction across 4 VLMs and 11 UI tasks. A 26B model under DVOC achieves 100% protocol convergence.

---

## Quick Start

```bash
git clone https://github.com/Pomilon-Intelligence-Lab/DVOC
cd DVOC
pip install -e dvoc-core/
pip install -e dvoc-py/
export GEMINI_API_KEY="your-key-here"
```

```python
from dvoc import DVOC

# Desktop backend (OS-level clicks)
agent = DVOC(
    backend="os",
    model="gemini/gemini-3.1-flash-lite",
    epsilon=30.0,
    manual_target=(960, 540),
)

result = agent.run("Click the center of the screen")
print(result["success"])      # True
print(result["final_point"])  # point model converged to
print(result["iterations"])   # iterations needed
```

### Web Backend

```python
from dvoc import DVOC
from dvoc_web import WebBackend

backend = WebBackend(headless=True)
backend.start()
backend.goto("https://example.com")

agent = DVOC(
    backend=backend,  # pass pre-configured backend directly
    model="gemini/gemini-3.1-flash-lite",
    epsilon=30.0,
)
result = agent.run("Click the 'More information' link")
backend.stop()
```

---

## Architecture

```
Planner → Backend (capture) → Renderer (overlay) → Verifier (VLM) → Corrector → Policy → ACT
```

Six modules, one responsibility each:

| Module | Responsibility |
|--------|--------------|
| `State` | Immutable per-iteration snapshots with full replay |
| `Planner` | Initial coordinate guess (manual or VLM) |
| `Renderer` | Draw crosshair + circle + labels on screenshot |
| `Verifier` | VLM estimates offset from crosshair to target |
| `Corrector` | Damped correction with exponential alpha decay |
| `Policy` | Convergence gating: REFINE / ACT / ABORT |

The Verifier uses a ReAct-style prompt — the model reasons step-by-step, sees its own previous iterations, then calls `report_offset(dx, dy, confidence)` via tool calling.

---

## Repository Structure

```
dvoc-protocol/
├── dvoc-core/src/dvoc_core/     # Loop engine (10 modules)
│   ├── _types.py                # Point, Vector, Geometry, Action
│   ├── _state.py                # Immutable state model
│   ├── _backend.py              # Backend ABC
│   ├── _planner.py              # Manual or model-based planner
│   ├── _verifier.py             # Simulated or model-based verifier
│   ├── _corrector.py            # Damped correction
│   ├── _renderer.py             # Visual overlay (crosshair + circle)
│   ├── _policy.py               # Convergence policy
│   ├── _loop.py                 # LoopEngine orchestrator
│   └── _model.py                # LiteLLM-based VLM client
├── dvoc-os/                     # Desktop backend (auto-detects X11 / Wayland / Windows)
├── dvoc-web/                    # Web backend (Playwright)
├── dvoc-py/                     # Public SDK
├── examples/
│   ├── benchmark/               # Benchmark engine (CLI, config, tasks, reporter)
│   ├── run_ablation.py          # Ablation experiments
│   ├── run_alpha_ablation.py    # Alpha damping ablation
│   ├── run_predict_ablation.py  # Predict method ablation
│   ├── test_with_model.py       # Synthetic model test harness
│   └── test_web_model.py        # Real web page model test
├── artifacts/
│   ├── charts/                  # Benchmark result charts
│   └── results/                 # Aggregated trial results (JSON)
├── PAPER.md                     # Technical whitepaper
├── Makefile                     # Test runner
└── docs/                        # Design specs and plans
```

---

## Tests

```bash
make test-all
# 80 tests across all packages (61 core + 3 os + 3 py + 13 web)
```

Or test individual packages:

```bash
make test-core    # 61 core engine tests
make test-web     # 13 web backend tests
```

---

## Research

See [PAPER.md](PAPER.md) for the full technical whitepaper, including benchmark methodology, results, and analysis.

Paper: [research.pomilon.xyz/papers/dvoc](https://research.pomilon.xyz/papers/dvoc-damped-visual-offset-correction-enables-weak-model-ui-grounding-via-kinematic-control)

---

## License

MIT
