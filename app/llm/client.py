from dataclasses import dataclass
import json
import re

from openai import OpenAI

from app.game.manager import QAItem

QUESTION_SYSTEM_PROMPT = """You are a Turtle Soup game host.
You must choose exactly one final answer with no explanation:
1) Yes
2) No
3) Irrelevant
"""

QUESTION_RETRY_SUFFIX = """Strictly follow this: output only one of "Yes" / "No" / "Irrelevant", with no punctuation or extra text."""

JUDGE_SYSTEM_PROMPT = """You are a Turtle Soup judge. Compare the canonical answer and player's final guess.
Output must be valid JSON in this format:
{"hit": true/false, "score": 0-100, "comment": "short English feedback"}
"""


@dataclass(slots=True)
class JudgeResult:
    hit: bool
    score: int
    comment: str


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
            f"[Surface]\n{surface}\n\n"
            f"[History]\n{context_block}\n\n"
            f"[Ground Truth (do not reveal)]\n{bottom}\n\n"
            f"[Player Question]\n{question}\n\n"
            "Return only: Yes / No / Irrelevant."
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
        user_prompt = (
            f"[Ground Truth]\n{bottom}\n\n"
            f"[Player Guess]\n{guess}\n\n"
            "Output JSON only."
        )

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        raw = (response.choices[0].message.content or "").strip()
        json_text = self._extract_json_object(raw)
        if not json_text:
            return JudgeResult(hit=False, score=40, comment="Close, but key causal links are still missing.")

        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError:
            return JudgeResult(hit=False, score=40, comment="Close, but key causal links are still missing.")
        hit = bool(payload.get("hit", False))
        score = int(payload.get("score", 0))
        score = max(0, min(100, score))
        comment = str(payload.get("comment", ""))
        if not comment:
            comment = "Judgment completed."
        return JudgeResult(hit=hit, score=score, comment=comment)

    @staticmethod
    def _extract_json_object(text: str) -> str | None:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None
        return match.group(0)
    
