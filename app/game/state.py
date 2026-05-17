from enum import Enum


class GameState(str, Enum):
    IDLE = "idle"
    QUESTIONING = "questioning"
    GUESSING = "guessing"
