from __future__ import annotations

import os
import re
import threading
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
from openai import OpenAIError
from PIL import Image

from app.audio.sound_manager import SoundManager
from app.config import (
    CONTEXT_WINDOW,
    MODEL_API_KEY,
    MODEL_BASE_URL,
    MODEL_NAME,
    MODEL_TEMPERATURE,
    PROJECT_ROOT,
    SFX_DIR,
    STORIES_DIR,
)
from app.data.story_loader import Story, load_stories
from app.game.manager import GameSession
from app.game.state import GameState
from app.llm.client import BobAction, JudgeResult, LLMEngine

UNICODE_ESCAPE_PATTERN = re.compile(r"\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}")
FONT_SCALE = float(os.getenv("TS_FONT_SCALE", "1.0"))
BASE_FONT_SIZE = max(24, int(42 * FONT_SCALE))
STATUS_FONT_SIZE = max(20, int(34 * FONT_SCALE))
TITLE_FONT_SIZE = max(32, int(58 * FONT_SCALE))
UI_SCALE = 1.0
WINDOW_WIDTH = 1440
WINDOW_HEIGHT = 900
MIN_WINDOW_WIDTH = 1180
MIN_WINDOW_HEIGHT = 720
STARTUP_CARD_RELWIDTH = 0.9
STARTUP_SUBTITLE_WRAP = 1240
FINAL_GUESS_SUCCESS_SCORE = 60
PIXEL_ASSET_ROOT = PROJECT_ROOT / "PixelPete'sArtAssets" / "PixelPete'sArtAssets"
PIXEL_UI_DIR = PIXEL_ASSET_ROOT / "Sprites" / "UI"
PIXEL_SPRITES_DIR = PIXEL_ASSET_ROOT / "Sprites"
PIXEL_GB_DIR = PIXEL_ASSET_ROOT / "GameBoy"


def _ui_text(text: str) -> str:
    if "\\" not in text:
        return text

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        return chr(int(token[2:], 16))

    return UNICODE_ESCAPE_PATTERN.sub(replace, text)


class TurtleSoupApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        ctk.set_widget_scaling(UI_SCALE)
        ctk.set_window_scaling(UI_SCALE)

        self.title(_ui_text("Turtle Soup · Story Night"))
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        self.configure(fg_color="#151022")

        self.session = GameSession(context_window=CONTEXT_WINDOW)
        self.llm = LLMEngine(
            base_url=MODEL_BASE_URL,
            api_key=MODEL_API_KEY,
            model=MODEL_NAME,
            temperature=MODEL_TEMPERATURE,
            max_retries=3,
        )
        self.sounds = SoundManager(SFX_DIR)
        self.stories: list[Story] = []
        self.selected_story_index: int | None = None
        self.is_thinking = False
        self._thinking_step = 0
        self._story_epoch = 0
        self._menu_layer = 1
        self._chat_row = 0
        self._startup_active = False
        self._startup_step = 0
        self._startup_overlay: ctk.CTkFrame | None = None
        self._startup_icon_label: ctk.CTkLabel | None = None
        self._startup_status_label: ctk.CTkLabel | None = None
        self._audio_env_warning_shown = False
        available_families = {name.lower() for name in tkfont.families(self)}
        family = "helvetica" if "helvetica" in available_families else "fixed"
        self.base_font = ctk.CTkFont(family=family, size=BASE_FONT_SIZE)
        self.status_font = ctk.CTkFont(family=family, size=STATUS_FONT_SIZE)
        self.title_font = ctk.CTkFont(family=family, size=TITLE_FONT_SIZE, weight="bold")
        self._font_env_warning_shown = False
        self.pixel_images: dict[str, ctk.CTkImage] = {}
        self._load_pixel_assets()

        self._build_layout()
        self._load_boot_sequence()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_panel = ctk.CTkFrame(self, corner_radius=0, fg_color="#1b1530")
        self.main_panel.grid(row=0, column=0, sticky="nsew")
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(1, weight=1)
        if self.pixel_images.get("bg"):
            self.background_art = ctk.CTkLabel(self.main_panel, text="", image=self.pixel_images["bg"])
            self.background_art.place(relx=0.5, rely=0.5, anchor="center")
            self.background_art.lower()

        self.status_label = ctk.CTkLabel(
            self.main_panel,
            text=_ui_text("Getting things ready..."),
            font=self.status_font,
            text_color="#c7d2fe",
            image=self.pixel_images.get("system_avatar"),
            compound="left",
        )
        self.status_label.grid(row=0, column=0, padx=24, pady=(20, 8), sticky="w")

        self.screen_stack = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.screen_stack.grid(row=1, column=0, padx=20, pady=8, sticky="nsew")
        self.screen_stack.grid_columnconfigure(0, weight=1)
        self.screen_stack.grid_rowconfigure(0, weight=1)

        self.menu_screen = ctk.CTkFrame(self.screen_stack, fg_color="#231a3a", border_width=2, border_color="#5b4b8a")
        self.menu_screen.grid(row=0, column=0, sticky="nsew")
        self.menu_screen.grid_columnconfigure(0, weight=1)
        self.menu_screen.grid_rowconfigure(3, weight=1)

        self.menu_bubble_wrap = ctk.CTkFrame(self.menu_screen, fg_color="transparent")
        self.menu_bubble_wrap.grid(row=0, column=0, padx=24, pady=(24, 10), sticky="w")
        self.menu_bubble = ctk.CTkLabel(
            self.menu_bubble_wrap,
            text="",
            font=self.base_font,
            text_color="#fef3c7",
            justify="left",
            wraplength=1020,
            fg_color="#2e234a",
            image=self.pixel_images.get("agent_avatar"),
            compound="left",
            corner_radius=8,
            padx=16,
            pady=12,
        )
        self.menu_bubble.grid(row=0, column=0, sticky="w")
        self.menu_bob_bubble = ctk.CTkLabel(
            self.menu_bubble_wrap,
            text="",
            font=self.base_font,
            text_color="#fef3c7",
            justify="left",
            wraplength=1020,
            fg_color="#253044",
            image=self.pixel_images.get("bob_avatar"),
            compound="left",
            corner_radius=8,
            padx=16,
            pady=12,
        )
        self.menu_bob_bubble.grid(row=1, column=0, sticky="w", pady=(8, 0))

        self.menu_action_button = ctk.CTkButton(
            self.menu_screen,
            text=_ui_text("Nice to meet you"),
            command=self._go_to_story_layer,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=True),
        )
        self.menu_action_button.grid(row=1, column=0, padx=24, pady=(2, 12), sticky="w")

        self.story_title_label = ctk.CTkLabel(
            self.menu_screen,
            text=_ui_text("Choose Your Story"),
            font=self.title_font,
        )
        self.story_title_label.grid(row=2, column=0, padx=24, pady=(2, 8), sticky="w")

        self.story_list_frame = ctk.CTkScrollableFrame(self.menu_screen, width=900)
        self.story_list_frame.grid(row=3, column=0, padx=24, pady=(0, 20), sticky="nsew")
        self.story_list_frame.configure(fg_color="#2b2046")

        self.game_screen = ctk.CTkFrame(self.screen_stack, fg_color="#231a3a", border_width=2, border_color="#5b4b8a")
        self.game_screen.grid(row=0, column=0, sticky="nsew")
        self.game_screen.grid_columnconfigure(0, weight=1)
        self.game_screen.grid_rowconfigure(0, weight=1)

        self.chat_stream = ctk.CTkScrollableFrame(self.game_screen)
        self.chat_stream.grid(row=0, column=0, padx=12, pady=(8, 6), sticky="nsew")
        self.chat_stream.grid_columnconfigure(0, weight=1)
        self.chat_stream.configure(fg_color="#17142a")

        self.thinking_label = ctk.CTkLabel(self.game_screen, text="", font=self.status_font, text_color="#60a5fa")
        self.thinking_label.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="w")

        self.action_row = ctk.CTkFrame(self.game_screen, fg_color="transparent")
        self.action_row.grid(row=2, column=0, padx=16, pady=(0, 16), sticky="ew")
        self.action_row.grid_columnconfigure(0, weight=1)

        self.question_entry = ctk.CTkEntry(
            self.action_row,
            placeholder_text=_ui_text("Ask anything to uncover the truth..."),
            font=self.base_font,
            fg_color="#140f25",
            border_width=2,
            border_color="#8b5cf6",
            text_color="#f8fafc",
        )
        self.question_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.question_entry.bind("<Return>", lambda _event: self.on_ask_question())

        self.ask_button = ctk.CTkButton(
            self.action_row,
            text=_ui_text("Send"),
            width=110,
            command=self.on_ask_question,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=True),
        )
        self.ask_button.grid(row=0, column=1, padx=(0, 8))

        self.guess_button = ctk.CTkButton(
            self.action_row,
            text=_ui_text("Final Guess"),
            width=170,
            command=self.on_submit_guess,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=False),
        )
        self.guess_button.grid(row=0, column=2, padx=(0, 8))

        self.back_to_menu_button = ctk.CTkButton(
            self.action_row,
            text=_ui_text("Back to Story Menu"),
            command=self.on_reset,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=False),
        )
        self.back_to_menu_button.grid(row=0, column=3)
        self.back_to_menu_button.grid_remove()

        self.boot_progress = ctk.CTkProgressBar(self.main_panel, mode="indeterminate")
        self.boot_progress.grid(row=2, column=0, padx=24, pady=(0, 18), sticky="ew")
        self.boot_progress.start()
        self._build_startup_overlay()
        self._show_menu_layer_one()

    def _pixel_button_style(self, primary: bool) -> dict[str, object]:
        if primary:
            return {
                "fg_color": "#7c3aed",
                "hover_color": "#8b5cf6",
                "border_width": 2,
                "border_color": "#c4b5fd",
                "corner_radius": 6,
                "text_color": "#fef3c7",
            }
        return {
            "fg_color": "#334155",
            "hover_color": "#475569",
            "border_width": 2,
            "border_color": "#94a3b8",
            "corner_radius": 6,
            "text_color": "#f8fafc",
        }

    def _load_pixel_assets(self) -> None:
        self._load_richer_background()
        self._load_pixel_asset("agent_avatar", PIXEL_SPRITES_DIR / "BunnyBoy.png", zoom=4, frame_index=1)
        self._load_pixel_asset("bob_avatar", PIXEL_SPRITES_DIR / "DuckBoy.png", zoom=4, frame_index=1)
        self._load_pixel_asset("user_avatar", PIXEL_SPRITES_DIR / "CatKid.png", zoom=3, frame_index=1)
        self._load_pixel_asset("system_avatar", PIXEL_SPRITES_DIR / "Fox.png", zoom=4)
        self._load_pixel_asset("button_icon", PIXEL_UI_DIR / "Map-Node.png", zoom=3)
        self._load_pixel_asset("story_icon", PIXEL_UI_DIR / "ItemSlot1.png", zoom=1)

    def _load_richer_background(self) -> None:
        tile_path = PIXEL_SPRITES_DIR / "ForrestTiles.png"
        if not tile_path.exists():
            self._load_pixel_asset("bg", PIXEL_GB_DIR / "GameBoyBGSprites.png", zoom=2)
            return
        try:
            with Image.open(tile_path) as raw:
                tileset = raw.convert("RGBA")
            tile_size = 16
            base_tile = tileset.crop((0, 0, tile_size, tile_size))
            alt_tile = None
            if tileset.width >= tile_size * 2:
                alt_tile = tileset.crop((tile_size, 0, tile_size * 2, tile_size))

            canvas_size = (WINDOW_WIDTH, WINDOW_HEIGHT)
            canvas = Image.new("RGBA", canvas_size)
            for y in range(0, canvas_size[1], tile_size):
                for x in range(0, canvas_size[0], tile_size):
                    tile = alt_tile if alt_tile and ((x // tile_size + y // tile_size) % 2 == 0) else base_tile
                    canvas.paste(tile, (x, y), tile)

            # Darken the texture so foreground UI remains readable.
            overlay = Image.new("RGBA", canvas_size, (20, 16, 36, 130))
            image = Image.alpha_composite(canvas, overlay)
            self.pixel_images["bg"] = ctk.CTkImage(light_image=image, dark_image=image, size=canvas_size)
        except (OSError, tk.TclError):
            self._load_pixel_asset("bg", PIXEL_GB_DIR / "GameBoyBGSprites.png", zoom=2)

    def _load_pixel_asset(self, key: str, path: Path, zoom: int = 1, frame_index: int | None = None) -> None:
        if not path.exists():
            return
        try:
            with Image.open(path) as raw:
                image = raw.convert("RGBA")
            if frame_index is not None:
                image = self._extract_sprite_frame(image, frame_index)
            if zoom > 1:
                resampling = getattr(Image, "Resampling", Image)
                image = image.resize((image.width * zoom, image.height * zoom), resampling.NEAREST)
            self.pixel_images[key] = ctk.CTkImage(light_image=image, dark_image=image, size=image.size)
        except (OSError, tk.TclError):
            return

    def _extract_sprite_frame(self, image: Image.Image, frame_index: int) -> Image.Image:
        alpha = image.getchannel("A")
        if alpha.getbbox() is None:
            return image
        columns = [alpha.crop((x, 0, x + 1, image.height)).getbbox() is not None for x in range(image.width)]
        segments: list[tuple[int, int]] = []
        start: int | None = None
        for x, has_pixels in enumerate(columns):
            if has_pixels and start is None:
                start = x
            elif not has_pixels and start is not None:
                segments.append((start, x))
                start = None
        if start is not None:
            segments.append((start, image.width))
        if not segments:
            return image
        safe_index = min(max(frame_index, 0), len(segments) - 1)
        left, right = segments[safe_index]
        return image.crop((left, 0, right, image.height))

    def _load_boot_sequence(self) -> None:
        self.status_label.configure(text=_ui_text("Loading stories and sounds..."))
        self._start_startup_sequence()
        self.after(200, self._boot_async)

    def _boot_async(self) -> None:
        def worker() -> None:
            self.stories = load_stories(STORIES_DIR)
            try:
                self.sounds.initialize()
            except pygame.error:
                pass
            if self._startup_active:
                self.after(0, lambda: self.sounds.play("startup"))
            self.after(0, self._finish_boot)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_boot(self) -> None:
        self.boot_progress.stop()
        self.boot_progress.grid_remove()
        self._render_story_buttons()
        if self.stories:
            self.status_label.configure(text=_ui_text(f"Ready! {len(self.stories)} stories loaded."))
        else:
            self.status_label.configure(text=_ui_text("No stories found yet. Add a .txt story under stories/."))
        self._show_menu_layer_one()
        self._warn_if_audio_environment_is_limited()
        self._warn_if_font_environment_is_limited()

    def _build_startup_overlay(self) -> None:
        overlay = ctk.CTkFrame(self.main_panel, corner_radius=0, fg_color="#0f0a1d")
        overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        card = ctk.CTkFrame(overlay, fg_color="#1f1635", border_width=2, border_color="#7c3aed", corner_radius=12)
        card.place(relx=0.5, rely=0.5, relwidth=STARTUP_CARD_RELWIDTH, anchor="center")
        icon = ctk.CTkLabel(card, text="", image=self.pixel_images.get("agent_avatar"))
        icon.pack(padx=24, pady=(20, 8))
        title = ctk.CTkLabel(
            card,
            text=_ui_text("Turtle Soup"),
            font=self.title_font,
            text_color="#fef3c7",
        )
        title.pack(padx=24)
        subtitle = ctk.CTkLabel(
            card,
            text=_ui_text("this is a turtlesoup game developed by Owen bao, Jacky yang and Xuan Puu"),
            font=self.status_font,
            text_color="#d8b4fe",
            justify="center",
            wraplength=STARTUP_SUBTITLE_WRAP,
        )
        subtitle.pack(padx=24, pady=(10, 12))
        status = ctk.CTkLabel(
            card,
            text=_ui_text("Booting."),
            font=self.status_font,
            text_color="#93c5fd",
        )
        status.pack(padx=24, pady=(0, 20))
        self._startup_overlay = overlay
        self._startup_icon_label = icon
        self._startup_status_label = status

    def _start_startup_sequence(self) -> None:
        if self._startup_overlay is None:
            return
        self._startup_active = True
        self._startup_step = 0
        self._animate_startup_overlay()
        self.after(10000, self._end_startup_sequence)

    def _animate_startup_overlay(self) -> None:
        if not self._startup_active:
            return
        frames = [
            self.pixel_images.get("agent_avatar"),
            self.pixel_images.get("system_avatar"),
            self.pixel_images.get("user_avatar"),
            self.pixel_images.get("system_avatar"),
        ]
        colors = ["#93c5fd", "#c4b5fd", "#a7f3d0", "#d8b4fe"]
        dots = "." * ((self._startup_step % 3) + 1)
        frame = frames[self._startup_step % len(frames)]
        if self._startup_icon_label and frame:
            self._startup_icon_label.configure(image=frame)
        if self._startup_status_label:
            self._startup_status_label.configure(text=_ui_text(f"Booting{dots}"), text_color=colors[self._startup_step % len(colors)])
        self._startup_step += 1
        self.after(280, self._animate_startup_overlay)

    def _end_startup_sequence(self) -> None:
        self._startup_active = False
        if self._startup_overlay is not None:
            self._startup_overlay.destroy()
            self._startup_overlay = None
            self._startup_icon_label = None
            self._startup_status_label = None

    def _warn_if_font_environment_is_limited(self) -> None:
        families = {name.lower() for name in tkfont.families(self)}
        if families != {"fixed"}:
            return
        if self._font_env_warning_shown:
            return
        self._font_env_warning_shown = True
        message = (
            "Your Tk runtime only exposes the 'fixed' bitmap font, so font size settings are ignored.\n\n"
            "Please install scalable X11 fonts and restart the app. On Ubuntu/WSL:\n"
            "sudo apt update && sudo apt install -y xfonts-base xfonts-75dpi xfonts-100dpi\n\n"
            "After installation, restart your terminal/session and run the app again."
        )
        self._append_bubble("System", message, role="system")
        self.status_label.configure(text=_ui_text("Font environment limited: install scalable fonts to enable larger text"))

    def _warn_if_audio_environment_is_limited(self) -> None:
        if self._audio_env_warning_shown:
            return
        message = self.sounds.warning_message()
        if message is None:
            return
        self._audio_env_warning_shown = True
        self._append_bubble("System", message, role="system")
        self.status_label.configure(text=_ui_text("Audio output unavailable: check WSL audio runtime"))

    def _render_story_buttons(self) -> None:
        for widget in self.story_list_frame.winfo_children():
            widget.destroy()

        for index, story in enumerate(self.stories):
            button = ctk.CTkButton(
                self.story_list_frame,
                text=_ui_text(story.title),
                anchor="w",
                font=self.base_font,
                image=self.pixel_images.get("story_icon"),
                compound="left",
                **self._pixel_button_style(primary=False),
                command=lambda i=index: self._select_story_and_start(i),
            )
            button.pack(fill="x", padx=6, pady=6)

    def _show_menu_layer_one(self) -> None:
        self._menu_layer = 1
        self.menu_screen.tkraise()
        self.story_title_label.grid_remove()
        self.story_list_frame.grid_remove()
        self.menu_action_button.grid()
        self.menu_action_button.configure(state="normal")
        self.menu_bubble.configure(
            text=_ui_text("Hello, I am Soupie, your story game agent. I'll guide you through this mystery chat.")
        )
        self.menu_bob_bubble.grid()
        self.menu_bob_bubble.configure(
            text=_ui_text("Hello, I'm Bob. I focus on rational elimination questions to test hypotheses and reduce uncertainty.")
        )

    def _go_to_story_layer(self) -> None:
        self.sounds.play("click")
        self._show_menu_layer_two(first_prompt=True)

    def _show_menu_layer_two(self, first_prompt: bool = False) -> None:
        self._menu_layer = 2
        self.menu_screen.tkraise()
        self.menu_action_button.grid_remove()
        self.story_title_label.grid()
        self.story_list_frame.grid()
        self.menu_bob_bubble.grid_remove()
        if not self.stories:
            prompt = "No stories are available yet. Please add files under stories/."
        elif first_prompt:
            prompt = "Which story would you like to play?"
        else:
            prompt = "Which one would you like to play next?"
        self.menu_bubble.configure(text=_ui_text(prompt))
        if self.stories:
            self.status_label.configure(text=_ui_text("Choose your story to enter the chat room."))

    def _show_game_screen(self) -> None:
        self.game_screen.tkraise()
        self.back_to_menu_button.grid_remove()
        self._set_player_controls(True)

    def _select_story_and_start(self, index: int) -> None:
        self.selected_story_index = index
        self.on_start_story()

    def on_start_story(self) -> None:
        self.sounds.play("click")
        if self.selected_story_index is None:
            messagebox.showinfo(_ui_text("Notice"), _ui_text("Please choose a story first."))
            return
        story = self.stories[self.selected_story_index]
        self.session.start_story(story)
        self._story_epoch += 1
        self._clear_chat_bubbles()
        self._append_bubble("Soupy", f"Story setup: {story.surface}", role="agent")
        self._append_bubble("Soupy", "Ask your questions anytime. I will reply with only: Yes / No / Irrelevant.", role="agent")
        self.status_label.configure(text=_ui_text(f"Now playing: {story.title}"))
        self._show_game_screen()

    def on_reset(self) -> None:
        self.sounds.play("click")
        self.session.reset()
        self._story_epoch += 1
        self._set_thinking(False)
        self.question_entry.delete(0, tk.END)
        self.status_label.configure(text=_ui_text("New round ready"))
        self._show_menu_layer_two(first_prompt=False)

    def on_ask_question(self) -> None:
        self.sounds.play("click")
        if self.session.story is None:
            messagebox.showinfo(_ui_text("Notice"), _ui_text("Please start a story first."))
            return
        if self.is_thinking:
            messagebox.showinfo(_ui_text("Notice"), _ui_text("Please wait for the current reply to finish."))
            return
        if not self.session.can_ask():
            messagebox.showinfo(_ui_text("Notice"), _ui_text("Please wait for Bob to finish his turn."))
            return
        question = self.question_entry.get().strip()
        if not question:
            return

        self.question_entry.delete(0, tk.END)
        self.sounds.play("thinking")
        self._append_bubble("You", question, role="user")
        self._set_thinking(True)
        request_epoch = self._story_epoch

        def worker() -> None:
            story = self.session.story
            if story is None:
                self.after(
                    0,
                    lambda: self._on_worker_error(_ui_text("Current story is unavailable. Please start again."), request_epoch),
                )
                return
            try:
                answer = self.llm.ask_question(
                    surface=story.surface,
                    bottom=story.bottom,
                    question=question,
                    history=self.session.history,
                )
            except OpenAIError:
                self.after(
                    0,
                    lambda: self._on_worker_error(
                        _ui_text("Model did not respond. Check local service and retry."),
                        request_epoch,
                    ),
                )
                return
            self.after(0, lambda: self._on_question_answered(question, answer, request_epoch))

        threading.Thread(target=worker, daemon=True).start()

    def _on_question_answered(self, question: str, answer: str, request_epoch: int) -> None:
        if request_epoch != self._story_epoch or not self.session.can_ask():
            return
        self.session.add_qa(question, answer)
        self._append_bubble("Soupy", answer, role="agent")
        if self.session.bob_can_act():
            self._start_bob_turn()
        else:
            self._set_thinking(False)

    def _start_bob_turn(self) -> None:
        if self.session.story is None or not self.session.bob_can_act():
            self._finish_bob_turn()
            return
        self.session.to_bob_questioning()
        self.sounds.play("thinking")
        self._set_player_controls(False)
        self._set_thinking(True)
        self.status_label.configure(text=_ui_text("Bob is formulating a rational question..."))
        request_epoch = self._story_epoch

        def worker() -> None:
            story = self.session.story
            if story is None:
                self.after(
                    0,
                    lambda: self._on_worker_error(_ui_text("Current story is unavailable. Please start again."), request_epoch),
                )
                return
            try:
                action = self.llm.generate_bob_action(surface=story.surface, history=self.session.history)
            except OpenAIError:
                self.after(
                    0,
                    lambda: self._on_worker_error(
                        _ui_text("Bob couldn't respond right now. Please retry in a moment."),
                        request_epoch,
                    ),
                )
                return
            self.after(0, lambda: self._on_bob_action_ready(action, request_epoch))

        threading.Thread(target=worker, daemon=True).start()

    def _on_bob_action_ready(self, action: BobAction, request_epoch: int) -> None:
        if request_epoch != self._story_epoch or self.session.story is None:
            return
        if not self.session.bob_can_act():
            self._finish_bob_turn()
            return

        if action.action == "question":
            self._append_bubble("Bob", action.text, role="bob")
            self.status_label.configure(text=_ui_text("Soupy is answering Bob..."))
            request_epoch = self._story_epoch

            def worker() -> None:
                story = self.session.story
                if story is None:
                    self.after(
                        0,
                        lambda: self._on_worker_error(
                            _ui_text("Current story is unavailable. Please start again."),
                            request_epoch,
                        ),
                    )
                    return
                try:
                    answer = self.llm.ask_question(
                        surface=story.surface,
                        bottom=story.bottom,
                        question=action.text,
                        history=self.session.history,
                    )
                except OpenAIError:
                    self.after(
                        0,
                        lambda: self._on_worker_error(
                            _ui_text("Model did not respond. Check local service and retry."),
                            request_epoch,
                        ),
                    )
                    return
                self.after(0, lambda: self._on_bob_question_answered(action.text, answer, request_epoch))

            threading.Thread(target=worker, daemon=True).start()
            return

        self.session.to_bob_guessing()
        self._append_bubble("Bob", f"Final guess: {action.text}", role="bob")
        self.status_label.configure(text=_ui_text("Judging Bob's theory..."))
        request_epoch = self._story_epoch

        def worker() -> None:
            story = self.session.story
            if story is None:
                self.after(
                    0,
                    lambda: self._on_worker_error(_ui_text("Current story is unavailable. Please start again."), request_epoch),
                )
                return
            try:
                result = self.llm.judge_bob_guess(bottom=story.bottom, guess=action.text)
            except OpenAIError:
                self.after(
                    0,
                    lambda: self._on_worker_error(
                        _ui_text("Judge is unavailable right now. Please retry in a moment."),
                        request_epoch,
                    ),
                )
                return
            self.after(0, lambda: self._on_bob_guess_judged(result, request_epoch))

        threading.Thread(target=worker, daemon=True).start()

    def _on_bob_question_answered(self, question: str, answer: str, request_epoch: int) -> None:
        if request_epoch != self._story_epoch or self.session.story is None:
            return
        if not self.session.bob_can_act():
            self._finish_bob_turn()
            return
        self.session.add_qa(question, answer)
        self._append_bubble("Soupy", answer, role="agent")
        self.status_label.configure(text=_ui_text("Your turn to ask the next question."))
        self._finish_bob_turn()

    def _on_bob_guess_judged(self, result: JudgeResult, request_epoch: int) -> None:
        if request_epoch != self._story_epoch or self.session.story is None:
            return
        comment = result.comment or "Judgment completed."
        success = result.hit or result.score >= FINAL_GUESS_SUCCESS_SCORE
        if success:
            self.sounds.play("success")
        else:
            self.sounds.play("fail")
        self._append_bubble("Soupy", f"Bob's theory scored {result.score}/100. {comment}", role="agent")

        if success:
            self.status_label.configure(text=_ui_text("Bob cracked the case!"))
            self.session.state = GameState.IDLE
            full_story = self.session.story.bottom
            self._append_bubble("Soupy", f"Here is the full story: {full_story}", role="agent")
            self._append_bubble(
                "Soupy",
                "Which one would you like to play next? Click Back to Story Menu to continue.",
                role="agent",
            )
            self._set_player_controls(False)
            self.back_to_menu_button.grid()
            self._set_thinking(False)
            return

        self.session.mark_bob_crying()
        self._append_bubble("Bob", "I'll step back to reassess. Please continue your line of questioning.", role="bob")
        self.status_label.configure(text=_ui_text("Bob is stepping back to reassess. Your turn."))
        self.session.to_player_questioning()
        self._set_player_controls(True)
        self._set_thinking(False)

    def _finish_bob_turn(self) -> None:
        if self.session.story is not None:
            self.session.to_player_questioning()
        self._set_player_controls(True)
        self._set_thinking(False)

    def on_submit_guess(self) -> None:
        self.sounds.play("click")
        if self.session.story is None:
            messagebox.showinfo(_ui_text("Notice"), _ui_text("Please start a story first."))
            return
        if self.is_thinking:
            messagebox.showinfo(_ui_text("Notice"), _ui_text("Please wait for the current reply to finish."))
            return
        if self.session.state not in {GameState.QUESTIONING, GameState.BOB_CRYING}:
            messagebox.showinfo(
                _ui_text("Notice"),
                _ui_text("Please wait for Bob to finish his turn before submitting a final theory."),
            )
            return

        self.session.to_guessing()
        guess = self._prompt_final_guess()
        if not guess:
            self.session.to_player_questioning()
            return

        self.sounds.play("thinking")
        self._append_bubble("You", f"Final guess: {guess}", role="user")
        self._set_thinking(True)
        self.status_label.configure(text=_ui_text("Judging your theory..."))
        request_epoch = self._story_epoch

        def worker() -> None:
            story = self.session.story
            if story is None:
                self.after(
                    0,
                    lambda: self._on_worker_error(_ui_text("Current story is unavailable. Please start again."), request_epoch),
                )
                return
            try:
                result = self.llm.judge_guess(bottom=story.bottom, guess=guess)
            except OpenAIError:
                self.after(
                    0,
                    lambda: self._on_worker_error(_ui_text("Judge is unavailable right now. Please retry in a moment."), request_epoch),
                )
                return
            self.after(0, lambda: self._on_guess_judged(result, request_epoch))

        threading.Thread(target=worker, daemon=True).start()

    def _on_guess_judged(self, result: JudgeResult, request_epoch: int) -> None:
        if request_epoch != self._story_epoch or self.session.story is None:
            return
        full_story = self.session.story.bottom
        success = result.hit or result.score >= FINAL_GUESS_SUCCESS_SCORE
        verdict = _ui_text("Correct!") if success else _ui_text("Not quite.")
        if success:
            self.sounds.play("success")
        else:
            self.sounds.play("fail")
        self._append_bubble("Judge", f"{verdict} (match score {result.score}/100) {result.comment}", role="agent")
        if success:
            self.status_label.configure(text=_ui_text("Amazing! You solved it."))
            self.session.state = GameState.IDLE
        else:
            self.status_label.configure(text=_ui_text("Nice try. Full story revealed."))
            self.session.state = GameState.IDLE
        self._append_bubble("Soupy", f"Here is the full story: {full_story}", role="agent")
        self._append_bubble("Soupy", "Which one would you like to play next? Click Back to Story Menu to continue.", role="agent")
        self._set_player_controls(False)
        self.back_to_menu_button.grid()
        self._set_thinking(False)

    def _prompt_final_guess(self) -> str | None:
        dialog = ctk.CTkToplevel(self)
        dialog.title(_ui_text("Final Theory"))
        dialog.geometry("920x560")
        dialog.minsize(760, 460)
        dialog.configure(fg_color="#1f1635")
        dialog.transient(self)
        dialog.lift()
        dialog.update_idletasks()
        dialog.wait_visibility()
        dialog.grab_set()
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            dialog,
            text=_ui_text("Share your full final theory:"),
            font=self.base_font,
            anchor="w",
            justify="left",
            text_color="#fef3c7",
            image=self.pixel_images.get("agent_avatar"),
            compound="left",
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        guess_box = ctk.CTkTextbox(
            dialog,
            wrap="word",
            font=self.base_font,
            fg_color="#140f25",
            border_width=2,
            border_color="#8b5cf6",
            text_color="#f8fafc",
        )
        guess_box.grid(row=1, column=0, padx=20, pady=(0, 12), sticky="nsew")
        guess_box.focus_set()

        button_row = ctk.CTkFrame(dialog, fg_color="transparent")
        button_row.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="e")

        result: dict[str, str | None] = {"value": None}

        def close_dialog() -> None:
            if not dialog.winfo_exists():
                return
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            dialog.withdraw()
            dialog.update_idletasks()
            dialog.destroy()

        def submit() -> None:
            self.sounds.play("click")
            value = guess_box.get("1.0", "end").strip()
            if value:
                result["value"] = value
            close_dialog()

        def cancel() -> None:
            self.sounds.play("click")
            close_dialog()

        ctk.CTkButton(
            button_row,
            text=_ui_text("Cancel"),
            command=cancel,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=False),
        ).pack(
            side="right", padx=(10, 0)
        )
        ctk.CTkButton(
            button_row,
            text=_ui_text("Submit"),
            command=submit,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=True),
        ).pack(side="right")
        dialog.bind("<Escape>", lambda _event: cancel())
        dialog.bind("<Control-Return>", lambda _event: submit())
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        self.wait_window(dialog)
        return result["value"]

    def _set_player_controls(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.question_entry.configure(state=state)
        self.ask_button.configure(state=state)
        self.guess_button.configure(state=state)

    def _set_thinking(self, active: bool) -> None:
        self.is_thinking = active
        if active:
            self._thinking_step = 0
            self._animate_thinking()
        else:
            self.thinking_label.configure(text="")

    def _animate_thinking(self) -> None:
        if not self.is_thinking:
            return
        patterns = [_ui_text("Thinking   "), _ui_text("Thinking.  "), _ui_text("Thinking.. "), _ui_text("Thinking...")]
        colors = ["#60a5fa", "#93c5fd", "#60a5fa", "#3b82f6"]
        idx = self._thinking_step % len(patterns)
        self.thinking_label.configure(text=patterns[idx], text_color=colors[idx])
        self._thinking_step += 1
        self.after(350, self._animate_thinking)

    def _on_worker_error(self, message: str, request_epoch: int) -> None:
        if request_epoch != self._story_epoch:
            return
        self._set_thinking(False)
        self._append_bubble("Soupy", message, role="agent")
        if self.session.story is not None:
            self.session.to_player_questioning()
        self._set_player_controls(True)

    def _clear_chat_bubbles(self) -> None:
        for widget in self.chat_stream.winfo_children():
            widget.destroy()
        self._chat_row = 0

    def _append_bubble(self, speaker: str, text: str, role: str) -> None:
        self.sounds.play_message(role)
        is_user = role == "user"
        if is_user:
            row_frame = ctk.CTkFrame(self.chat_stream, fg_color="transparent")
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid(row=self._chat_row, column=0, sticky="ew", padx=4, pady=6)
            bubble = ctk.CTkFrame(
                row_frame,
                fg_color="#1f3654",
                border_width=2,
                border_color="#7dd3fc",
                corner_radius=8,
            )
            bubble.grid(row=0, column=1, sticky="e", padx=(130, 0))
            speaker_color = "#bae6fd"
            message_color = "#e2e8f0"
            avatar = self.pixel_images.get("user_avatar")
        elif role == "system":
            row_frame = ctk.CTkFrame(self.chat_stream, fg_color="transparent")
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid(row=self._chat_row, column=0, sticky="ew", padx=4, pady=6)
            bubble = ctk.CTkFrame(
                row_frame,
                fg_color="#3a275a",
                border_width=2,
                border_color="#c4b5fd",
                corner_radius=8,
            )
            bubble.grid(row=0, column=0, sticky="w", padx=(0, 130))
            speaker_color = "#ddd6fe"
            message_color = "#f5f3ff"
            avatar = self.pixel_images.get("system_avatar")
        elif role == "bob":
            row_frame = ctk.CTkFrame(self.chat_stream, fg_color="transparent")
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid(row=self._chat_row, column=0, sticky="ew", padx=4, pady=6)
            bubble = ctk.CTkFrame(
                row_frame,
                fg_color="#2a3b2f",
                border_width=2,
                border_color="#86efac",
                corner_radius=8,
            )
            bubble.grid(row=0, column=0, sticky="w", padx=(0, 130))
            speaker_color = "#bbf7d0"
            message_color = "#ecfccb"
            avatar = self.pixel_images.get("bob_avatar")
        else:
            row_frame = ctk.CTkFrame(self.chat_stream, fg_color="transparent")
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid(row=self._chat_row, column=0, sticky="ew", padx=4, pady=6)
            bubble = ctk.CTkFrame(
                row_frame,
                fg_color="#22453f",
                border_width=2,
                border_color="#6ee7b7",
                corner_radius=8,
            )
            bubble.grid(row=0, column=0, sticky="w", padx=(0, 130))
            speaker_color = "#a7f3d0"
            message_color = "#ecfeff"
            avatar = self.pixel_images.get("agent_avatar")

        ctk.CTkLabel(
            bubble,
            text=_ui_text(speaker),
            justify="left",
            anchor="w",
            wraplength=760,
            text_color=speaker_color,
            font=self.base_font,
            image=avatar,
            compound="left",
        ).pack(padx=14, pady=(10, 4), fill="x")
        ctk.CTkLabel(
            bubble,
            text=_ui_text(text),
            justify="left",
            anchor="w",
            wraplength=760,
            text_color=message_color,
            font=self.base_font,
        ).pack(padx=14, pady=(0, 10), fill="x")
        self._chat_row += 1

        canvas = getattr(self.chat_stream, "_parent_canvas", None)
        if canvas is not None:
            self.after(20, lambda: canvas.yview_moveto(1.0))
