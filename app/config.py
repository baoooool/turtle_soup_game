import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
STORIES_DIR = PROJECT_ROOT / "stories"
AUDIO_RES_DIR = PROJECT_ROOT / "audio_res"
SFX_DIR = AUDIO_RES_DIR
USER_DATA_PATH = PROJECT_ROOT / "user_profiles.json"

# Language: "zh" for Chinese, "en" for English
LANGUAGE = os.getenv("TS_LANGUAGE", "zh").lower()

MODEL_BASE_URL = os.getenv("TS_BASE_URL", "http://127.0.0.1:11434/v1")
MODEL_API_KEY = os.getenv("TS_API_KEY", "local-key")
MODEL_NAME = os.getenv("TS_MODEL", "qwen2.5:7b-instruct")
MODEL_TEMPERATURE = float(os.getenv("TS_TEMPERATURE", "0.2"))
CONTEXT_WINDOW = int(os.getenv("TS_CONTEXT_WINDOW", "8"))
BOB_ENABLED = os.getenv("TS_BOB_ENABLED", "true").lower() == "true"

# Bob personality attributes (1-10 scale)
BOB_QUESTION_STRATEGY = int(os.getenv("TS_BOB_QUESTION_STRATEGY", "5"))  # 1=谨慎, 10=跳越
BOB_ANSWER_STRATEGY = int(os.getenv("TS_BOB_ANSWER_STRATEGY", "5"))  # 1=保守, 10=激进
BOB_TRAIT = os.getenv("TS_BOB_TRAIT", "normal")  # villain / normal / genius
