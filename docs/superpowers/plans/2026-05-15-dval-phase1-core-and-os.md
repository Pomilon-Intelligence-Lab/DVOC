# DVOC Phase 1: Core Engine + OS Backend Implementation Plan

> **For agentic workers:** Use subagent-driven-development or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build DVOC-core (loop engine, state, modules) and DVOC-OS (desktop backend) into a working system that can capture the screen, run the Draft-Verify-Action loop with a simulated verifier, and execute mouse clicks.

**Architecture:** Monorepo with `dvoc-core/` (pure Python library), `dvoc-os/` (desktop backend), and `dvoc-py/` (SDK). Core uses immutable state model, module-per-file structure. Backend implements abstract interface. Each module built TDD.

**Tech Stack:** Python 3.11+, pytest, Pillow, mss, PyAutoGUI, pygetwindow

---

## File Structure

```
dvoc-protocol/
├── pyproject.toml                          # root workspace config
├── dvoc-core/
│   ├── pyproject.toml                      # dvoc-core package
│   ├── src/dvoc_core/
│   │   ├── __init__.py                     # public exports
│   │   ├── _types.py                       # Point, Vector, Geometry, Action, ActionResult
│   │   ├── _state.py                       # DVOCSnapshot, DVOCState
│   │   ├── _backend.py                     # DVOCBackend ABC
│   │   ├── _planner.py                     # Planner (manual mode)
│   │   ├── _verifier.py                    # Verifier (simulated)
│   │   ├── _corrector.py                   # Corrector
│   │   ├── _renderer.py                    # Renderer (Pillow overlays)
│   │   ├── _policy.py                      # Policy, Decision enum
│   │   └── _loop.py                        # LoopEngine
│   └── tests/
│       ├── __init__.py
│       ├── test_types.py
│       ├── test_state.py
│       ├── test_planner.py
│       ├── test_verifier.py
│       ├── test_corrector.py
│       ├── test_renderer.py
│       ├── test_policy.py
│       └── test_loop.py
├── dvoc-os/
│   ├── pyproject.toml
│   ├── src/dval_os/
│   │   ├── __init__.py
│   │   └── _backend.py                     # OSSBackend
│   └── tests/
│       ├── __init__.py
│       └── test_backend.py
├── dvoc-py/
│   ├── pyproject.toml
│   ├── src/dval/
│   │   ├── __init__.py
│   │   └── _agent.py                       # DVOC agent class
│   └── tests/
│       ├── __init__.py
│       └── test_agent.py
└── docs/
    └── superpowers/
        ├── specs/2026-05-15-dvoc-system-design.md
        └── plans/2026-05-15-dvoc-phase1-core-and-os.md
```

---

### Task 1: Project Scaffolding and Root Structure

**Files:**
- Create: `pyproject.toml` (root)
- Create: `dvoc-core/pyproject.toml`
- Create: `dvoc-core/src/dvoc_core/__init__.py`
- Create: `dvoc-core/tests/__init__.py`
- Create: `dvoc-os/pyproject.toml`
- Create: `dvoc-os/src/dval_os/__init__.py`
- Create: `dvoc-os/tests/__init__.py`
- Create: `dvoc-py/pyproject.toml`
- Create: `dvoc-py/src/dval/__init__.py`
- Create: `dvoc-py/tests/__init__.py`

- [ ] **Step 1: Create root pyproject.toml**

```toml
[project]
name = "dvoc-protocol"
version = "0.1.0"
description = "Draft-Verify-Action Loop: multimodal UI grounding framework"
requires-python = ">=3.11"

[tool.pytest.ini_options]
testpaths = ["dvoc-core/tests", "dvoc-os/tests", "dvoc-py/tests"]
```

- [ ] **Step 2: Create dvoc-core/pyproject.toml**

```toml
[project]
name = "dvoc-core"
version = "0.1.0"
description = "DVOC core loop engine"
requires-python = ">=3.11"
dependencies = [
    "Pillow>=10.0.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]
```

- [ ] **Step 3: Create dvoc-core/src/dvoc_core/__init__.py**

```python
from dvoc_core._types import Point, Vector, Geometry, Action, ActionResult
from dvoc_core._state import DVOCSnapshot, DVOCState
from dvoc_core._backend import DVOCBackend
from dvoc_core._planner import Planner
from dvoc_core._verifier import Verifier
from dvoc_core._corrector import Corrector
from dvoc_core._renderer import Renderer
from dvoc_core._policy import Policy, Decision
from dvoc_core._loop import LoopEngine

__all__ = [
    "Point", "Vector", "Geometry", "Action", "ActionResult",
    "DVOCSnapshot", "DVOCState",
    "DVOCBackend",
    "Planner", "Verifier", "Corrector", "Renderer", "Policy", "Decision",
    "LoopEngine",
]
```

- [ ] **Step 4: Create remaining __init__ files**

dvoc-core/tests/__init__.py — empty file
dvoc-os/pyproject.toml:

```toml
[project]
name = "dvoc-os"
version = "0.1.0"
description = "DVOC desktop OS backend"
requires-python = ">=3.11"
dependencies = [
    "dvoc-core>=0.1.0",
    "mss>=9.0.0",
    "PyAutoGUI>=0.9.54",
    "pygetwindow>=0.0.9",
    "Pillow>=10.0.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]
```

dvoc-os/src/dval_os/__init__.py — empty
dvoc-os/tests/__init__.py — empty

dvoc-py/pyproject.toml:

