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
    def __init__(self, audio_dir: Path) -> None:
        self.audio_dir = audio_dir
        self.enabled = False
        self.audio_driver = "uninitialized"
        self.using_dummy_driver = False
        self.last_error: str | None = None
        self.sounds: dict[str, pygame.mixer.Sound] = {}
        self.channels: dict[str, pygame.mixer.Channel] = {}
        self.priority_effects = {"click", "success", "fail"}

    def initialize(self) -> None:
        selected_driver = self._initialize_mixer()
        self.enabled = bool(pygame.mixer.get_init())
        if not self.enabled:
            return
        self.audio_driver = selected_driver or "default"
        self.using_dummy_driver = self.audio_driver == "dummy"
        self._load_effects()
        self._setup_channels()
        self._start_background_music()

    def _initialize_mixer(self) -> str | None:
        if pygame.mixer.get_init():
            pygame.mixer.quit()
        previous_driver = os.getenv("SDL_AUDIODRIVER")
        os.environ.setdefault("PULSE_LATENCY_MSEC", "0")
        candidates: list[str | None] = []
        if previous_driver:
            candidates.append(previous_driver)
        if os.getenv("PULSE_SERVER"):
            candidates.append("pulseaudio")
        candidates.append(None)
        candidates.append("dummy")

        selected: str | None = None
        preferred_buffers = (64, 128, 256, 512, 1024)
        with _suppress_stderr_fd():
            for driver in candidates:
                if driver is None:
                    if previous_driver is None:
                        os.environ.pop("SDL_AUDIODRIVER", None)
                    else:
                        os.environ["SDL_AUDIODRIVER"] = previous_driver
                else:
                    os.environ["SDL_AUDIODRIVER"] = driver
                for buffer_size in preferred_buffers:
                    try:
                        pygame.mixer.pre_init(
                            frequency=44100,
                            size=-16,
                            channels=2,
                            buffer=buffer_size,
                        )
                        pygame.mixer.init(
                            frequency=44100,
                            size=-16,
                            channels=2,
                            buffer=buffer_size,
                            allowedchanges=0,
                        )
                        selected = driver
                        break
                    except pygame.error as error:
                        self.last_error = str(error)
                if selected is not None:
                    break
        return selected

    def _setup_channels(self) -> None:
        pygame.mixer.set_num_channels(24)
        channel_map = {
            "click": 0,
            "thinking": 1,
            "message_user": 2,
            "message_agent": 3,
            "message_system": 4,
            "success": 5,
            "fail": 6,
            "startup": 7,
            "message_bob": 8,
        }
        pygame.mixer.set_reserved(len(channel_map))
        self.channels.clear()
        for name, index in channel_map.items():
            if name in self.sounds:
                self.channels[name] = pygame.mixer.Channel(index)

    def _load_effects(self) -> None:
        switch_audio = self.audio_dir / "switch audio"
        self._try_load("click", switch_audio / "click2.ogg")
        self._try_load("thinking", switch_audio / "switch16.ogg")
        self._try_load("message_user", switch_audio / "rollover2.ogg")
        self._try_load("message_agent", switch_audio / "rollover5.ogg")
        self._try_load("message_system", switch_audio / "rollover3.ogg")
        self._try_load("message_bob", switch_audio / "rollover6.ogg")
        self._try_load("success", self.audio_dir / "8-Bit jingles" / "jingles_NES03.ogg")
        self._try_load("fail", self.audio_dir / "Hit jingles" / "jingles_HIT15.ogg")
        self._try_load("startup", self.audio_dir / "Steel jingles" / "jingles_STEEL00.ogg")
        if "message_agent" in self.sounds:
            self.sounds["reply"] = self.sounds["message_agent"]

    def _start_background_music(self) -> None:
        music_path = self.audio_dir / "background.mp3"
        if not music_path.exists():
            return
        try:
            pygame.mixer.music.load(str(music_path))
            pygame.mixer.music.set_volume(0.45)
            pygame.mixer.music.play(-1)
        except pygame.error:
            return

    def _try_load(self, name: str, file_path: Path) -> None:
        if not file_path.exists():
            return
        self.sounds[name] = pygame.mixer.Sound(str(file_path))

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound:
            channel = self.channels.get(name)
            if name in self.priority_effects:
                if channel is not None:
                    channel.stop()
                else:
                    sound.stop()
            if channel is not None:
                channel.play(sound)
            else:
                sound.play()

    def play_message(self, role: str) -> None:
        if role == "user":
            self.play("message_user")
        elif role == "bob":
            self.play("message_bob")
        elif role == "system":
            self.play("message_system")
        else:
            self.play("message_agent")

    def warning_message(self) -> str | None:
        if not self.enabled:
            detail = self.last_error or "unknown mixer error"
            return (
                "Audio could not be initialized.\n"
                f"Reason: {detail}\n\n"
                "If you are on WSL, install Linux audio runtime packages and restart WSL:\n"
                "sudo apt update && sudo apt install -y libpulse0 libasound2"
            )
        if self.using_dummy_driver:
            return (
                "Audio is using SDL dummy driver, so sound output is muted.\n"
                "If you are on WSL, install Linux audio runtime packages and restart WSL:\n"
                "sudo apt update && sudo apt install -y libpulse0 libasound2"
            )
        return None
