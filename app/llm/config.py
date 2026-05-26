"""
Configuration for LLM engines

Modify this file to switch between different LLM backends
"""

from typing import Literal, Any

# Engine type: "ollama", "local", or "mock"
LLM_ENGINE_TYPE: Literal["ollama", "local", "mock"] = "ollama"

# Host difficulty mode: "strict", "normal", or "supportive"
# - strict: Only answers Yes/No/Irrelevant (default)
# - normal: Gives hints after 3 consecutive irrelevant questions or every 10 rounds
# - supportive: Indicates importance of answers and gives more guidance
HOST_DIFFICULTY: Literal["strict", "normal", "supportive"] = "normal"

# Ollama configuration (used when LLM_ENGINE_TYPE = "ollama")
OLLAMA_CONFIG: dict[str, Any] = {
    "base_url": "http://localhost:11434",
    "api_key": "ollama",
    "model": "qwen2.5:0.5b",
    "temperature": 0.2,
    "max_retries": 3,
}

# Local engine configuration (used when LLM_ENGINE_TYPE = "local")
LOCAL_CONFIG: dict[str, Any] = {
    "model_name": "Qwen/Qwen2.5-0.5B-Instruct",  # Hugging Face model name or local path
    "device": "cpu",  # "cpu", "cuda", or "mps"
    "temperature": 0.2,
    "max_retries": 3,
    "load_in_4bit": False,  # Use 4-bit quantization (requires CUDA)
}

# Recommended models for local engine
RECOMMENDED_MODELS = {
    "tiny": "Qwen/Qwen2.5-0.5B-Instruct",      # 0.5B, ~1GB VRAM, fast but less accurate
    "small": "Qwen/Qwen2.5-1.5B-Instruct",     # 1.5B, ~3GB VRAM, good balance
    "medium": "Qwen/Qwen2.5-3B-Instruct",      # 3B, ~6GB VRAM, better quality
    "large": "Qwen/Qwen2.5-7B-Instruct",       # 7B, ~14GB VRAM, best quality
    "cpu_friendly": "Qwen/Qwen2.5-0.5B-Instruct",  # Best for CPU-only
}

# How to get started:
# 1. Ollama: 
#    - Install: https://ollama.ai
#    - Pull model: ollama pull qwen2.5:0.5b
#    - Run: ollama serve
#
# 2. Local (Hugging Face):
#    - Install: pip install transformers torch accelerate
#    - For GPU: pip install bitsandbytes
#    - Models will be downloaded automatically on first run
#
# 3. Mock (testing):
#    - No setup required
#    - Returns random responses for testing