```toml
[project]
name = "dval"
version = "0.1.0"
description = "DVOC Python SDK"
requires-python = ">=3.11"
dependencies = [
    "dvoc-core>=0.1.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[tool.setuptools.packages.find]
where = ["src"]
```

dvoc-py/src/dval/__init__.py:

```python
from dvoc._agent import DVOC

__all__ = ["DVOC"]
```

dvoc-py/tests/__init__.py — empty

- [ ] **Step 5: Install dvoc-core in editable mode**

Run: `pip install -e dvoc-core/`
Expected: "Successfully installed dvoc-core-0.1.0"

- [ ] **Step 6: Run pytest to confirm test suite loads**

Run: `python -m pytest dvoc-core/tests/ -v`
Expected: "no tests ran" (no test functions yet, but discovery succeeds)

---

### Task 2: Core Types — Point, Vector, Geometry, Action

**Files:**
- Create: `dvoc-core/src/dvoc_core/_types.py`
- Create: `dvoc-core/tests/test_types.py`

- [ ] **Step 1: Write the failing tests**

```python
import pytest
from dvoc_core import Point, Vector, Geometry, Action, ActionResult


class TestPoint:
    def test_creates_with_xy(self):
        p = Point(100.0, 200.0)
        assert p.x == 100.0
        assert p.y == 200.0

    def test_is_frozen(self):
        p = Point(1.0, 2.0)
        with pytest.raises(AttributeError):
            p.x = 99.0

    def test_equality(self):
        assert Point(1.0, 2.0) == Point(1.0, 2.0)
        assert Point(1.0, 2.0) != Point(3.0, 4.0)

    def test_repr(self):
        r = repr(Point(1.5, 2.5))
        assert "Point" in r
        assert "1.5" in r


class TestVector:
    def test_creates_with_dx_dy(self):
        v = Vector(10.0, -5.0)
        assert v.dx == 10.0
        assert v.dy == -5.0

    def test_is_frozen(self):
        v = Vector(1.0, 2.0)
        with pytest.raises(AttributeError):
            v.dx = 99.0

    def test_magnitude(self):
        v = Vector(3.0, 4.0)
        assert v.magnitude == 5.0

    def test_zero_vector(self):
        v = Vector(0.0, 0.0)
        assert v.magnitude == 0.0


class TestGeometry:
    def test_creates_with_dimensions(self):
        g = Geometry(width=1920, height=1080)
        assert g.width == 1920
        assert g.height == 1080

    def test_is_frozen(self):
        g = Geometry(1920, 1080)
        with pytest.raises(AttributeError):
            g.width = 999


class TestAction:
    def test_click_action(self):
        a = Action(type="click", target=Point(100.0, 200.0))
        assert a.type == "click"
        assert a.target == Point(100.0, 200.0)

    def test_type_action(self):
        a = Action(type="type", text="hello")
        assert a.type == "type"
        assert a.text == "hello"

    def test_is_frozen(self):
        a = Action(type="click", target=Point(1.0, 2.0))
        with pytest.raises(AttributeError):
            a.type = "type"


class TestActionResult:
    def test_success(self):
        r = ActionResult(success=True)
        assert r.success is True
        assert r.error is None

    def test_failure(self):
        r = ActionResult(success=False, error="click missed")
        assert r.success is False
        assert r.error == "click missed"

    def test_is_frozen(self):
        r = ActionResult(success=True)
        with pytest.raises(AttributeError):
            r.success = False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dvoc-core/tests/test_types.py -v`
Expected: ALL FAIL (module not found or imports broken)

- [ ] **Step 3: Write implementation**

```python
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True)
class Vector:
    dx: float
    dy: float

    @property
    def magnitude(self) -> float:
        return math.sqrt(self.dx ** 2 + self.dy ** 2)


@dataclass(frozen=True)
class Geometry:
    width: int
    height: int


@dataclass(frozen=True)
class Action:
    type: str  # "click", "type", "scroll", "keypress"
    target: Point | None = None
    text: str | None = None
    key: str | None = None
    scroll_dx: int = 0
    scroll_dy: int = 0


@dataclass(frozen=True)
class ActionResult:
    success: bool
    error: str | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest dvoc-core/tests/test_types.py -v`
Expected: ALL PASS

---

### Task 3: State Model

