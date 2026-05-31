import os, random
from dataclasses import dataclass, field
from typing import Optional

SEED = 42

# Fixed starting positions — same across all models and tasks
rng = random.Random(SEED)
START_POSITIONS = [
    (rng.randint(80, 720), rng.randint(80, 520))  # synthetic 800x600 viewport
    for _ in range(5)
]

EPSILON = 30.0          # convergence threshold for DVOC Policy
MIN_HIT_RADIUS = 30.0   # minimum success radius (element size or this floor)
MAX_DVAL_ITERS = 15
MAX_NAIVE_RETRIES = 5
REPEATS_PER_POSITION = 3

DVAL_SYSTEM = (
    "You are a DVOC (Draft-Verify-Action Loop) verifier. "
    "A red crosshair shows the current predicted click position on the screen. "
    "A fixed blue circle provides spatial reference.\n\n"
    "Call report_offset(dx, dy, confidence) with the pixel offset from the "
    "crosshair to the target element center.\n"
    "dx: pixels right (negative = left). dy: pixels down (negative = up).\n"
    "confidence: 0.0 (uncertain) to 1.0 (certain).\n\n"
    "Only report dx=0, dy=0 when the crosshair is within a few pixels of the target. "
    "If uncertain, set lower confidence so the loop keeps refining."
)

# Overlay-mode-specific system prompts for ablation
DVAL_SYSTEM_BY_MODE = {
    "full": DVAL_SYSTEM,
    "crosshair-only": (
        "You are a DVOC (Draft-Verify-Action Loop) verifier. "
        "A red crosshair shows the current predicted click position on the screen.\n\n"
        "Call report_offset(dx, dy, confidence) with the pixel offset from the "
        "crosshair to the target element center.\n"
        "dx: pixels right (negative = left). dy: pixels down (negative = up).\n"
        "confidence: 0.0 (uncertain) to 1.0 (certain).\n\n"
        "Only report dx=0, dy=0 when the crosshair is within a few pixels of the target. "
        "If uncertain, set lower confidence so the loop keeps refining."
    ),
    "none": (
        "You are a DVOC (Draft-Verify-Action Loop) verifier. "
        "Use the text history below to determine your previous estimated click position.\n\n"
        "Call report_offset(dx, dy, confidence) with the pixel offset from your "
        "previous estimate to the target element center.\n"
        "dx: pixels right (negative = left). dy: pixels down (negative = up).\n"
        "confidence: 0.0 (uncertain) to 1.0 (certain).\n\n"
        "Only report dx=0, dy=0 when you believe you are within a few pixels of the target. "
        "If uncertain, set lower confidence so the loop keeps refining."
    ),
}

DVAL_ABSOLUTE_SYSTEM = (
    "You are a DVOC (Draft-Verify-Action Loop) verifier. "
    "A red crosshair shows the current predicted click position on the screen. "
    "A fixed blue circle provides spatial reference.\n\n"
    "Call click_at(x, y, confidence) with the ABSOLUTE pixel coordinates "
    "of the target element center (not the offset from the crosshair).\n"
    "confidence: 0.0 (uncertain) to 1.0 (certain).\n\n"
    "Only report the same coordinates as previous iteration when the "
    "crosshair is within a few pixels of the target. "
    "If uncertain, set lower confidence so the loop keeps refining."
)

NAIVE_SYSTEM_FIRST = (
    "You are a UI clicking agent. Given a screenshot of a screen, "
    "determine the pixel coordinates of the target element.\n\n"
    "Call click_at(x, y, confidence) with the center pixel coordinates "
    "of the target element."
)

NAIVE_SYSTEM_RETRY = (
    "You tried to click at ({x:.0f}, {y:.0f}) but that position was outside "
    "the target element. The target is still: {task}\n\n"
    "Look at the screenshot again and call click_at(x, y, confidence) "
    "with corrected coordinates."
)

OFFSET_TOOLS = [{"type":"function","function":{
    "name":"report_offset","parameters":{"type":"object","properties":{
        "dx":{"type":"number","description":"Pixels right. Negative=left."},
        "dy":{"type":"number","description":"Pixels down. Negative=up."},
        "confidence":{"type":"number","description":"Confidence 0-1"},
    },"required":["dx","dy","confidence"]},
}}]

CLICK_TOOLS = [{"type":"function","function":{
    "name":"click_at","parameters":{"type":"object","properties":{
        "x":{"type":"number"},"y":{"type":"number"},
        "confidence":{"type":"number"},
    },"required":["x","y","confidence"]},
}}]

OUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUT_DIR, exist_ok=True)

MODELS = {
    "gemini-3.1-flash-lite": {
        "name": "gemini/gemini-3.1-flash-lite",
        "provider": "gemini",
    },
    "gemini-2.5-flash-lite": {
        "name": "gemini/gemini-2.5-flash-lite",
        "provider": "gemini",
    },
    "gemma-4-26b": {
        "names": ["gemini/gemma-4-26b-a4b-it", "openrouter/google/gemma-4-26b-a4b-it:free"],
        "provider": "hybrid",
    },
    "gemma-4-31b": {
        "names": ["gemini/gemma-4-31b-it", "openrouter/google/gemma-4-31b-it:free"],
        "provider": "hybrid",
    },
    "nemotron-12b-vl": {
        "name": "openrouter/nvidia/nemotron-nano-12b-v2-vl:free",
        "provider": "openrouter",
    },
    "nemotron-30b": {
        "name": "openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
        "provider": "openrouter",
    },
    "gemma-4-26b-via-or": {
        "name": "openrouter/google/gemma-4-26b-a4b-it:free",
        "provider": "openrouter",
    },
    "gemma-4-31b-via-or": {
        "name": "openrouter/google/gemma-4-31b-it:free",
        "provider": "openrouter",
    },
    "openrouter-free-vision": {
        "name": "openrouter/openrouter/free",
        "provider": "openrouter",
    },
}

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
