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
)
from app.i18n import UI


@dataclass(slots=True)
class JudgeResult:
    hit: bool
    score: int
    comment: str


@dataclass(slots=True)
class BobAction:
    action: Literal["question", "guess"]
    text: str


class LLMEngine:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.2,
        max_retries: int = 3,
    ) -> None:
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries

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

        if re.search(r"(没有关系|无关|与此无关|不相关|irrelevant|notrelated)", normalized, re.I):
            return "Irrelevant"
        if re.search(r"(不是|不对|否|no|false)", normalized, re.I):
            return "No"
        if re.search(r"(是|对|yes|true)", normalized, re.I):
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

        retry_temps = [self.temperature, max(0.0, self.temperature - 0.1), 0.0]
        for i in range(self.max_retries):
            system_prompt = QUESTION_SYSTEM_PROMPT
            if i > 0:
                system_prompt = f"{QUESTION_SYSTEM_PROMPT}\n{QUESTION_RETRY_SUFFIX}"

            response = self.client.chat.completions.create(
                model=self.model,
                temperature=retry_temps[min(i, len(retry_temps) - 1)],
                messages=[
                    {"role": "system", "content": system_prompt},
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

    def generate_bob_action(self, *, surface: str, history: list[QAItem]) -> BobAction:
        context_block = self._build_context_lines(history)
        user_prompt = (
            f"[{UI['prompt_surface']}]\n{surface}\n\n"
            f"[{UI['prompt_history']}]\n{context_block}\n\n"
            f"{UI['prompt_json_only']}"
        )

        retry_temps = [self.temperature, max(0.0, self.temperature - 0.1), 0.0]
        for i in range(self.max_retries):
            system_prompt = BOB_SYSTEM_PROMPT
            if i > 0:
                system_prompt = f"{BOB_SYSTEM_PROMPT}\n{BOB_ACTION_RETRY_SUFFIX}"
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
        if action not in {"question", "guess"}:
            return None
        if not text:
            return None
        return BobAction(action=action, text=text)
    