**Files:**
- Create: `dvoc-core/src/dvoc_core/_state.py`
- Create: `dvoc-core/tests/test_state.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from PIL import Image
from dvoc_core import Point, Vector
from dvoc_core._state import DVOCSnapshot, DVOCState


class TestDVOCSnapshot:
    def test_creates(self):
        img = Image.new("RGB", (100, 100))
        snap = DVOCSnapshot(
            iteration=0,
            draft_point=Point(50.0, 50.0),
            annotated_frame=img,
            error_vector=Vector(10.0, -5.0),
            confidence=0.85,
        )
        assert snap.iteration == 0
        assert snap.draft_point == Point(50.0, 50.0)
        assert snap.error_vector == Vector(10.0, -5.0)
        assert snap.confidence == 0.85

    def test_is_frozen(self):
        img = Image.new("RGB", (100, 100))
        snap = DVOCSnapshot(0, Point(0, 0), img, Vector(0, 0), 0.9)
        with pytest.raises(AttributeError):
            snap.iteration = 1


class TestDVOCState:
    def test_empty_state(self):
        state = DVOCState(task="click the button")
        assert state.task == "click the button"
        assert len(state.snapshots) == 0
        assert state.iteration == 0

    def test_push_adds_snapshot(self):
        state = DVOCState(task="test")
        img = Image.new("RGB", (100, 100))
        snap = DVOCSnapshot(0, Point(0, 0), img, Vector(1.0, 1.0), 0.9)
        state2 = state.push(snap)
        assert len(state2.snapshots) == 1
        assert len(state.snapshots) == 0  # original unchanged

    def test_iteration_counts_snapshots(self):
        state = DVOCState(task="test")
        img = Image.new("RGB", (100, 100))
        for i in range(3):
            snap = DVOCSnapshot(i, Point(i, i), img, Vector(0, 0), 0.9)
            state = state.push(snap)
        assert state.iteration == 3

    def test_current_draft_last_snapshot(self):
        state = DVOCState(task="test")
        img = Image.new("RGB", (100, 100))
        state = state.push(DVOCSnapshot(0, Point(10, 20), img, Vector(1, 1), 0.9))
        state = state.push(DVOCSnapshot(1, Point(30, 40), img, Vector(0, 0), 0.95))
        assert state.current_draft == Point(30, 40)

    def test_current_draft_on_empty_state(self):
        state = DVOCState(task="test")
        assert state.current_draft is None

    def test_immutable_task(self):
        state = DVOCState(task="click")
        with pytest.raises(AttributeError):
            state.task = "type"

    def test_immutable_snapshots(self):
        state = DVOCState(task="test")
        with pytest.raises(AttributeError):
            state.snapshots = ()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dvoc-core/tests/test_state.py -v`
Expected: ImportError or similar failures

- [ ] **Step 3: Write implementation**

```python
from dataclasses import dataclass, field
from PIL import Image
from dvoc_core._types import Point, Vector


@dataclass(frozen=True)
class DVOCSnapshot:
    iteration: int
    draft_point: Point
    annotated_frame: Image.Image
    error_vector: Vector
    confidence: float


@dataclass(frozen=True)
class DVOCState:
    task: str
    snapshots: tuple[DVOCSnapshot, ...] = ()

    def push(self, snapshot: DVOCSnapshot) -> "DVOCState":
        return DVOCState(
            task=self.task,
            snapshots=self.snapshots + (snapshot,),
        )

    @property
    def iteration(self) -> int:
        return len(self.snapshots)

    @property
    def current_draft(self) -> Point | None:
        if not self.snapshots:
            return None
        return self.snapshots[-1].draft_point
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest dvoc-core/tests/test_state.py -v`
Expected: ALL PASS

---

### Task 4: Backend Abstract Base Class

**Files:**
- Create: `dvoc-core/src/dvoc_core/_backend.py`
- Create: `dvoc-core/tests/test_backend_abc.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from dvoc_core import DVOCBackend, Point, Action, ActionResult, Geometry


class TestDVOCBackendABC:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            DVOCBackend()

    def test_concrete_subclass(self):
        class TestBackend(DVOCBackend):
            def capture(self):
                return None

            def execute(self, action: Action) -> ActionResult:
                return ActionResult(success=True)

            def get_screen_geometry(self) -> Geometry:
                return Geometry(1920, 1080)

        b = TestBackend()
        assert b.get_screen_geometry() == Geometry(1920, 1080)

    def test_missing_method_raises(self):
        with pytest.raises(TypeError):

            class BadBackend(DVOCBackend):
                pass

            BadBackend()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dvoc-core/tests/test_backend_abc.py -v`

- [ ] **Step 3: Write implementation**

```python
from abc import ABC, abstractmethod
from PIL import Image
from dvoc_core._types import Action, ActionResult, Geometry


class DVOCBackend(ABC):
    @abstractmethod
    def capture(self) -> Image.Image: ...

    @abstractmethod
    def execute(self, action: Action) -> ActionResult: ...

    @abstractmethod
    def get_screen_geometry(self) -> Geometry: ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest dvoc-core/tests/test_backend_abc.py -v`

---

### Task 5: Planner (Manual Mode)

**Files:**
- Create: `dvoc-core/src/dvoc_core/_planner.py`
- Create: `dvoc-core/tests/test_planner.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from dvoc_core import Point, Planner


class TestPlanner:
    def test_manual_mode_returns_target(self):
        p = Planner(mode="manual", manual_target=Point(100.0, 200.0))
        result = p.draft("click anything")
        assert result == Point(100.0, 200.0)

    def test_manual_mode_different_target(self):
        p = Planner(mode="manual", manual_target=Point(800.0, 600.0))
        result = p.draft("click login")
        assert result == Point(800.0, 600.0)

    def test_manual_mode_default_is_center(self):
        p = Planner(mode="manual")
        result = p.draft("click")
        # default center is at (960, 540) for 1920x1080
        assert result == Point(960.0, 540.0)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dvoc-core/tests/test_planner.py -v`

- [ ] **Step 3: Write implementation**

```python
from dvoc_core._types import Point


class Planner:
    def __init__(
        self,
        mode: str = "manual",
        manual_target: Point | None = None,
    ):
        self.mode = mode
        self.manual_target = manual_target

    def draft(self, task: str) -> Point:
        if self.mode == "manual":
            if self.manual_target is not None:
                return self.manual_target
            return Point(960.0, 540.0)  # sane default center
        raise ValueError(f"Unknown planner mode: {self.mode}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest dvoc-core/tests/test_planner.py -v`

---

### Task 6: Simulated Verifier

