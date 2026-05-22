from enum import Enum


class GameState(str, Enum):
    IDLE = "idle"
    QUESTIONING = "questioning"
    GUESSING = "guessing"
    BOB_QUESTIONING = "bob_questioning"
    BOB_GUESSING = "bob_guessing"
    BOB_CRYING = "bob_crying"
