from dataclasses import dataclass, field
from typing import Literal

from app.data.story_loader import Story
from app.game.state import GameState


ParsedAnswer = Literal["Yes", "No", "Irrelevant"]


@dataclass(slots=True)
class QAItem:
    question: str
    answer: ParsedAnswer


@dataclass(slots=True)
class GameSession:
    story: Story | None = None
    state: GameState = GameState.IDLE
    history: list[QAItem] = field(default_factory=list)
    context_window: int = 8

    def reset(self) -> None:
        self.story = None
        self.state = GameState.IDLE
        self.history.clear()

    def start_story(self, story: Story) -> None:
        self.story = story
        self.state = GameState.QUESTIONING
        self.history.clear()

    def add_qa(self, question: str, answer: ParsedAnswer) -> None:
        self.history.append(QAItem(question=question, answer=answer))
        if len(self.history) > self.context_window:
            self.history = self.history[-self.context_window :]

    def can_ask(self) -> bool:
        return self.story is not None and self.state == GameState.QUESTIONING

    def to_guessing(self) -> None:
        if self.story is None:
            raise RuntimeError("Cannot enter guessing without a story.")
        self.state = GameState.GUESSING