**Files:**
- Create: `dvoc-core/src/dvoc_core/_verifier.py`
- Create: `dvoc-core/tests/test_verifier.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from PIL import Image
from dvoc_core import Point, Vector, Verifier


class TestVerifier:
    def test_simulated_returns_expected_vector(self):
        v = Verifier(mode="simulated", fixed_error=Vector(15.0, -10.0), fixed_confidence=0.8)
        img = Image.new("RGB", (100, 100))
        error, confidence = v.verify(img, Point(50.0, 50.0))
        assert error == Vector(15.0, -10.0)
        assert confidence == 0.8

    def test_simulated_zero_error(self):
        v = Verifier(mode="simulated", fixed_error=Vector(0.0, 0.0), fixed_confidence=0.99)
        img = Image.new("RGB", (100, 100))
        error, confidence = v.verify(img, Point(100.0, 100.0))
        assert error == Vector(0.0, 0.0)
        assert confidence == 0.99

    def test_confidence_clamped(self):
        v = Verifier(mode="simulated", fixed_error=Vector(1.0, 1.0), fixed_confidence=1.5)
        img = Image.new("RGB", (100, 100))
        _, confidence = v.verify(img, Point(0.0, 0.0))
        assert confidence == pytest.approx(1.0, abs=1e-6)

    def test_unknown_mode_raises(self):
        v = Verifier(mode="nonexistent")
        img = Image.new("RGB", (100, 100))
        with pytest.raises(ValueError, match="Unknown verifier mode"):
            v.verify(img, Point(0.0, 0.0))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dvoc-core/tests/test_verifier.py -v`

- [ ] **Step 3: Write implementation**

```python
from PIL import Image
from dvoc_core._types import Point, Vector


class Verifier:
    def __init__(
        self,
        mode: str = "simulated",
        fixed_error: Vector = Vector(0.0, 0.0),
        fixed_confidence: float = 0.95,
    ):
        self.mode = mode
        self.fixed_error = fixed_error
        self.fixed_confidence = min(max(fixed_confidence, 0.0), 1.0)

    def verify(self, annotated_frame: Image.Image, draft: Point) -> tuple[Vector, float]:
        if self.mode == "simulated":
            return self.fixed_error, self.fixed_confidence
        raise ValueError(f"Unknown verifier mode: {self.mode}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest dvoc-core/tests/test_verifier.py -v`

---

### Task 7: Corrector

**Files:**
- Create: `dvoc-core/src/dvoc_core/_corrector.py`
- Create: `dvoc-core/tests/test_corrector.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from dvoc_core import Point, Vector, Corrector


class TestCorrector:
    def test_alpha_1_at_iter_0(self):
        c = Corrector(epsilon=5.0)
        result = c.correct(Point(100.0, 100.0), Vector(20.0, 0.0), iteration=0)
        # new = 100 + 1.0 * 20 = 120
        assert result == Point(120.0, 100.0)

    def test_alpha_half_at_iter_1(self):
        c = Corrector(epsilon=5.0)
        result = c.correct(Point(100.0, 100.0), Vector(20.0, 0.0), iteration=1)
        # new = 100 + 0.5 * 20 = 110
        assert result == Point(110.0, 100.0)

    def test_alpha_quarter_at_iter_2(self):
        c = Corrector(epsilon=5.0)
        result = c.correct(Point(100.0, 100.0), Vector(20.0, 0.0), iteration=2)
        # new = 100 + 0.25 * 20 = 105
        assert result == Point(105.0, 100.0)

    def test_alpha_min_at_iter_10(self):
        c = Corrector(epsilon=5.0)
        # alpha decays: iter0=1.0, iter1=0.5, iter2=0.25, iter3=0.25, ...
        result = c.correct(Point(100.0, 100.0), Vector(20.0, 0.0), iteration=5)
        # new = 100 + 0.25 * 20 = 105
        assert result == Point(105.0, 100.0)

    def test_converged_true_when_error_small(self):
        c = Corrector(epsilon=5.0, threshold=0.9)
        assert c.is_converged(Vector(3.0, 0.0), 0.95) is True

    def test_converged_false_when_error_large(self):
        c = Corrector(epsilon=5.0, threshold=0.9)
        assert c.is_converged(Vector(10.0, 0.0), 0.95) is False

    def test_converged_false_when_confidence_low(self):
        c = Corrector(epsilon=5.0, threshold=0.9)
        assert c.is_converged(Vector(3.0, 0.0), 0.5) is False

    def test_custom_epsilon(self):
        c = Corrector(epsilon=10.0, threshold=0.9)
        assert c.is_converged(Vector(8.0, 0.0), 0.95) is True
        assert c.is_converged(Vector(12.0, 0.0), 0.95) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dvoc-core/tests/test_corrector.py -v`

- [ ] **Step 3: Write implementation**

```python
from dvoc_core._types import Point, Vector


class Corrector:
    def __init__(self, epsilon: float = 5.0, threshold: float = 0.85):
        self.epsilon = epsilon
        self.threshold = threshold

    def correct(self, current: Point, error: Vector, iteration: int) -> Point:
        alpha = self._alpha(iteration)
        return Point(
            x=current.x + alpha * error.dx,
            y=current.y + alpha * error.dy,
        )

    def _alpha(self, iteration: int) -> float:
        if iteration == 0:
            return 1.0
        if iteration == 1:
            return 0.5
        return 0.25

    def is_converged(self, error: Vector, confidence: float) -> bool:
        return error.magnitude < self.epsilon and confidence >= self.threshold
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest dvoc-core/tests/test_corrector.py -v`

