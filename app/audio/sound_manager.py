import os
from contextlib import contextmanager
from pathlib import Path

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame


@contextmanager
def _suppress_stderr_fd() -> None:
    stderr_fd = 2
    null_fd = os.open(os.devnull, os.O_WRONLY)
    saved_fd = os.dup(stderr_fd)
    try:
        os.dup2(null_fd, stderr_fd)
        yield
    finally:
        os.dup2(saved_fd, stderr_fd)
        os.close(saved_fd)
        os.close(null_fd)


class SoundManager:
    def __init__(self, sfx_dir: Path) -> None:
        self.sfx_dir = sfx_dir
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}

    def initialize(self) -> None:
        with _suppress_stderr_fd():
            try:
                pygame.mixer.init()
            except pygame.error:
                previous_driver = os.getenv("SDL_AUDIODRIVER")
                if previous_driver != "dummy":
                    os.environ["SDL_AUDIODRIVER"] = "dummy"
                try:
                    pygame.mixer.init()
                except pygame.error:
                    if previous_driver is None:
                        os.environ.pop("SDL_AUDIODRIVER", None)
                    elif previous_driver != "dummy":
                        os.environ["SDL_AUDIODRIVER"] = previous_driver
                    return

        self.enabled = bool(pygame.mixer.get_init())
        if not self.enabled:
            return
        self._try_load("click", "click.wav")
        self._try_load("reply", "reply.wav")
        self._try_load("success", "success.wav")
        self._try_load("fail", "fail.wav")
        self._try_load("thinking", "thinking.wav")

    def _try_load(self, name: str, file_name: str) -> None:
        file_path = self.sfx_dir / file_name
        if not file_path.exists():
            return
        self.sounds[name] = pygame.mixer.Sound(str(file_path))

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            sound.play()
