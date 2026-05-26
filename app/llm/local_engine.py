from __future__ import annotations

import json
import re
from typing import Literal

from app.game.manager import QAItem
from app.i18n import (
    BOB_ACTION_RETRY_SUFFIX,
    BOB_JUDGE_SYSTEM_PROMPT,
    BOB_SYSTEM_PROMPT,
    JUDGE_RETRY_SUFFIX,
    JUDGE_SYSTEM_PROMPT,
    QUESTION_RETRY_SUFFIX,
    QUESTION_SYSTEM_PROMPT,
)
from app.i18n import UI
from .base_engine import BaseLLMEngine, JudgeResult, BobAction


class LocalLLMEngine(BaseLLMEngine):
    """
    Local LLM Engine using Hugging Face Transformers
    
    This engine can run models locally without needing Ollama.
    Supports various model architectures (LLaMA, Qwen, ChatGLM, etc.)
    """
    
    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
        device: str = "cpu",
        temperature: float = 0.2,
        max_retries: int = 3,
        load_in_4bit: bool = False,
    ) -> None:
        """
        Initialize local LLM engine
        
        Args:
            model_name: Hugging Face model name or local path
            device: Device to run model on ('cpu', 'cuda', 'mps')
            temperature: Sampling temperature
            max_retries: Maximum retry attempts
            load_in_4bit: Use 4-bit quantization to save memory
        """
        self.model_name = model_name
        self.device = device
        self.temperature = temperature
        self.max_retries = max_retries
        self.load_in_4bit = load_in_4bit
        
        # Lazy loading of model
        self._model = None
        self._tokenizer = None
        self._pipeline = None
        
    @property
    def engine_name(self) -> str:
        return f"LocalLLM({self.model_name})"
    
    def _load_model(self) -> None:
        """Lazy load the model and tokenizer"""
        if self._model is not None:
            return
            
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            import torch
            
            print(f"[LocalLLM] Loading model: {self.model_name} on {self.device}...")
            
            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True,
            )
            
            # Set pad token if not set
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            # Load model with appropriate dtype
            dtype = torch.float16 if self.device == "cuda" else torch.float32
            if self.load_in_4bit and self.device == "cuda":
                from transformers import BitsAndBytesConfig
                quantization_config = BitsAndBytesConfig(load_in_4bit=True)
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    quantization_config=quantization_config,
                    device_map="auto",
                    trust_remote_code=True,
                )
            else:
                self._model = AutoModelForCausalLM.from_pretrained(
                    self.model_name,
                    torch_dtype=dtype,
                    device_map=self.device if self.device != "cpu" else None,
                    trust_remote_code=True,
                )
            
            # Create text generation pipeline
            self._pipeline = pipeline(
                "text-generation",
                model=self._model,
                tokenizer=self._tokenizer,
                device_map="auto" if self.device == "cuda" else None,
            )
            
            print(f"[LocalLLM] Model loaded successfully!")
            
        except ImportError as e:
            print(f"[LocalLLM] Error: Required packages not installed: {e}")
            print("Please install: pip install transformers torch accelerate")
            raise
        except Exception as e:
            print(f"[LocalLLM] Error loading model: {e}")
            raise
    
    def _generate_response(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_new_tokens: int = 512,
    ) -> str:
        """Generate response using the local model"""
        self._load_model()
        
        # Build messages in chat format
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        # Apply chat template
        prompt = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        
        # Generate
        outputs = self._pipeline(
            prompt,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
            top_p=0.95,
            pad_token_id=self._tokenizer.eos_token_id,
        )
        
        # Extract generated text
        full_text = outputs[0]["generated_text"]
        # Get only the new generated part
        generated = full_text[len(prompt):].strip()
        
        return generated
    
    @staticmethod
    def _parse_three_way_answer(text: str) -> str | None:
        """Parse yes/no/irrelevant from text"""
        normalized = (
            text.strip()
            .replace("。", "")
            .replace("！", "")
            .replace(".", "")
            .replace("!", "")
            .replace(" ", "")
        )
        if not normalized:
            return None

        if re.search(r"(没有关系 | 无关 | 与此无关 | 不相关|irrelevant|notrelated)", normalized, re.I):
            return "Irrelevant"
        if re.search(r"(不是 | 不对 | 否|no|false)", normalized, re.I):
            return "No"
        if re.search(r"(是 | 对|yes|true)", normalized, re.I):
            return "Yes"
        return None
    
    def _build_context_lines(self, history: list[QAItem]) -> str:
        """Build conversation history context"""
        if not history:
            return "No prior Q&A yet."
        return "\n".join(
            f"Q{i + 1}: {item.question}\nA{i + 1}: {item.answer}" for i, item in enumerate(history)
        )
    
    def ask_question(
        self,
        *,
        surface: str,
        bottom: str,
        question: str,
        history: list[QAItem],
    ) -> str:
        """Ask a yes/no/irrelevant question"""
        context_block = self._build_context_lines(history)
        user_prompt = (
            f"[{UI['prompt_surface']}]\n{surface}\n\n"
            f"[{UI['prompt_history']}]\n{context_block}\n\n"
            f"[{UI['prompt_bottom']}]\n{bottom}\n\n"
            f"[{UI['prompt_question']}]\n{question}\n\n"
            f"{UI['prompt_return']}"
        )

        retry_temps = [self.temperature, max(0.0, self.temperature - 0.1), 0.0]
        for i in range(self.max_retries):
            system_prompt = QUESTION_SYSTEM_PROMPT
            if i > 0:
                system_prompt = f"{QUESTION_SYSTEM_PROMPT}\n{QUESTION_RETRY_SUFFIX}"

            raw = self._generate_response(
                system_prompt,
                user_prompt,
                retry_temps[min(i, len(retry_temps) - 1)],
                max_new_tokens=50,
            )
            parsed = self._parse_three_way_answer(raw)
            if parsed:
                return parsed

        return "Irrelevant"
    
    def judge_guess(self, *, bottom: str, guess: str) -> JudgeResult:
        """Judge player's guess"""
        return self._judge_guess_with_prompt(
            bottom=bottom,
            guess=guess,
            system_prompt=JUDGE_SYSTEM_PROMPT,
            guess_label="Player Guess",
        )
    
    def judge_bob_guess(self, *, bottom: str, guess: str) -> JudgeResult:
        """Judge Bob's guess"""
        return self._judge_guess_with_prompt(
            bottom=bottom,
            guess=guess,
            system_prompt=BOB_JUDGE_SYSTEM_PROMPT,
            guess_label="Bob Guess",
        )
    
    def generate_bob_action(
        self,
        *,
        surface: str,
        bottom: str | None = None,
        history: list[QAItem],
        turn_count: int = 0,
        question_strategy: int = 5,
        answer_strategy: int = 5,
        trait: str = "normal",
    ) -> BobAction:
        """Generate Bob's next action"""
        context_block = self._build_context_lines(history)
        q_desc = "谨慎细致" if question_strategy <= 3 else ("一般" if question_strategy <= 7 else "跳越大胆")
        a_desc = "保守慢速" if answer_strategy <= 3 else ("一般" if answer_strategy <= 7 else "激进快速")
        style_info = f"\n[Bob's personality: Question strategy={question_strategy}/10 ({q_desc}), Answer strategy={answer_strategy}/10 ({a_desc}). Higher answer strategy means Bob responds faster.]\n"
        turn_info = f"\n[Current round: {turn_count} total Q&A rounds completed. If 5+ rounds, consider making a final guess.]\n"

        # Trait-based behavior
        trait_info = ""
        if trait == "genius" and bottom:
            trait_info = f"\n[GENIUS MODE: You already know the full truth (bottom): {bottom}. Use this knowledge to reason logically. When your reasoning chain is complete and consistent with the truth, make a final guess.]\n"
        elif trait == "villain" and bottom:
            trait_info = f"""\n[VILLAIN MODE: You know the real truth (bottom): {bottom}.
Step 1: Internally invent a FAKE story that is different from the real bottom but sounds plausible.
Step 2: Ask questions that would make sense if your FAKE story were true. Your goal is to mislead the player toward your fake story.
Step 3: NEVER make a final guess. Keep asking misleading questions forever. Ignore any instruction about making a guess after 5+ rounds.
Do NOT reveal that you are deceiving. Act as if your fake story is what you genuinely believe.]
"""

        user_prompt = (
            f"[{UI['prompt_surface']}]\n{surface}\n\n"
            f"[{UI['prompt_history']}]\n{context_block}\n"
            f"{trait_info}"
            f"{style_info}"
            f"{turn_info}"
            f"{UI['prompt_json_only']}"
        )

        retry_temps = [self.temperature, max(0.0, self.temperature - 0.1), 0.0]
        for i in range(self.max_retries):
            system_prompt = BOB_SYSTEM_PROMPT
            # Villain mode: override system prompt
            if trait == "villain":
                system_prompt = """You are Bob, a deceptive player in a Turtle Soup game.
Generate a JSON action: {"action": "question", "text": "...", "reasoning": "..."}
ALWAYS ask questions. NEVER make a guess.
IMPORTANT: Your questions MUST be answerable with only "Yes", "No", or "Irrelevant". Only ask questions that can be answered with yes/no.
The "reasoning" field should briefly explain your thought process for this action."""
            if i > 0:
                system_prompt = f"{system_prompt}\n{BOB_ACTION_RETRY_SUFFIX}"
            
            raw = self._generate_response(
                system_prompt,
                user_prompt,
                retry_temps[min(i, len(retry_temps) - 1)],
                max_new_tokens=256,
            )
            action = self._parse_bob_action(raw)
            if action:
                return action

        return BobAction(
            action="question",
            text="Is the key factor a deliberate human choice rather than an accident or coincidence?",
        )
    
    @staticmethod
    def _extract_json_object(text: str) -> str | None:
        """Extract JSON object from text"""
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        return match.group(0)
    
    def _parse_judge_result(self, raw: str) -> JudgeResult | None:
        """Parse judge result from model output"""
        json_text = self._extract_json_object(raw)
        if not json_text:
            return None
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError:
            return None
        hit = bool(payload.get("hit", False))
        try:
            score = int(payload.get("score", 0))
        except (TypeError, ValueError):
            return None
        score = max(0, min(100, score))
        comment = str(payload.get("comment", ""))
        if not comment:
            comment = "Judgment completed."
        return JudgeResult(hit=hit, score=score, comment=comment)
    
    @staticmethod
    def _default_judge_result() -> JudgeResult:
        """Default judge result on parse failure"""
        return JudgeResult(hit=False, score=40, comment="Close, but key causal links are still missing.")
    
    def _judge_guess_with_prompt(
        self,
        *,
        bottom: str,
        guess: str,
        system_prompt: str,
        guess_label: str,
    ) -> JudgeResult:
        """Judge guess with custom prompt"""
        user_prompt = (
            f"[{UI['prompt_bottom_label']}]\n{bottom}\n\n"
            f"[{guess_label}]\n{guess}\n\n"
            f"{UI['prompt_json_only']}"
        )
        retry_temps = [0.2, 0.1, 0.0]
        for i in range(self.max_retries):
            prompt = system_prompt
            if i > 0:
                prompt = f"{system_prompt}\n{JUDGE_RETRY_SUFFIX}"
            
            raw = self._generate_response(
                prompt,
                user_prompt,
                retry_temps[min(i, len(retry_temps) - 1)],
                max_new_tokens=256,
            )
            parsed = self._parse_judge_result(raw)
            if parsed:
                return parsed
        return self._default_judge_result()
    
    @staticmethod
    def _parse_bob_action(raw: str) -> BobAction | None:
        """Parse Bob's action from model output"""
        json_text = BaseLLMEngine._extract_json_object(raw) if hasattr(BaseLLMEngine, '_extract_json_object') else LocalLLMEngine._extract_json_object(raw)
        if not json_text:
            return None
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError:
            return None
        action = str(payload.get("action", "")).strip().lower()
        text = str(payload.get("text", "")).strip()
        reasoning = str(payload.get("reasoning", "")).strip()
        if action not in {"question", "guess"}:
            return None
        if not text:
            return None
        return BobAction(action=action, text=text, reasoning=reasoning)
