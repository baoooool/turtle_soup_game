import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STORIES_DIR = PROJECT_ROOT / "stories"
AUDIO_RES_DIR = PROJECT_ROOT / "audio_res"
SFX_DIR = AUDIO_RES_DIR

MODEL_BASE_URL = os.getenv("TS_BASE_URL", "http://127.0.0.1:11434/v1")
MODEL_API_KEY = os.getenv("TS_API_KEY", "local-key")
MODEL_NAME = os.getenv("TS_MODEL", "qwen2.5:7b-instruct")
MODEL_TEMPERATURE = float(os.getenv("TS_TEMPERATURE", "0.2"))
CONTEXT_WINDOW = int(os.getenv("TS_CONTEXT_WINDOW", "8"))