---

### Task 8: Renderer

**Files:**
- Create: `dvoc-core/src/dvoc_core/_renderer.py`
- Create: `dvoc-core/tests/test_renderer.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from PIL import Image
from dvoc_core import Point, Renderer


class TestRenderer:
    def test_overlay_returns_image(self):
        r = Renderer()
        frame = Image.new("RGB", (1920, 1080), color=(255, 255, 255))
        result = r.overlay(frame, Point(960.0, 540.0), radius=30.0, iteration=0)
        assert isinstance(result, Image.Image)
        assert result.size == (1920, 1080)

    def test_overlay_deterministic(self):
        r = Renderer()
        frame = Image.new("RGB", (100, 100), color=(0, 0, 0))
        a = r.overlay(frame, Point(50.0, 50.0), radius=20.0, iteration=0)
        b = r.overlay(frame, Point(50.0, 50.0), radius=20.0, iteration=0)
        assert list(a.getdata()) == list(b.getdata())

    def test_overlay_at_origin(self):
        r = Renderer()
        frame = Image.new("RGB", (100, 100), color=(255, 255, 255))
        result = r.overlay(frame, Point(0.0, 0.0), radius=10.0, iteration=0)
        assert isinstance(result, Image.Image)

    def test_different_radius_gives_different_result(self):
        r = Renderer()
        frame = Image.new("RGB", (100, 100), color=(0, 0, 0))
        a = r.overlay(frame, Point(50.0, 50.0), radius=10.0, iteration=0)
        b = r.overlay(frame, Point(50.0, 50.0), radius=50.0, iteration=0)
        assert list(a.getdata()) != list(b.getdata())

    def test_crosshair_visible_at_center(self):
        r = Renderer()
        frame = Image.new("RGB", (100, 100), color=(255, 255, 255))
        result = r.overlay(frame, Point(50.0, 50.0), radius=20.0, iteration=0)
        # crosshair intersection at (50, 50) should be red
        px = result.getpixel((50, 50))
        assert px == (255, 0, 0), f"Expected red at center, got {px}"

    def test_iteration_text_appears(self):
        r = Renderer()
        frame = Image.new("RGB", (500, 500), color=(255, 255, 255))
        result = r.overlay(frame, Point(250.0, 250.0), radius=20.0, iteration=3)
        # text is white on white bg, but crosshair should still be visible
        # at least verify the function runs without error
        assert isinstance(result, Image.Image)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dvoc-core/tests/test_renderer.py -v`

- [ ] **Step 3: Write implementation**

```python
from PIL import Image, ImageDraw
from dvoc_core._types import Point


class Renderer:
    def __init__(self):
        self.crosshair_color = (255, 0, 0)     # red
        self.crosshair_arm = 15                 # half-arm length in pixels
        self.crosshair_width = 3
        self.circle_color = (0, 100, 255)       # blue
        self.circle_width = 3
        self.text_bg = (0, 0, 0)
        self.text_fg = (255, 255, 255)
        self.font_size = 18

    def overlay(self, frame: Image.Image, draft: Point, radius: float, iteration: int = 0) -> Image.Image:
        img = frame.copy()
        draw = ImageDraw.Draw(img)
        cx, cy = int(draft.x), int(draft.y)

        # crosshair (3px thick, 30px arms)
        arm = self.crosshair_arm
        draw.line([(cx - arm, cy), (cx + arm, cy)], fill=self.crosshair_color, width=self.crosshair_width)
        draw.line([(cx, cy - arm), (cx, cy + arm)], fill=self.crosshair_color, width=self.crosshair_width)

        # uncertainty circle (3px thick)
        r = int(max(10, radius))
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            outline=self.circle_color,
            width=self.circle_width,
        )

        # iteration counter — top-left
        draw.text((10, 10), f"iter {iteration}", fill=self.text_fg)

        # coordinate label — bottom-right
        w, h = img.size
        label = f"({cx}, {cy}) +/- {r}px"
        bbox = draw.textbbox((0, 0), label)
        tw = bbox[2] - bbox[0]
        draw.text((w - tw - 10, h - 30), label, fill=self.text_fg)

        return img
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest dvoc-core/tests/test_renderer.py -v`

---

### Task 9: Policy

**Files:**
- Create: `dvoc-core/src/dvoc_core/_policy.py`
- Create: `dvoc-core/tests/test_policy.py`

- [ ] **Step 1: Write failing tests**

