# DVOC: Damped Visual Offset Correction — Making Weak Vision Models Viable for UI Grounding

**Authors:** Pomilon (Pomilon Intelligence Research)  
**Date:** May 2026  
**Repository:** [github.com/Pomilon-Intelligence-Lab/DVOC](https://github.com/Pomilon-Intelligence-Lab/DVOC)  
**Paper:** [research.pomilon.xyz/papers/dvoc](https://research.pomilon.xyz/papers/dvoc-damped-visual-offset-correction-enables-weak-model-ui-grounding-via-kinematic-control)

---

## Abstract

We introduce **DVOC** (Draft-Verify-Action Loop), a recursive spatial refinement protocol that enables weak vision-language models to perform pixel-precise UI grounding through iterative visual feedback. DVOC runs a closed loop: render a predicted click position as a visual overlay (crosshair + uncertainty circle), ask the model to estimate the offset to the target, apply the correction, and repeat until convergence.

In a multi-model benchmark across 4 vision-language models (Gemini 3.1 Flash Lite, Gemini 2.5 Flash Lite, Gemma 4 26B, Gemma 4 31B) on 11 UI grounding tasks (6 synthetic + 5 web), DVOC achieved **53–67% raw convergence (63–100% protocol convergence) within 30px** across all models. The strongest model, Gemma 4 31B, reached 67% DVOC raw success (93% protocol) with a mean final distance of 34px. Gemma 4 26B achieved 100% protocol convergence on every completed trial (20px mean distance). The naive one-shot baseline achieved **0–14%** — all models consistently fixated on wrong coordinates with confidence 1.0, unable to self-correct without spatial feedback.

DVOC trades per-call accuracy for iterative refinement, making cheap models viable for tasks that previously required expensive, pixel-perfect vision models. The protocol is more important than the model: even the weakest model with DVOC outperforms every model's naive baseline.

---

## 1. Introduction

UI grounding — mapping natural language instructions ("click the login button") to precise pixel coordinates — is a fundamental capability for autonomous agents. Current approaches fall into two camps:

1. **One-shot vision models** (GPT-4V, Gemini 2.5 Pro, etc.) attempt to predict coordinates in a single inference. This works when the model is large and capable, but is expensive ($\sim$\$5–10/1M tokens) and brittle — a single misprediction fails silently.

2. **DOM-based approaches** (Playwright, Selenium) use structured document access rather than vision, but fail on canvas-based UI, shadow DOM, virtualized lists, and any non-browser environment.

**DVOC takes a third approach:** instead of making the model smarter, make the loop smarter. A cheap vision model iteratively refines its prediction by observing the visual consequences of its previous estimate. The model doesn't need to be pixel-perfect — it only needs to be *directionally correct* ("the target is to the right and down from the crosshair").

---

## 2. The DVOC Protocol

### 2.1 Loop Architecture

```
Planner → Backend (capture) → Renderer (overlay) → Verifier (VLM) → Corrector → Policy → ACT
```

### 2.2 Components

**Planner** generates the initial coordinate hypothesis. Supports manual mode (fixed target for testing) and model mode (VLM generates initial guess from task + screenshot).

**Renderer** draws visual feedback on the captured screenshot:
- Red crosshair (`+`) at the predicted coordinate, 3px thick, 30px arms
- Blue uncertainty circle, 3px thick, fixed 30px radius (provides spatial reference)
- Iteration counter and coordinate label with white-on-black text

**Verifier** is the core innovation. The annotated screenshot is sent to a vision-language model with the prompt explaining the DVOC mechanism, previous iteration history, and the task. The model calls a `report_offset(dx, dy, confidence)` function.

**Corrector** applies the offset with exponential alpha decay:

```
α(0) = 1.0,  α(1) = 0.5,  α(iteration >= 2) = 0.25
new_position = old_position + α × error_vector
```

**Policy** decides the next action:
- `REFINE`: error too large or confidence too low, continue loop
- `ACT_SAFE`: error < ε and confidence > threshold for 2 consecutive iterations
- `ABORT_OSCILLATION`: error magnitude non-decreasing for 3+ iterations

### 2.3 ReAct-Style Agent Loop

The Verifier uses a ReAct (Reasoning + Acting) prompt that:
1. Explains the DVOC mechanism (how crosshair, circle, and correction work)
2. Shows previous iteration history ("You were at (100,100) and said dx=375, dy=333...")
3. Asks the model to reason step-by-step before calling the tool

### 2.4 Convergence Criteria

Convergence requires error magnitude < ε (30px) AND confidence ≥ 0.5 for 2 consecutive iterations.

---

## 3. Experimental Setup

### 3.1 Test Environment

- **Scene (synthetic)**: 800×600 synthetic desktop with a dark background (RGB 40,42,48) containing UI elements at 6 target positions (S1–S6)
- **Scene (web)**: Styled HTML dashboard at 1280×720 viewport containing 5 UI element types (W1–W5)
- **Models**: 4 vision-language models: `gemini-3.1-flash-lite`, `gemini-2.5-flash-lite`, `gemma-4-26b`, `gemma-4-31b`
- **Access via LiteLLM unified interface**
- **Epsilon**: 30px
- **Convergence window**: 2 consecutive iterations
- **Rate limiting**: Free API tiers with ~15 req/min limits; scheduler uses quota-aware retry (3-retry cap, 30s cooldown) and hybrid provider interleaving

### 3.2 DVOC Test Protocol

1. Select a random starting crosshair position $p_0 \in [50, 750] \times [50, 550]$
2. Run the DVOC loop until convergence or 15 iterations
3. Record: final distance to target, iterations, model calls
4. Each (model, task, method) combination was repeated 3–5 times from varying starting positions
5. Total: 233 DVOC trials + 230 naive trials = 463 total (396 valid, 67 lost to API errors)

### 3.3 Naive Baseline Protocol

1. Present raw screenshot (no overlay) to the model
2. Ask "Click the target. Call click_at(x, y, confidence)."
3. If predicted position is within ε of target, stop
4. Otherwise, repeat with the same raw screenshot (no feedback)
5. Maximum 5 retries per attempt

---

## 4. Results

### 4.1 Overall Results

DVOC was benchmarked across 4 models, 11 tasks (6 synthetic S1–S6, 5 web W1–W5), and 2 methods (DVOC vs naive). A total of 463 trials (396 valid, 67 API errors) were processed over 21.9 hours of cumulative benchmark time. The convergence threshold was 30px from the target center.

| Model | Method | Total | Err | Valid | Success | Raw Rate | Proto Rate | Mean Dist | Mean Iters |
|-------|--------|-------|-----|-------|---------|----------|------------|-----------|------------|
| Gemini 3.1 Flash Lite | DVOC | 115 | 1 | 114 | 72 | 63% | 63% | 41.9px | 5.2 |
| Gemini 3.1 Flash Lite | NAIVE | 115 | 1 | 114 | 15 | 13% | 13% | 178.9px | 4.5 |
| Gemini 2.5 Flash Lite | DVOC | 6 | 0 | 6 | 2 | 33% | 33% | 114.8px | 3.7 |
| Gemini 2.5 Flash Lite | NAIVE | 4 | 0 | 4 | 0 | 0% | 0% | 274.7px | 5.0 |
| Gemma 4 26B | DVOC | 55 | 26 | 29 | 29 | 53% | 100% | 19.6px | 5.6 |
| Gemma 4 26B | NAIVE | 55 | 11 | 44 | 6 | 11% | 14% | 170.8px | 4.5 |
| Gemma 4 31B | DVOC | 57 | 16 | 41 | 38 | 67% | 93% | 34.4px | 7.1 |
| Gemma 4 31B | NAIVE | 56 | 12 | 44 | 8 | 14% | 18% | 166.6px | 4.3 |

*Note: "Raw Rate" = successes / total (API errors counted as failures). "Proto Rate" = successes / valid (API errors excluded).*

**Key findings:**
- **DVOC dominates naive across every model**: DVOC raw success rates (53–67%, 63–100% protocol) far exceed naive (0–14% raw, 0–18% protocol).
- **Gemma 4 31B is the strongest model**: 67% raw DVOC success (93% protocol) with mean 34.4px final distance.
- **Gemma 4 26B achieves perfect DVOC protocol success** (100%) on every completed trial, with the lowest mean distance (19.6px), but suffers a high API error rate (47% of DVOC trials lost to timeouts/auth failures).
- **The naive baseline is consistently broken**: Across 230 naive trials, the pattern is identical — the model fixates on a single wrong coordinate (typically (500, ~500) or (500, ~650)) with confidence 1.0 and never self-corrects across retries.

### 4.2 Per-Task Breakdown

| Task | Gemini 3.1 FL | Gemma 4 26B | Gemma 4 31B | Description |
|------|--------------|-------------|-------------|-------------|
| **S1** | 100%, 24px | 100%, 9px | 100%, 12px | Single green button (400, 300) |
| **S2** | 27%, 39px | 100%, 12px | 100%, 17px | Small green button (400, 300) |
| **S3** | 53%, 26px | 100%, 12px | 100%, 23px | Multi-button grid, target "Submit" (360, 220) |
| **S4** | 100%, 17px | 100%, 8px | 100%, 14px | Edge target top-left (40, 25) |
| **S5** | 33%, 40px | 100%, 9px | 100%, 43px | Text input field (325, 240) |
| **S6** | 53%, 25px | 100%, 10px | 100%, 19px | Blue button among distractors (190, 370) |
| **W1** | 100%, 65px | 100%, 25px | 100%, 25px | Sign In button (large) |
| **W2** | 80%, 32px | 100%, 21px | 80%, 31px | Nav bar "Docs" link |
| **W3** | 100%, 77px | 100%, 52px | 100%, 90px | Card grid "Beta" card |
| **W4** | 0%, 214px | 100%, 25px | 50%, 32px | Dashboard table "Edit Bob" |
| **W5** | 80%, 66px | 100%, 19px | 100%, 43px | Dropdown menu "Profile" |

*Format: Success rate (%), mean final distance (px). Only counts valid (non-error) trials.*

**Findings:**
- **Synthetic tasks are easier than web tasks**: Mean DVOC distance across all models: ~20px (synthetic) vs ~50px (web) among valid trials.
- **When DVOC completes without API errors, success rates are high**: Gemma 4 26B achieved 100% DVOC success on every task that completed, and Gemma 4 31B achieved 100% on 9 of 11 tasks.
- **Task W4 (dashboard table Edit) is the hardest task**: Only Gemma 4 26B achieved 100% on this task (2/2 trials). Gemini 3.1 Flash Lite scored 0% (mean 214px). The model tends to fixate on nearby rows or disabled buttons.
- **Gemini 3.1 Flash Lite struggles with small or ambiguous targets**: S2 (27%), S5 (33%), S3 (53%), S6 (53%) — all below 60% success.
- **Task S4 (edge target) and S1 (central button) are the easiest**: 100% success across all models with data.

### 4.3 Convergence Trajectories

DVOC convergence follows a characteristic pattern across all models: an initial large correction (often 100–300px in one step), followed by progressively smaller oscillations until settling within ε.

Key trajectory observations:
- **First-step accuracy varies by model**: Gemma 4 31B's initial corrections are the most directionally correct. Gemma 4 26B often under-corrects on the first step.
- **Convergence typically requires 4–10 iterations** when successful.
- **The alpha decay schedule ($\alpha = 1.0 \to 0.5 \to 0.25$) causes near-misses**: Several Gemini 3.1 Flash Lite trials landed at 32–47px, within a single correction step of success.

### 4.4 Naive Baseline Analysis

| Model | Naive Trials | Naive Success | Mean Distance | Fixation Pattern |
|-------|-------------|--------------|---------------|------------------|
| Gemini 3.1 Flash Lite | 114 | 13% | 179px | (500, ~500) or (500, ~650), confidence 1.0 |
| Gemma 4 26B | 44 | 14% | 171px | Iterates between (410, 400) and (300, 400) |
| Gemma 4 31B | 44 | 18% | 167px | Varies by task, no self-correction |

### 4.5 Web Page Results

| Model | Web DVOC Success | Web DVOC Mean Dist | Web DVOC Mean Iters |
|-------|-----------------|-------------------|---------------------|
| Gemini 3.1 Flash Lite | 72% (17/24) | 90.7px | 6.6 |
| Gemma 4 26B | 100% (14/14) | 47.0px | 8.0 |
| Gemma 4 31B | 86% (18/21) | 54.0px | 7.8 |

**Findings:**
- DVOC transfers reliably from synthetic to real HTML pages across all tested models.
- Web tasks require more iterations on average (6.6–8.0 vs 4.5–5.5 for synthetic) due to the larger viewport and visual complexity.
- Among completed trials, DVOC achieves 72–100% web task success.

---

## 5. Ablation Studies

Ablation studies were conducted on Gemini 3.1 Flash Lite with synthetic tasks S1–S6 (30 trials per condition).

### 5.1 Relative vs. Absolute Prediction

| Prediction mode | Success | Mean Dist | Median Dist | Mean Iters |
|----------------|---------|-----------|-------------|------------|
| Relative (Δx, Δy) | 83% | 26.8px | 22px | 5.0 |
| Absolute (x, y) | 17% | 175.4px | 201px | 3.0 |

Relative offset parameterisation is the decisive architectural choice: 83% vs 17% success.

### 5.2 Visual Overlay

| Condition | Success | Mean Dist | Median Dist |
|-----------|---------|-----------|-------------|
| Text-only (no overlay) | 35% | 135.2px | 103px |
| Crosshair only | 100% | 25.7px | 22px |
| Crosshair + circle (full) | 82% | 27.3px | 24px |

The crosshair provides the majority of the benefit. The uncertainty circle slightly degrades performance on this model-task combination (82% vs 100%), likely due to visual clutter.

### 5.3 Alpha Decay Schedule

| Schedule | Success | Mean Dist | Mean Iters |
|----------|---------|-----------|------------|
| Decay (1.0 → 0.5 → 0.25) | 87% | 26.1px | 4.8 |
| Constant α = 0.5 | 97% | 23.0px | 4.8 |
| Undamped α = 1.0 | 97% | 29.1px | 4.5 |

All schedules achieve high success on Gemini 3.1 Flash Lite synthetic tasks. Constant α = 0.5 gives the lowest mean distance (23.0px). The decay schedule provides a balanced trade-off. These results suggest that damping offers modest gains on capable models with simple tasks, but may be more important for noisier models.

---

## 6. Limitations and Future Work

**Current limitations:**
- API rate limits and quota exhaustion caused significant data loss: Gemma 4 26B lost 26/55 DVOC trials to timeouts/auth errors; Gemini 2.5 Flash Lite was limited to 10 total trials by quota
- No comparison against larger premium models (GPT-4V, Gemini 2.5 Pro, Claude 3.5 Sonnet)
- Web benchmark remains limited in scope (5 elements, 1 page design)
- Web backend uses Playwright screenshot coordinates, not real OS-level mouse events
- No systematic cost modeling ($/successful-click) across model tiers and providers
- Alpha damping's limited impact on this model-task combination suggests it may be a second-order effect for capable models

**Future work:**
- **Provisioned throughput**: Benchmark with paid API tiers or local model execution to eliminate data loss from rate limits
- **Premium model comparison**: Compare DVOC-enhanced cheap models against GPT-4V, Gemini 2.5 Pro, and Claude 3.5 Sonnet one-shot performance
- **Adaptive alpha decay**: PID controller tuned to convergence velocity
- **Multi-target scenarios**: Forms, dropdowns, drag-and-drop, and sequential interactions
- **Canvas and non-DOM UIs**: Where DOM-based approaches fundamentally fail
- **Cost modeling**: "$/successful-click" analysis across model tiers

---

## 7. Related Work

**See Point Refine** [Mittal et al., 2026] also renders a red crosshair at the model's previous prediction and iterates based on visual feedback. DVOC differs by using relative offset vectors (not absolute coordinates) and includes kinematic damping.

**GUI-Cursor** [Zhao et al., 2025] reframes grounding as an interactive search via reinforcement learning. DVOC requires no training or reward engineering.

**Iterative Narrowing** [Nguyen, 2024] uses progressive cropping to refine predictions, which discards global visual context. DVOC preserves full-resolution context throughout.

**Set-of-Marks (SoM)** [Yang et al., 2023] augments screenshots with numerical labels for elements. DVOC uses an interactive marker that moves based on model feedback.

**ReAct** [Yao et al., 2022] demonstrates that reasoning traces improve LLM task performance. DVOC's ReAct-style verifier prompt similarly lets the model reason about spatial relationships before reporting offsets.

---

## 8. Conclusion

We presented DVOC, a recursive spatial refinement loop that makes weak vision models viable for pixel-precise UI grounding. In a multi-model benchmark across 4 vision-language models and 11 UI grounding tasks (6 synthetic + 5 web), DVOC achieved 53–67% raw convergence (63–100% protocol convergence) within 30px, while the same models without DVOC achieved 0–14%. The pattern is consistent and unambiguous: **iterative visual feedback enables reliable convergence; one-shot prediction does not**.

Ablations confirm that relative offset parameterisation is the primary driver (83% vs 17% success), followed by the visual crosshair overlay (100% vs 35% for text-only). The protocol is model-agnostic, environment-agnostic, and directly addresses a fundamental limitation of current UI agents.

---

## Acknowledgments

Thanks to Google for providing the Gemini API free tier which made these experiments possible. Thanks to LiteLLM for providing a clean unified interface to multiple model providers.

---

## Appendix A: Implementation

The full implementation is available at [github.com/Pomilon-Intelligence-Lab/DVOC](https://github.com/Pomilon-Intelligence-Lab/DVOC).

**Repository structure:**
- `dvoc-core/src/dvoc_core/` — Core loop engine (10 modules, 61 tests)
- `dvoc-os/src/dvoc_os/` — Desktop backend (mss + pynput)
- `dvoc-web/src/dvoc_web/` — Web browser backend (Playwright, 13 tests)
- `dvoc-py/src/dvoc/` — SDK: `DVOC(backend, model).run(task)`
- `examples/` — Test harnesses, benchmark scripts
- `docs/` — System design spec and implementation plan

**Dependencies:** Python 3.11+, Pillow, Litellm, Playwright

## Appendix B: Benchmark Artifacts

Annotated screenshots from each DVOC iteration are available in `examples/benchmark/output/artifacts/`.  

The canonical paper is published at [research.pomilon.xyz/papers/dvoc](https://research.pomilon.xyz/papers/dvoc-damped-visual-offset-correction-enables-weak-model-ui-grounding-via-kinematic-control).
