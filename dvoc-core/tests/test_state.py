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