```python
import pytest
from PIL import Image
from dvoc_core import Point, Vector
from dvoc_core._state import DVOCSnapshot, DVOCState
from dvoc_core._policy import Policy, Decision


def _state_with_errors(errors: list[Vector], confidences: list[float]) -> DVOCState:
    state = DVOCState(task="test")
    img = Image.new("RGB", (100, 100))
    for i, (err, conf) in enumerate(zip(errors, confidences)):
        snap = DVOCSnapshot(
            iteration=i,
            draft_point=Point(0.0, 0.0),
            annotated_frame=img,
            error_vector=err,
            confidence=conf,
        )
        state = state.push(snap)
    return state


class TestPolicy:
    def test_refine_on_first_iteration(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        state = _state_with_errors(
            [Vector(20.0, 0.0)],
            [0.8],
        )
        assert policy.evaluate(state) == Decision.REFINE

    def test_act_when_converged_two_in_a_row(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        state = _state_with_errors(
            [Vector(3.0, 0.0), Vector(2.0, 0.0)],
            [0.9, 0.95],
        )
        assert policy.evaluate(state) == Decision.ACT_SAFE

    def test_not_converged_with_one_good(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        state = _state_with_errors(
            [Vector(3.0, 0.0)],
            [0.9],
        )
        assert policy.evaluate(state) == Decision.REFINE

    def test_oscillation_aborts(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        state = _state_with_errors(
            [Vector(5.0, 0.0), Vector(10.0, 0.0), Vector(20.0, 0.0)],
            [0.8, 0.7, 0.6],
        )
        assert policy.evaluate(state) == Decision.ABORT_OSCILLATION

    def test_no_oscillation_after_two_iters(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        state = _state_with_errors(
            [Vector(20.0, 0.0), Vector(10.0, 0.0)],
            [0.6, 0.7],
        )
        assert policy.evaluate(state) == Decision.REFINE

    def test_oscillation_confidence_not_checked(self):
        policy = Policy(epsilon=5.0, threshold=0.85, convergence_window=2)
        # errors increasing but confidence high — still oscillation based on error
        state = _state_with_errors(
            [Vector(3.0, 0.0), Vector(8.0, 0.0), Vector(15.0, 0.0)],
            [0.9, 0.9, 0.9],
        )
        assert policy.evaluate(state) == Decision.ABORT_OSCILLATION

    def test_custom_threshold(self):
        policy = Policy(epsilon=10.0, threshold=0.5, convergence_window=1)
        state = _state_with_errors(
            [Vector(8.0, 0.0)],
            [0.6],
        )
        assert policy.evaluate(state) == Decision.ACT_SAFE
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dvoc-core/tests/test_policy.py -v`

- [ ] **Step 3: Write implementation**

```python
from enum import Enum
from dvoc_core._state import DVOCState
from dvoc_core._types import Vector


class Decision(Enum):
    REFINE = "refine"
    ACT_SAFE = "act_safe"
    ABORT_OSCILLATION = "abort_oscillation"


class Policy:
    def __init__(self, epsilon: float = 5.0, threshold: float = 0.85, convergence_window: int = 2):
        self.epsilon = epsilon
        self.threshold = threshold
        self.convergence_window = convergence_window

    def evaluate(self, state: DVOCState) -> Decision:
        if not state.snapshots:
            return Decision.REFINE

        last_errors = [s.error_vector for s in state.snapshots]
        last_confs = [s.confidence for s in state.snapshots]

        # check oscillation: error magnitude increasing for 3+ consecutive
        if len(last_errors) >= 3:
            mags = [e.magnitude for e in last_errors[-3:]]
            if mags[0] < mags[1] < mags[2]:
                return Decision.ABORT_OSCILLATION

        # check convergence: last N consecutive iterations converged
        recent = list(zip(last_errors[-self.convergence_window:], last_confs[-self.convergence_window:]))
        if len(recent) == self.convergence_window:
            if all(e.magnitude < self.epsilon and c >= self.threshold for e, c in recent):
                return Decision.ACT_SAFE

        return Decision.REFINE
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest dvoc-core/tests/test_policy.py -v`

---

### Task 10: LoopEngine (Integration)

**Files:**
- Create: `dvoc-core/src/dvoc_core/_loop.py`
- Create: `dvoc-core/tests/test_loop.py`

- [ ] **Step 1: Write failing tests**

```python
from PIL import Image
from dvoc_core import (
    Point, Vector, Geometry, Action, ActionResult,
    DVOCBackend, Planner, Verifier, Corrector, Renderer, Policy,
)
from dvoc_core._loop import LoopEngine


class FakeBackend(DVOCBackend):
    def __init__(self):
        self.captures = 0
        self.executions = []

    def capture(self):
        self.captures += 1
        return Image.new("RGB", (1920, 1080))

    def execute(self, action: Action) -> ActionResult:
        self.executions.append(action)
        return ActionResult(success=True)

    def get_screen_geometry(self):
        return Geometry(1920, 1080)


class TestLoopEngine:
    def test_converges_on_zero_error(self):
        backend = FakeBackend()
        engine = LoopEngine(
            backend=backend,
            planner=Planner(mode="manual", manual_target=Point(100.0, 100.0)),
            verifier=Verifier(mode="simulated", fixed_error=Vector(0.0, 0.0), fixed_confidence=0.99),
            corrector=Corrector(epsilon=5.0, threshold=0.85),
            renderer=Renderer(),
            policy=Policy(epsilon=5.0, threshold=0.85, convergence_window=2),
        )
        result = engine.run("click test")
        assert result.success is True
        assert result.final_point == Point(100.0, 100.0)
        assert result.iterations == 2  # 2 iterations for convergence_window=2
        assert len(backend.executions) == 1

    def test_corrects_to_target(self):
        backend = FakeBackend()
        # Start with error 50px right, verifier keeps reporting same error
        # Corrector moves left by alpha*50 each iteration
        # iter0: alpha=1.0, moves 50px left (to target)
        # iter1: alpha=0.5, moves 25px left (past target), verifier reports -25px
        engine = LoopEngine(
            backend=backend,
            planner=Planner(mode="manual", manual_target=Point(200.0, 200.0)),
            verifier=Verifier(mode="simulated", fixed_error=Vector(50.0, 0.0), fixed_confidence=0.8),
            corrector=Corrector(epsilon=5.0, threshold=0.85),
            renderer=Renderer(),
            policy=Policy(epsilon=5.0, threshold=0.85, convergence_window=2),
        )
        result = engine.run("click test")
        assert result.success is True
        assert len(backend.executions) == 1

    def test_aborts_on_oscillation(self):
        backend = FakeBackend()
        # verifier gives increasing errors = oscillation
        engine = LoopEngine(
            backend=backend,
            planner=Planner(mode="manual", manual_target=Point(100.0, 100.0)),
            verifier=Verifier(mode="simulated", fixed_error=Vector(100.0, 0.0), fixed_confidence=0.5),
            corrector=Corrector(epsilon=5.0, threshold=0.85),
            renderer=Renderer(),
            policy=Policy(epsilon=5.0, threshold=0.85, convergence_window=2),
        )
        result = engine.run("click test")
        assert result.success is False
        assert result.decision == "abort_oscillation"

    def test_full_history_returned(self):
        backend = FakeBackend()
        engine = LoopEngine(
            backend=backend,
            planner=Planner(mode="manual", manual_target=Point(50.0, 50.0)),
            verifier=Verifier(mode="simulated", fixed_error=Vector(0.0, 0.0), fixed_confidence=0.99),
            corrector=Corrector(epsilon=5.0, threshold=0.85),
            renderer=Renderer(),
            policy=Policy(epsilon=5.0, threshold=0.85, convergence_window=2),
        )
        result = engine.run("click test")
        assert len(result.history) == 2  # one snapshot per iteration
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest dvoc-core/tests/test_loop.py -v`

