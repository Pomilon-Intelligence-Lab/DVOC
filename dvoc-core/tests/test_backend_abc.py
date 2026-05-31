import pytest
from dvoc_core import DVOCBackend, Action, ActionResult, Geometry


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
