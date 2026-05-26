from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class JudgeResult:
    hit: bool
    score: int
    comment: str


@dataclass(slots=True)
class BobAction:
    action: Literal["question", "guess"]
    text: str
    reasoning: str = ""


class BaseLLMEngine(ABC):
    """Abstract base class for LLM engines"""
    
    @abstractmethod
    def ask_question(
        self,
        *,
        surface: str,
        bottom: str,
        question: str,
        history: list,
    ) -> str:
        """Ask a yes/no/irrelevant question"""
        pass
    
    @abstractmethod
    def judge_guess(self, *, bottom: str, guess: str) -> JudgeResult:
        """Judge player's guess"""
        pass
    
    @abstractmethod
    def judge_bob_guess(self, *, bottom: str, guess: str) -> JudgeResult:
        """Judge Bob's guess"""
        pass
    
    @abstractmethod
    def generate_bob_action(
        self,
        *,
        surface: str,
        bottom: str | None = None,
        history: list,
        turn_count: int = 0,
        question_strategy: int = 5,
        answer_strategy: int = 5,
        trait: str = "normal",
    ) -> BobAction:
        """Generate Bob's next action (question or guess)"""
        pass
    
    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Return the name of this engine"""
        pass