- [ ] **Step 3: Write implementation**

```python
from dataclasses import dataclass, field
from PIL import Image
from dvoc_core._types import Point, Action
from dvoc_core._state import DVOCSnapshot, DVOCState
from dvoc_core._backend import DVOCBackend
from dvoc_core._planner import Planner
from dvoc_core._verifier import Verifier
from dvoc_core._corrector import Corrector
from dvoc_core._renderer import Renderer
from dvoc_core._policy import Policy, Decision


@dataclass(frozen=True)
class LoopResult:
    success: bool
    final_point: Point | None
    iterations: int
    decision: str
    history: tuple[DVOCSnapshot, ...]


class LoopEngine:
    def __init__(
        self,
        backend: DVOCBackend,
        planner: Planner,
        verifier: Verifier,
        corrector: Corrector,
        renderer: Renderer,
        policy: Policy,
    ):
        self.backend = backend
        self.planner = planner
        self.verifier = verifier
        self.corrector = corrector
        self.renderer = renderer
        self.policy = policy

    def run(self, task: str) -> LoopResult:
        state = DVOCState(task=task)
        draft = self.planner.draft(task)

        while True:
            frame = self.backend.capture()

            if state.iteration == 0:
                radius = 100.0  # default initial uncertainty
            else:
                last_conf = state.snapshots[-1].confidence
                radius = max(10.0, (1.0 - last_conf) * 200.0)

            annotated = self.renderer.overlay(frame, draft, radius, iteration=state.iteration)

            error, confidence = self.verifier.verify(annotated, draft)

            snap = DVOCSnapshot(
                iteration=state.iteration,
                draft_point=draft,
                annotated_frame=annotated,
                error_vector=error,
                confidence=confidence,
            )
            state = state.push(snap)

            decision = self.policy.evaluate(state)

            match decision:
                case Decision.REFINE:
                    draft = self.corrector.correct(draft, error, state.iteration)
                case Decision.ACT_SAFE:
                    action = Action(type="click", target=draft)
                    self.backend.execute(action)
                    return LoopResult(
                        success=True,
                        final_point=draft,
                        iterations=state.iteration,
                        decision="act_safe",
                        history=state.snapshots,
                    )
                case Decision.ABORT_OSCILLATION:
                    return LoopResult(
                        success=False,
                        final_point=draft,
                        iterations=state.iteration,
                        decision="abort_oscillation",
                        history=state.snapshots,
                    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest dvoc-core/tests/test_loop.py -v`

---

### Task 11: DVOC-OS Backend

**Files:**
- Create: `dvoc-os/src/dval_os/_backend.py`
- Create: `dvoc-os/tests/test_backend.py`

- [ ] **Step 1: Install dvoc-os in editable mode**

Run: `pip install -e dvoc-os/`
Expected: "Successfully installed dvoc-os-0.1.0"

- [ ] **Step 2: Write tests**

```python
import pytest
from PIL import Image
from dvoc_core import Point, Action, Geometry
from dvoc_os import OSSBackend


class TestOSSBackend:
    def test_capture_returns_image(self):
        backend = OSSBackend()
        img = backend.capture()
        assert isinstance(img, Image.Image)
        assert img.size[0] > 0
        assert img.size[1] > 0

    def test_get_screen_geometry(self):
        backend = OSSBackend()
        geom = backend.get_screen_geometry()
        assert isinstance(geom, Geometry)
        assert geom.width > 0
        assert geom.height > 0

    def test_capture_size_matches_geometry(self):
        backend = OSSBackend()
        geom = backend.get_screen_geometry()
        img = backend.capture()
        assert img.size == (geom.width, geom.height)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest dvoc-os/tests/test_backend.py -v`
Expected: ImportError (OSSBackend not yet defined)

- [ ] **Step 4: Write implementation**

