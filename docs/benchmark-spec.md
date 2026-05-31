# Benchmark Specification

## Objective

Quantitatively evaluate DVOC against naive one-shot prediction across multiple vision-language models and diverse UI tasks. Establish the conditions under which iterative spatial refinement outperforms single-shot guessing, and measure the magnitude of improvement per model.

## Success Criteria

- Statistical comparison of DVOC vs naive success rate across models
- Per-task analysis showing which tasks benefit most from DVOC
- Cross-model ranking of DVOC convergence speed (iterations to converge)
- Exportable data for paper tables and figures

## Task Catalog

### Synthetic Tasks (no browser needed)

| ID | Name | Description | Target Size | Difficulty |
|----|------|-------------|-------------|------------|
| S1 | single-button | Green button on dark background (existing) | 80×50 px | Easy |
| S2 | small-target | Tiny button (24×12 px) | 24×12 px | Medium |
| S3 | multi-button | 4 buttons, pick by label text | 80×40 px each | Medium |
| S4 | edge-target | Button within 30px of screen corner | 60×30 px | Hard |
| S5 | input-field | Text input with placeholder, click to focus | 200×30 px | Medium |
| S6 | distractors | Target among visually similar distractors | 60×30 px | Hard |

### Web Tasks (Playwright browser)

| ID | Name | Description | Elements | Difficulty |
|----|------|-------------|----------|------------|
| W1 | login-form | Email + password + submit button | 2 inputs, 1 button | Easy |
| W2 | nav-bar | Navigation links in header bar | 4-5 links | Easy |
| W3 | card-grid | Click card by heading text | 6 cards | Medium |
| W4 | dense-dashboard | Charts + tables + buttons close together | 12+ elements | Hard |
| W5 | dropdown-menu | Click to open dropdown, then select item | 2-stage interaction | Hard |

## Starting Positions

For each task, 5 systematic starting positions:

```
P1: Center of viewport
P2: Top-left quadrant (100, 100)
P3: Top-right quadrant (viewport_w-100, 100)
P4: Bottom-left quadrant (100, viewport_h-100)
P5: Bottom-right quadrant (viewport_w-100, viewport_h-100)
```

## Trial Structure

Per configuration `(task, model, method, start_position)`:
- **Repeats**: 3 trials (to measure variance)
- **Total per model**: 6 synth × 5 pos × 3 reps × 2 methods = 180 trials
- **Total across 6 models**: 1,080 trials

## Metrics Collected

| Metric | Description |
|--------|-------------|
| `success` | Final distance < 30px epsilon |
| `final_dist` | Euclidean distance from prediction to target center |
| `iterations` | Total DVOC iterations (or naive retries) |
| `model_calls` | API calls made |
| `elapsed` | Wall-clock time in seconds |
| `iteration_history` | Per-iteration (draft, error, confidence, distance) — DVOC only |
| `start_position` | Initial (x, y) |
| `target_position` | Actual target (x, y) |
| `confidence` | Final model confidence |
| `error` | Any error message |

## Model Lineup

| Key | API Name | Provider | Quota |
|-----|----------|----------|-------|
| gemini-3.1-flash-lite | `gemini/gemini-3.1-flash-lite` | Gemini API | 500 RPD |
| gemini-2.5-flash-lite | `gemini/gemini-2.5-flash-lite` | Gemini API | 500 RPD |
| gemma-4-26b | `gemini/gemma-4-26b-a4b-it` | Gemini API | 1,500 RPD |
| gemma-4-31b | `gemini/gemma-4-31b-it` | Gemini API | 1,500 RPD |
| nemotron-12b-vl | `openrouter/nvidia/nemotron-nano-12b-v2-vl:free` | OpenRouter | 50 RPD |
| nemotron-30b | `openrouter/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free` | OpenRouter | 50 RPD |

## Directory Structure

```
examples/benchmark/
├── __init__.py
├── run.py                  # CLI entry point
├── config.py               # Model definitions, paths, constants
├── tasks/
│   ├── __init__.py
│   ├── synthetic.py        # S1-S6 task generators
│   └── web.py              # W1-W5 HTML fixture generators
├── engine.py               # Trial executor (DVOC + Naive)
├── reporter.py             # Summary tables, JSON export
├── html_fixtures/          # HTML files for web tasks
│   ├── login_form.html
│   ├── nav_bar.html
│   ├── card_grid.html
│   ├── dense_dashboard.html
│   └── dropdown.html
└── output/                 # Results directory (gitignored)
```

## Phasing

### Phase 1: Synthetic benchmark (all models)
Validate core hypothesis across models. ~30 min with Gemini models (faster), longer with OpenRouter.

### Phase 2: Web benchmark (top models)
Run web tasks on the best-performing models. Confirms transfer to real HTML.

### Phase 3: Cross-validation
Full run with all models on all tasks. Generates paper-ready data.

## Open Questions

1. Should we use fixed starting positions or random? Fixed gives cleaner comparisons.
2. Should naive get only 1 attempt or multiple retries? Multiple retries (5) better simulates real use.
3. Should epsilon be fixed at 30px or vary by task? Fixed 30px for consistency; we can also report raw distances.
4. Web tasks need API keys — do we want to run OpenRouter models on web tasks too, or just Gemini models?
5. Should we include non-visual baseline (random click, center click)?
