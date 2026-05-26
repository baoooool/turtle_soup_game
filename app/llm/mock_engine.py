import random
from .base_engine import BaseLLMEngine, JudgeResult, BobAction
from app.game.manager import QAItem


class MockEngine(BaseLLMEngine):
    """
    Mock LLM Engine for testing
    
    Returns predefined responses for testing purposes
    """
    
    def __init__(self) -> None:
        self.call_count = 0
    
    @property
    def engine_name(self) -> str:
        return "MockEngine"
    
    def ask_question(
        self,
        *,
        surface: str,
        bottom: str,
        question: str,
        history: list[QAItem],
    ) -> str:
        """Return random yes/no/irrelevant for testing"""
        self.call_count += 1
        responses = ["Yes", "No", "Irrelevant"]
        return random.choice(responses)
    
    def judge_guess(self, *, bottom: str, guess: str) -> JudgeResult:
        """Return mock judge result"""
        self.call_count += 1
        similarity = len(set(bottom.lower()) & set(guess.lower())) / max(len(bottom), len(guess))
        hit = similarity > 0.7
        score = int(similarity * 100)
        return JudgeResult(
            hit=hit,
            score=score,
            comment="Mock judgment - this is a test response."
        )
    
    def judge_bob_guess(self, *, bottom: str, guess: str) -> JudgeResult:
        """Same as judge_guess for mock"""
        return self.judge_guess(bottom=bottom, guess=guess)
    
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
        """Return mock Bob action"""
        self.call_count += 1
        
        questions = [
            "Is the story related to a person's death?",
            "Did someone make a deliberate choice?",
            "Is there an element of surprise or misunderstanding?",
            "Does the story involve family relationships?",
        ]
        
        return BobAction(
            action="question" if turn_count < 5 else "guess",
            text=random.choice(questions),
            reasoning=f"Mock reasoning for turn {turn_count}. Testing mode."
        )
