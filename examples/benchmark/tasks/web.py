"""Web task definitions.

Each task loads HTML from fixture files and provides metadata
about the target element and its selector.

Element dimensions (target_w, target_h) are filled at runtime
by querying getBoundingClientRect.
"""

import os
from dataclasses import dataclass


FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..", "html_fixtures")


def _load(name: str) -> str:
    path = os.path.join(FIXTURE_DIR, name)
    with open(path) as f:
        return f.read()


@dataclass
class WebTask:
    id: str
    name: str
    prompt: str
    target_selector: str
    difficulty: str
    html: str
    target: tuple[float, float] | None = None
    target_w: float = 0
    target_h: float = 0


LOGIN_HTML = _load("w1_login_form.html")
NAV_HTML = _load("w2_nav_bar.html")
CARD_HTML = _load("w3_card_grid.html")
DASHBOARD_HTML = _load("w4_dashboard.html")
DROPDOWN_HTML = _load("w5_dropdown.html")

TASKS = [
    WebTask(id="W1", name="login-form",
            prompt="Click the Sign In button",
            target_selector="#login-btn",
            difficulty="easy", html=LOGIN_HTML),
    WebTask(id="W2", name="nav-bar",
            prompt="Click the Docs link in the navigation",
            target_selector="#nav-docs",
            difficulty="easy", html=NAV_HTML),
    WebTask(id="W3", name="card-grid",
            prompt="Click the Beta project card",
            target_selector="#card-beta",
            difficulty="medium", html=CARD_HTML),
    WebTask(id="W4", name="dashboard",
            prompt="Click the Edit button for Bob",
            target_selector="#edit-bob",
            difficulty="hard", html=DASHBOARD_HTML),
    WebTask(id="W5", name="dropdown",
            prompt="Click the Profile link in the dropdown menu",
            target_selector="#menu-profile",
            difficulty="hard", html=DROPDOWN_HTML),
]
