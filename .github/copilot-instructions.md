# Copilot instructions for `turtle_soup_game`

## Build, test, and lint commands

### Environment setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the app
**CRITICAL:** This project uses an existing Conda environment named `turtle_soup_env`. **Do NOT create any new virtual environments** (do not use `python -m venv`, `conda create`, etc.) during operations or terminal commands.
```bash
python main.py
```

### Tests
There is currently no automated test suite configured in this repository (`tests/`, `pytest.ini`, and test runner config files are not present), so there is no full-suite or single-test command yet.

### Lint/type-check
There is currently no lint/type-check tool configuration (no `ruff`, `flake8`, `mypy`, `pylint`, or equivalent config files).

## High-level architecture

- `main.py` is the entrypoint and just starts `TurtleSoupApp` from `app/ui/main_window.py`.
- `TurtleSoupApp` is the orchestration layer:
  - Builds all CustomTkinter UI screens (menu + game chat UI).
  - Loads stories (`app/data/story_loader.py`) and audio (`app/audio/sound_manager.py`) during boot on a background thread.
  - Owns session/game lifecycle via `GameSession` (`app/game/manager.py`) and `GameState` enum (`app/game/state.py`).
  - Calls LLM functions via `LLMEngine` (`app/llm/client.py`) from worker threads, then marshals UI updates back with `self.after(...)`.
- `app/llm/client.py` encapsulates model behavior:
  - `ask_question(...)` enforces **Yes / No / Irrelevant** outputs (with retries + stricter follow-up prompt).
  - `judge_guess(...)` requests strict JSON verdict and falls back to a default result when parsing fails.
- `app/data/story_loader.py` loads `stories/*.txt` and parses strict tagged sections: `[Title]`, `[Surface]`, `[Bottom]`.
- `app/audio/sound_manager.py` initializes `pygame.mixer`, attempts multiple audio drivers/buffer sizes, and degrades to dummy/no-audio mode with user-facing warnings surfaced by the UI.
- `app/config.py` centralizes runtime paths and env-configurable model settings (`TS_BASE_URL`, `TS_API_KEY`, `TS_MODEL`, `TS_TEMPERATURE`, `TS_CONTEXT_WINDOW`).

## Key conventions (repo-specific)

- Story files must use the three-tag format exactly (`[Title]`, `[Surface]`, `[Bottom]`); invalid files are skipped silently in loader.
- Both story text and UI text support `\uXXXX` / `\UXXXXXXXX` escape decoding (implemented separately in loader and UI helpers).
- Q&A history is bounded by `context_window` in `GameSession`; older turns are truncated to keep only the latest N turns for model context.
- UI+LLM async pattern:
  - Long-running model calls run in daemon threads.
  - Results are applied through `self.after(...)`.
  - `_story_epoch` guards against stale async callbacks after reset/story changes.
- Game flow relies on explicit state transitions:
  - `IDLE -> QUESTIONING` when a story starts.
  - `QUESTIONING -> GUESSING` during final guess submission.
  - Returns to `IDLE` after judgment.
- LLM answer normalization is intentionally tolerant of multilingual/noisy outputs, but only canonicalizes to `Yes`, `No`, or `Irrelevant`.
- Audio is event-name driven (`click`, `thinking`, `message_user`, `message_agent`, `success`, `fail`, `startup`) and wired in one place (`SoundManager._load_effects` + `_setup_channels`).
- The startup overlay sequence and credit text are first-class UI behavior; keep this flow intact when modifying boot logic.

## Runtime environment details worth preserving

- Default model endpoint is local OpenAI-compatible API: `http://127.0.0.1:11434/v1`.
- Font scale is controlled by `TS_FONT_SCALE` (UI computes font sizes from it).
- On limited Linux/WSL environments, the app shows in-chat warnings for missing scalable fonts or unavailable audio runtime.
