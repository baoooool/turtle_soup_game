from dataclasses import dataclass, field
from typing import Literal

from app.data.story_loader import Story
from app.data.user_manager import UserManager
from app.game.state import GameState
from app.game.recorder import recorder as game_recorder


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
    bob_crying: bool = False
    player_name: str | None = None
    total_rounds: int = 0

    def reset(self) -> None:
        self.story = None
        self.state = GameState.IDLE
        self.history.clear()
        self.total_rounds = 0
        self.bob_crying = False

    def start_story(self, story: Story) -> None:
        self.story = story
        self.state = GameState.QUESTIONING
        self.history.clear()
        self.total_rounds = 0
        self.bob_crying = False
        
        # 开始游戏记录
        from app.llm.config import HOST_DIFFICULTY
        game_recorder.start_game(
            story_title=story.title,
            story_surface=story.surface,
            story_bottom=story.bottom,
            player_name=self.player_name or "Player",
            host_difficulty=HOST_DIFFICULTY
        )

    def add_qa(self, question: str, answer: ParsedAnswer) -> None:
        self.history.append(QAItem(question=question, answer=answer))
        self.total_rounds += 1
        if len(self.history) > self.context_window:
            self.history = self.history[-self.context_window :]
        
        # 记录问答
        turn_number = len(self.history)
        game_recorder.record_question(
            question=question,
            answer=answer,
            turn_number=turn_number,
            player_type="player"
        )

    def can_ask(self) -> bool:
        return self.story is not None and self.state in {GameState.QUESTIONING, GameState.BOB_CRYING}

    def bob_can_act(self) -> bool:
        return self.story is not None and not self.bob_crying

    def to_bob_questioning(self) -> None:
        if self.story is None:
            raise RuntimeError("Cannot enter Bob's turn without a story.")
        if self.bob_crying:
            return
        self.state = GameState.BOB_QUESTIONING

    def add_bob_qa(self, question: str, answer: ParsedAnswer) -> None:
        """记录 BOB 的问答"""
        self.history.append(QAItem(question=question, answer=answer))
        self.total_rounds += 1
        if len(self.history) > self.context_window:
            self.history = self.history[-self.context_window :]
        
        # 记录 BOB 的问答
        turn_number = len(self.history)
        game_recorder.record_question(
            question=question,
            answer=answer,
            turn_number=turn_number,
            player_type="bob"
        )

    def to_bob_guessing(self) -> None:
        if self.story is None:
            raise RuntimeError("Cannot enter Bob's guess without a story.")
        if self.bob_crying:
            return
        self.state = GameState.BOB_GUESSING

    def to_guessing(self) -> None:
        if self.story is None:
            raise RuntimeError("Cannot enter guessing without a story.")
        self.state = GameState.GUESSING

    def to_player_questioning(self) -> None:
        if self.story is None:
            raise RuntimeError("Cannot resume questioning without a story.")
        self.state = GameState.BOB_CRYING if self.bob_crying else GameState.QUESTIONING

    def mark_bob_crying(self) -> None:
        if self.story is None:
            raise RuntimeError("Cannot update Bob's mood without a story.")
        self.bob_crying = True
        self.state = GameState.BOB_CRYING

    def set_player(self, name: str | None) -> None:
        self.player_name = name

    def apply_final_score(self, user_manager: UserManager, score: int) -> tuple[int, int, int, float]:
        if not self.player_name:
            raise RuntimeError("No active player selected for scoring.")
        rounds = self.total_rounds
        # Apply round coefficient: 1.0 for <=10 rounds, linearly decreases to 0.8 at 30 rounds
        if rounds <= 10:
            coefficient = 1.0
        elif rounds >= 30:
            coefficient = 0.8
        else:
            coefficient = 1.0 - (rounds - 10) * 0.01  # Linear decrease from 1.0 to 0.8
        adjusted_score = int(score * coefficient)
        user_manager.set_score(self.player_name, adjusted_score)
        return adjusted_score, score, rounds, coefficient
