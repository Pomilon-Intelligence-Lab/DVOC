# DVOC Protocol — System Design Specification

## Draft–Verify–Action Loop (DVOC)

**Date:** 2026-05-15
**Status:** Approved design, pre-implementation

---

## 1. Overview

DVOC is a **multimodal UI grounding and execution framework** that enables AI agents to interact with graphical interfaces through a **closed-loop visual correction system**. Actions are not executed until a recursive spatial refinement loop converges on precise coordinates.

### 1.1 Core Innovation

Instead of predict-and-execute, DVOC runs:

```
Draft → Verify → Align → Action (repeat until convergence)
```

Each iteration produces visual feedback (crosshair + uncertainty radius) that a vision model can evaluate, creating a closed correction loop.

### 1.2 Repositories (Monorepo Layout)

```
dvoc-protocol/
├── dvoc-core/          # Core loop engine (pure Python)
├── dvoc-os/            # Desktop backend (PyAutoGUI + mss + X11)
├── dvoc-web/           # Browser backend (Playwright) — phase 2
├── dvoc-vm/            # VM backend (Docker/VNC) — phase 2
├── dvoc-py/            # Public SDK wrapper — after core stable
├── docs/               # Design docs and specs
└── pyproject.toml      # Workspace root
```

---

## 2. Core Architecture

### 2.1 Loop Engine

```python
state = DVOCState(task=task)
backend = OSSBackend()
draft = planner.draft(task)  # initial guess

while True:
    frame = backend.capture()
    annotated = renderer.overlay(frame, draft, radius)

    error, confidence = verifier.verify(annotated, draft)

    state = state.push(DVOCSnapshot(draft, annotated, error, confidence))
    decision = policy.evaluate(state)

    match decision:
        case Decision.REFINE:
            draft = corrector.correct(draft, error, state.iteration)
        case Decision.ACT_SAFE:
            backend.execute(draft)
            persist_success(state)
            break
        case Decision.ABORT_OSCILLATION:
            persist_failure(state)
            break
```

### 2.2 State Model

Immutable per-iteration dataclasses:

```python
@dataclass(frozen=True)
class Point:
    x: float
    y: float

@dataclass(frozen=True)
class Vector:
    dx: float
    dy: float

@dataclass(frozen=True)
class DVOCSnapshot:
    iteration: int
    draft_point: Point
    annotated_frame: Image
    error_vector: Vector
    confidence: float

@dataclass(frozen=True)
class DVOCState:
    task: str
    snapshots: tuple[DVOCSnapshot, ...]

    def push(self, snapshot: DVOCSnapshot) -> DVOCState:
        ...

    @property
    def current_draft(self) -> Point: ...

    @property
    def iteration(self) -> int: ...

All state is immutable. History is append-only via `push()`. `converged` is computed by Policy, not stored. Full replayability.

---

## 3. Module Specifications

### 3.1 Planner

| Phase | Implementation | Input → Output |
|-------|---------------|----------------|
| MVP | Manual mode: returns fixed/configured point. Heuristic mode: screen center fallback | `task: str` → `Point` |
| Production | Vision model mode: task + screenshot → predicted coordinate | `task: str, frame: Image` → `Point` |

Configurable via `Planner(mode="manual", manual_target=Point(x,y))` or `Planner(mode="model")`.

### 3.2 Verifier

Parses structured spatial feedback from a vision model.

Returns:
- `error_vector: Vector` — estimated pixel offset
- `confidence: float` — 0.0–1.0 confidence in the estimate

**MVP:** Simulated verifier that adds controlled noise for testing convergence.
**Production:** Model prompt with structured JSON output (`{"dx": ..., "dy": ..., "confidence": ...}`).

### 3.3 Corrector

Applies damped update:

```
new_point = current_point + alpha(iteration) × error_vector
```

Alpha decay:
- iter 0: `alpha = 1.0`
- iter 1: `alpha = 0.5`
- iter 2+: `alpha = 0.25`

Convergence: `|error| < epsilon` (default 5px, configurable) AND `confidence >= threshold` (default 0.85) for **2 consecutive iterations**.

### 3.4 Renderer

Pillow-based overlay on screenshots:

1. **Crosshair** at draft point — red, bold (3px thick), 30px arms
2. **Uncertainty circle** — blue, 3px thick, radius = `max(10, (1 - confidence) × 200)` px
3. **Iteration counter** — top-left, white text on black bg, font size 24
4. **Coordinate label** — bottom-right, white text on black bg, `"(x, y) ± r px"`

All elements are bold/high-contrast for reliable model detection.

### 3.5 Policy

| Condition | Decision |
|-----------|----------|
| `|error| < epsilon` and `confidence > threshold` for 2 consecutive iterations | `ACT_SAFE` |
| Error magnitude increasing 3+ consecutive iterations | `ABORT_OSCILLATION` |
| All other cases | `REFINE` (continue loop) |

No maximum iteration limit. Each refinement appends to an ephemeral context that the vision model sees, enabling it to learn from past corrections.

### 3.6 Ephemeral Context

Per-action conversation history:

```python
@dataclass
class EphemeralContext:
    action_id: str
    task: str
    turns: list[EphemeralTurn]
    converged: bool
    result: Optional[ActionResult]

