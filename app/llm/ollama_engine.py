from dataclasses import dataclass
import json
import re
from typing import Literal

from openai import OpenAI

from app.game.manager import QAItem
from app.i18n import (
    BOB_ACTION_RETRY_SUFFIX,
    BOB_JUDGE_SYSTEM_PROMPT,
    BOB_SYSTEM_PROMPT,
    JUDGE_RETRY_SUFFIX,
    JUDGE_SYSTEM_PROMPT,
    QUESTION_RETRY_SUFFIX,
    QUESTION_SYSTEM_PROMPT,
    QUESTION_SYSTEM_PROMPT_NORMAL,
    QUESTION_SYSTEM_PROMPT_SUPPORTIVE,
)
from app.i18n import UI
from app.llm.config import HOST_DIFFICULTY
from .base_engine import BaseLLMEngine, JudgeResult, BobAction


class OllamaEngine(BaseLLMEngine):
    """
    Ollama LLM Engine
    
    Uses OpenAI-compatible API to communicate with Ollama server
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        api_key: str = "ollama",
        model: str = "qwen2.5:0.5b",
        temperature: float = 0.2,
        max_retries: int = 3,
    ) -> None:
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
    
    @property
    def engine_name(self) -> str:
        return f"Ollama({self.model})"
    
    @staticmethod
    def _parse_three_way_answer(text: str) -> str | None:
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
        context_block = self._build_context_lines(history)
        user_prompt = (
            f"[{UI['prompt_surface']}]\n{surface}\n\n"
            f"[{UI['prompt_history']}]\n{context_block}\n\n"
            f"[{UI['prompt_bottom']}]\n{bottom}\n\n"
            f"[{UI['prompt_question']}]\n{question}\n\n"
            f"{UI['prompt_return']}"
        )

        # Select system prompt based on difficulty
        if HOST_DIFFICULTY == "strict":
            system_prompt = QUESTION_SYSTEM_PROMPT
        elif HOST_DIFFICULTY == "normal":
            system_prompt = QUESTION_SYSTEM_PROMPT_NORMAL.format(
                bottom=bottom,
                history=context_block,
                turn_count=len(history) + 1
            )
        elif HOST_DIFFICULTY == "supportive":
            system_prompt = QUESTION_SYSTEM_PROMPT_SUPPORTIVE.format(
                bottom=bottom,
                history=context_block,
                turn_count=len(history) + 1
            )
        else:
            system_prompt = QUESTION_SYSTEM_PROMPT

        retry_temps = [self.temperature, max(0.0, self.temperature - 0.1), 0.0]
        for i in range(self.max_retries):
            current_system_prompt = system_prompt
            if i > 0:
                current_system_prompt = f"{system_prompt}\n{QUESTION_RETRY_SUFFIX}"

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=retry_temps[min(i, len(retry_temps) - 1)],
                messages=[
                    {"role": "system", "content": current_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = response.choices[0].message.content or ""
            parsed = self._parse_three_way_answer(raw)
            if parsed:
                return parsed

        return "Irrelevant"
    
    def judge_guess(self, *, bottom: str, guess: str) -> JudgeResult:
        return self._judge_guess_with_prompt(
            bottom=bottom,
            guess=guess,
            system_prompt=JUDGE_SYSTEM_PROMPT,
            guess_label="Player Guess",
        )
    
    def judge_bob_guess(self, *, bottom: str, guess: str) -> JudgeResult:
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
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=retry_temps[min(i, len(retry_temps) - 1)],
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = response.choices[0].message.content or ""
            action = self._parse_bob_action(raw)
            if action:
                return action

        return BobAction(
            action="question",
            text="Is the key factor a deliberate human choice rather than an accident or coincidence?",
        )
    
    @staticmethod
    def _extract_json_object(text: str) -> str | None:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        return match.group(0)
    
    def _parse_judge_result(self, raw: str) -> JudgeResult | None:
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
        return JudgeResult(hit=False, score=40, comment="Close, but key causal links are still missing.")
    
    def _judge_guess_with_prompt(
        self,
        *,
        bottom: str,
        guess: str,
        system_prompt: str,
        guess_label: str,
    ) -> JudgeResult:
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
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=retry_temps[min(i, len(retry_temps) - 1)],
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = (response.choices[0].message.content or "").strip()
            parsed = self._parse_judge_result(raw)
            if parsed:
                return parsed
        return self._default_judge_result()
    
    def _parse_bob_action(self, raw: str) -> BobAction | None:
        json_text = self._extract_json_object(raw)
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
