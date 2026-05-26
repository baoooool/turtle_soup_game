from typing import Literal, Union
from .base_engine import BaseLLMEngine


EngineType = Literal["ollama", "local", "mock"]


def create_llm_engine(
    engine_type: EngineType = "ollama",
    **kwargs,
) -> BaseLLMEngine:
    """
    Factory function to create LLM engines
    
    Args:
        engine_type: Type of engine ("ollama", "local", "mock")
        **kwargs: Engine-specific arguments
    
    Returns:
        Configured LLM engine instance
    
    Examples:
        # Ollama engine
        engine = create_llm_engine("ollama", base_url="http://localhost:11434", model="qwen2.5:0.5b")
        
        # Local engine
        engine = create_llm_engine("local", model_name="Qwen/Qwen2.5-0.5B-Instruct", device="cuda")
        
        # Mock engine (for testing)
        engine = create_llm_engine("mock")
    """
    if engine_type == "ollama":
        from .ollama_engine import OllamaEngine
        return OllamaEngine(
            base_url=kwargs.get("base_url", "http://localhost:11434"),
            api_key=kwargs.get("api_key", "ollama"),
            model=kwargs.get("model", "qwen2.5:0.5b"),
            temperature=kwargs.get("temperature", 0.2),
            max_retries=kwargs.get("max_retries", 3),
        )
    
    elif engine_type == "local":
        from .local_engine import LocalLLMEngine
        return LocalLLMEngine(
            model_name=kwargs.get("model_name", "Qwen/Qwen2.5-0.5B-Instruct"),
            device=kwargs.get("device", "cpu"),
            temperature=kwargs.get("temperature", 0.2),
            max_retries=kwargs.get("max_retries", 3),
            load_in_4bit=kwargs.get("load_in_4bit", False),
        )
    
    elif engine_type == "mock":
        from .mock_engine import MockEngine
        return MockEngine()
    
    else:
        raise ValueError(f"Unknown engine type: {engine_type}. Valid types: {EngineType.__args__}")