@dataclass
class EphemeralTurn:
    draft: Point
    annotated_frame: Image  # base64-encoded for model API
    error: Vector
    confidence: float
```

On `ACT_SAFE`: persist `(action_id, task, final_coords, iteration_count, result)` and discard context.
On `ABORT_OSCILLATION`: persist as failed attempt.

---

## 4. Backend Interface

All backends implement:

```python
class DVOCBackend(ABC):
    @abstractmethod
    def capture(self) -> Image: ...
    @abstractmethod
    def execute(self, action: Action) -> ActionResult: ...
    @abstractmethod
    def get_screen_geometry(self) -> Geometry: ...
```

### 4.1 DVOC-OS (Desktop Backend)

**MVP Stack:**
- `mss` for screen capture (fast, multi-monitor)
- `PyAutoGUI` for mouse click/keyboard
- X11 backend (Linux)
- Unified coordinate system normalized to 0–1 or pixel-based with DPI awareness

**Key challenges to solve:**
- Multi-monitor capture
- DPI scaling
- Window-relative vs absolute coordinates

### 4.2 DVOC-Web (Future)

Playwright-based browser automation:
- Viewport screenshots
- DOM → coordinate mapping
- Click/type/scroll execution
- Shadow DOM resolution

### 4.3 DVOC-VM (Future)

Docker + VNC or QEMU sandbox:
- Isolated execution
- Snapshot/revert
- Benchmarking infrastructure

---

## 5. DVOC-py (SDK)

```python
from dvoc import DVOC

agent = DVOC(
    backend="os",
    model="gpt-4o"
)

result = agent.run("Click the login button and type credentials")
```

Responsible for:
- Backend selection and configuration
- Model integration (API key management)
- Executing the full DVOC loop
- Returning results and metadata

---

## 6. Testing Strategy

### Unit Tests (per module)
- Planner: manual mode returns correct point
- Verifier: simulated mode produces expected error vectors
- Corrector: converges given known error sequence
- Renderer: overlay is deterministic, crosshair at correct position
- Policy: correct decision for each state configuration
- State: immutability, snapshot history append

### Integration Tests
- Loop engine with simulated verifier converges within N iterations
- Loop engine aborts on oscillation
- Full state replay matches original execution

### E2E Tests (DVOC-OS)
- Capture + click on known screen region
- DVOC loop corrects simulated offset to hit target

---

## 7. Build Order

| Step | Package | Module | Depends On |
|------|---------|--------|------------|
| 1 | core | State + Point + Vector | nothing |
| 2 | core | Planner (manual mode) | State |
| 3 | core | Verifier (simulated) | State, Image |
| 4 | core | Corrector | State, Vector |
| 5 | core | Renderer | State, Image |
| 6 | core | Policy | State |
| 7 | core | LoopEngine | all above |
| 8 | core | Backend ABC | nothing |
| 9 | os | OSSBackend (capture + click) | Backend ABC |
| 10 | os | Integration: core + os loop | all above |
| 11 | core | Planner (model mode) | LoopEngine |
| 12 | core | Verifier (model mode) | LoopEngine |
| 13 | os | Full E2E: model-based loop | all above |
| 14 | py | DVOC SDK | core, os |
| 15 | web | DVOC-Web backend | core |
| 16 | vm | DVOC-VM backend | core |

---

## 8. Performance Considerations

- Screenshot capture: medium cost (use mss, avoid PIL conversion overhead)
- Vision model inference: dominant cost (optimize for correctness, not latency)
- DVOC-core logic: negligible
- Renderer: deterministic, sub-millisecond with Pillow
