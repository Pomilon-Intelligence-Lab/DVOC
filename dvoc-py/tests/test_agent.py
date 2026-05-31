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