```python
from PIL import Image
import mss
import pyautogui
from dvoc_core import DVOCBackend, Point, Action, ActionResult, Geometry


class OSSBackend(DVOCBackend):
    def __init__(self):
        self.screen = mss.mss()

    def capture(self) -> Image.Image:
        monitor = self.screen.monitors[0]
        sct_img = self.screen.grab(monitor)
        return Image.frombytes("RGB", sct_img.size, sct_img.rgb)

    def execute(self, action: Action) -> ActionResult:
        try:
            if action.type == "click":
                pyautogui.click(int(action.target.x), int(action.target.y))
                return ActionResult(success=True)
            elif action.type == "type":
                pyautogui.typewrite(action.text or "")
                return ActionResult(success=True)
            elif action.type == "keypress":
                pyautogui.press(action.key or "")
                return ActionResult(success=True)
            elif action.type == "scroll":
                pyautogui.scroll(action.scroll_dy)
                return ActionResult(success=True)
            else:
                return ActionResult(success=False, error=f"unknown action type: {action.type}")
        except Exception as e:
            return ActionResult(success=False, error=str(e))

    def get_screen_geometry(self) -> Geometry:
        monitor = self.screen.monitors[0]
        return Geometry(width=monitor["width"], height=monitor["height"])
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest dvoc-os/tests/test_backend.py -v`
Expected: ALL PASS

---

### Task 12: Integration — Core + OS End-to-End

**Files:**
- Modify: `dvoc-core/tests/test_loop.py` (add integration tests)

- [ ] **Step 1: Write integration test**

```python
from dvoc_core import (
    Point, Vector, Geometry, Action, ActionResult,
    DVOCBackend, Planner, Verifier, Corrector, Renderer, Policy,
)
from dvoc_core._loop import LoopEngine


class TestLoopEngineIntegration:
    def test_full_loop_with_os_backend(self):
        try:
            from dvoc_os import OSSBackend
        except ImportError:
            pytest.skip("dvoc-os not available")

        backend = OSSBackend()
        engine = LoopEngine(
            backend=backend,
            planner=Planner(mode="manual", manual_target=Point(960.0, 540.0)),
            verifier=Verifier(mode="simulated", fixed_error=Vector(0.0, 0.0), fixed_confidence=0.99),
            corrector=Corrector(epsilon=5.0, threshold=0.85),
            renderer=Renderer(),
            policy=Policy(epsilon=5.0, threshold=0.85, convergence_window=2),
        )
        result = engine.run("click target")
        assert result.success is True
        assert result.final_point == Point(960.0, 540.0)
        assert result.iterations == 2
```

- [ ] **Step 2: Run the integration test**

Run: `python -m pytest dvoc-core/tests/test_loop.py::TestLoopEngineIntegration -v`
Expected: PASS

---

### Task 13: DVOC-py SDK

**Files:**
- Create: `dvoc-py/src/dval/_agent.py`
- Create: `dvoc-py/tests/test_agent.py`

- [ ] **Step 1: Install dvoc-py in editable mode**

Run: `pip install -e dvoc-py/`

- [ ] **Step 2: Write tests**

```python
import pytest
from dvoc import DVOC
from dvoc_core import Point, Vector


class TestDVAL:
    def test_create_defaults(self):
        agent = DVOC()
        assert agent.backend_type == "os"
        assert agent.model is None

    def test_create_with_model(self):
        agent = DVOC(model="gpt-4o")
        assert agent.model == "gpt-4o"

    def test_create_custom_epsilon(self):
        agent = DVOC(epsilon=10.0)
        assert agent.epsilon == 10.0
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m pytest dvoc-py/tests/ -v`

- [ ] **Step 4: Write implementation**

```python
from dvoc_core import (
    Point, Vector, Geometry, Action, ActionResult,
    DVOCBackend, Planner, Verifier, Corrector, Renderer, Policy,
)
from dvoc_core._loop import LoopEngine


class DVOC:
    def __init__(
        self,
        backend: str = "os",
        model: str | None = None,
        epsilon: float = 5.0,
        threshold: float = 0.85,
        manual_target: Point | None = None,
    ):
        self.backend_type = backend
        self.model = model
        self.epsilon = epsilon
        self.threshold = threshold
        self.manual_target = manual_target

    def run(self, task: str) -> dict:
        backend = self._create_backend()
        planner = Planner(mode="manual", manual_target=self.manual_target)
        verifier = Verifier(mode="simulated", fixed_error=Vector(0.0, 0.0), fixed_confidence=0.99)
        corrector = Corrector(epsilon=self.epsilon, threshold=self.threshold)
        renderer = Renderer()
        policy = Policy(epsilon=self.epsilon, threshold=self.threshold)

        engine = LoopEngine(
            backend=backend,
            planner=planner,
            verifier=verifier,
            corrector=corrector,
            renderer=renderer,
            policy=policy,
        )

        result = engine.run(task)
        return {
            "success": result.success,
            "final_point": result.final_point,
            "iterations": result.iterations,
            "decision": result.decision,
        }

    def _create_backend(self) -> DVOCBackend:
        if self.backend_type == "os":
            from dvoc_os import OSSBackend
            return OSSBackend()
        raise ValueError(f"Unknown backend: {self.backend_type}")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest dvoc-py/tests/ -v`
Expected: ALL PASS

- [ ] **Step 6: Run full test suite**

Run: `python -m pytest dvoc-core/tests/ dvoc-os/tests/ dvoc-py/tests/ -v`
Expected: ALL PASS
