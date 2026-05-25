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
    BOB_ANSWER_STRATEGY,
    BOB_ENABLED,
    BOB_QUESTION_STRATEGY,
    BOB_TRAIT,
    CONTEXT_WINDOW,
    MODEL_API_KEY,
    MODEL_BASE_URL,
    MODEL_NAME,
    MODEL_TEMPERATURE,
    PROJECT_ROOT,
    SFX_DIR,
    STORIES_DIR,
    USER_DATA_PATH,
)
from app.data.story_loader import Story, load_stories
from app.data.user_manager import UserManager, UserProfile
from app.game.manager import GameSession
from app.game.state import GameState
from app.i18n import LANGUAGE, UI
from app.llm.client import BobAction, JudgeResult, LLMEngine

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


class TurtleSoupApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        ctk.set_widget_scaling(UI_SCALE)
        ctk.set_window_scaling(UI_SCALE)

        self.title(UI["startup_title"] + " · Story Night")
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
        self.user_manager = UserManager(
            USER_DATA_PATH,
            default_bob_avatar="bob",
        )
        self.stories: list[Story] = []
        self.selected_story_index: int | None = None
        self.is_thinking = False
        self._thinking_step = 0
        self._story_epoch = 0
        self._menu_layer = 1
        self._chat_row = 0
        self._turn_count = 0  # Total Q&A turns (player + Bob)
        self._sidebar_labels: list[str] = []
        self._bob_question_count = 0
        self._bob_guess_count = 0
        self._startup_active = False
        self._startup_step = 0
        self._startup_overlay: ctk.CTkFrame | None = None
        self._startup_icon_label: ctk.CTkLabel | None = None
        self._startup_status_label: ctk.CTkLabel | None = None
        self._audio_env_warning_shown = False
        available_families = {name.lower() for name in tkfont.families(self)}
        # Prefer Chinese-supporting fonts on Windows
        for preferred in ["microsoft yahei", "simhei", "simsun", "helvetica"]:
            if preferred in available_families:
                family = preferred
                break
        else:
            family = "fixed"
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
            text=UI["boot_preparing"],
            font=self.status_font,
            text_color="#c7d2fe",
            image=self.pixel_images.get("system_avatar"),
            compound="left",
        )
        self.status_label.grid(row=0, column=0, padx=24, pady=(20, 8), sticky="w")

        self.lang_toggle_button = ctk.CTkButton(
            self.main_panel,
            text=UI["lang_toggle"],
            command=self._toggle_language,
            font=ctk.CTkFont(family="helvetica" if "helvetica" in tkfont.families() else "fixed", size=14),
            width=100,
            height=36,
            fg_color="#4c1d95",
            hover_color="#6d28d9",
            border_width=2,
            border_color="#a78bfa",
            corner_radius=8,
            text_color="#fef3c7",
        )
        self.lang_toggle_button.grid(row=0, column=1, padx=24, pady=(20, 8), sticky="e")

        self.lang_label = ctk.CTkLabel(
            self.main_panel,
            text=UI["lang_label"],
            font=ctk.CTkFont(family="helvetica" if "helvetica" in tkfont.families() else "fixed", size=14),
            text_color="#c7d2fe",
        )
        self.lang_label.grid(row=0, column=2, padx=(0, 8), pady=(20, 8), sticky="e")

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
            fg_color="#253044" if BOB_ENABLED else "#1a1a2e",
            image=self.pixel_images.get("bob_avatar"),
            compound="left",
            corner_radius=8,
            padx=16,
            pady=12,
        )
        self.menu_bob_bubble.bind("<Button-1>", lambda e: self._toggle_bob_from_menu())
        self.menu_bob_bubble.bind("<Enter>", lambda e: self._on_bob_bubble_enter())
        self.menu_bob_bubble.bind("<Leave>", lambda e: self._on_bob_bubble_leave())
        self.menu_bob_bubble.grid(row=1, column=0, sticky="w", pady=(8, 0))

        # Bob attributes gear button (next to Bob bubble)
        self.menu_bob_gear = ctk.CTkButton(
            self.menu_bubble_wrap,
            text="⚙",
            width=32,
            height=32,
            font=ctk.CTkFont(size=16),
            fg_color="#253044",
            hover_color="#2a3a54",
            text_color="#fef3c7",
            corner_radius=6,
            command=self._show_bob_attributes_page,
        )
        self.menu_bob_gear.grid(row=1, column=1, sticky="w", pady=(8, 0), padx=(8, 0))

        self.menu_action_button = ctk.CTkButton(
            self.menu_screen,
            text=UI["menu_greeting"],
            command=self._go_to_story_layer,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=True),
        )
        self.menu_action_button.grid(row=1, column=0, padx=24, pady=(2, 12), sticky="w")

        self.player_select_button = ctk.CTkButton(
            self.menu_screen,
            text=UI["player_choose"],
            command=self._go_to_player_screen,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=False),
        )
        self.player_select_button.grid(row=2, column=0, padx=24, pady=(2, 8), sticky="w")

        self.story_title_label = ctk.CTkLabel(
            self.menu_screen,
            text=UI["menu_choose"],
            font=self.title_font,
        )
        self.story_title_label.grid(row=2, column=0, padx=24, pady=(2, 8), sticky="w")

        self.story_list_frame = ctk.CTkScrollableFrame(self.menu_screen, width=900)
        self.story_list_frame.grid(row=3, column=0, padx=24, pady=(0, 8), sticky="nsew")
        self.story_list_frame.configure(fg_color="#2b2046")

        self.story_manage_button = ctk.CTkButton(
            self.menu_screen,
            text=UI["story_management_title"],
            command=self._open_story_management,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=False),
        )
        self.story_manage_button.grid(row=4, column=0, padx=24, pady=(8, 20), sticky="w")

        self.leaderboard_button = ctk.CTkButton(
            self.menu_screen,
            text=UI["leaderboard_title"],
            command=self._go_to_leaderboard,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=False),
        )
        self.leaderboard_button.grid(row=5, column=0, padx=24, pady=(0, 8), sticky="w")

        self.menu_back_button = ctk.CTkButton(
            self.menu_screen,
            text=UI["game_back_to_menu"],
            command=self._back_to_menu_layer_one,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=False),
        )
        self.menu_back_button.grid(row=6, column=0, padx=24, pady=(0, 20), sticky="w")
        self.menu_back_button.grid_remove()

        # Story management screen
        self.story_manage_screen = ctk.CTkFrame(self.screen_stack, fg_color="#231a3a", border_width=2, border_color="#5b4b8a")
        self.story_manage_screen.grid(row=0, column=0, sticky="nsew")
        self.story_manage_screen.grid_remove()
        self.story_manage_screen.grid_columnconfigure(0, weight=1)
        self.story_manage_screen.grid_rowconfigure(1, weight=1)

        self.story_manage_header = ctk.CTkLabel(
            self.story_manage_screen,
            text=UI["story_management_title"],
            font=self.title_font,
            text_color="#fef3c7",
        )
        self.story_manage_header.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="w")

        self.story_manage_list_frame = ctk.CTkScrollableFrame(self.story_manage_screen, width=900)
        self.story_manage_list_frame.grid(row=1, column=0, padx=24, pady=(0, 10), sticky="nsew")
        self.story_manage_list_frame.configure(fg_color="#2b2046")

        self.story_manage_bottom = ctk.CTkFrame(self.story_manage_screen, fg_color="transparent")
        self.story_manage_bottom.grid(row=2, column=0, padx=24, pady=(10, 20), sticky="w")

        self.story_manage_back_button = ctk.CTkButton(
            self.story_manage_bottom,
            text=UI["story_management_back"],
            command=self._back_to_menu,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=False),
        )
        self.story_manage_back_button.pack(side="left")

        self.story_manage_add_button = ctk.CTkButton(
            self.story_manage_bottom,
            text=UI["story_management_add"],
            command=self._open_custom_story_dialog_from_manage,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=True),
        )
        self.story_manage_add_button.pack(side="left", padx=(12, 0))

        # Player selection screen
        self.player_screen = ctk.CTkFrame(self.screen_stack, fg_color="#231a3a", border_width=2, border_color="#5b4b8a")
        self.player_screen.grid(row=0, column=0, sticky="nsew")
        self.player_screen.grid_remove()
        self.player_screen.grid_columnconfigure(0, weight=1)
        self.player_screen.grid_rowconfigure(2, weight=1)

        self.player_title_label = ctk.CTkLabel(
            self.player_screen,
            text=UI["player_choose"],
            font=self.title_font,
            text_color="#fef3c7",
        )
        self.player_title_label.grid(row=0, column=0, padx=24, pady=(20, 6), sticky="w")
        self.player_hint_label = ctk.CTkLabel(
            self.player_screen,
            text=UI["player_hint"],
            font=self.status_font,
            text_color="#c7d2fe",
        )
        self.player_hint_label.grid(row=1, column=0, padx=24, pady=(0, 10), sticky="w")

        self.player_list_frame = ctk.CTkScrollableFrame(self.player_screen, width=940)
        self.player_list_frame.grid(row=2, column=0, padx=24, pady=(0, 16), sticky="nsew")
        self.player_list_frame.configure(fg_color="#2b2046")

        self.player_action_row = ctk.CTkFrame(self.player_screen, fg_color="transparent")
        self.player_action_row.grid(row=3, column=0, padx=24, pady=(0, 20), sticky="ew")
        self.player_action_row.grid_columnconfigure(0, weight=1)
        self.create_user_button = ctk.CTkButton(
            self.player_action_row,
            text=UI["player_create"],
            command=self._create_user_flow,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=True),
        )
        self.create_user_button.pack(side="right")

        # Leaderboard screen
        self.leaderboard_screen = ctk.CTkFrame(self.screen_stack, fg_color="#231a3a", border_width=2, border_color="#5b4b8a")
        self.leaderboard_screen.grid(row=0, column=0, sticky="nsew")
        self.leaderboard_screen.grid_remove()
        self.leaderboard_screen.grid_columnconfigure(0, weight=1)
        self.leaderboard_screen.grid_rowconfigure(1, weight=1)

        self.leaderboard_title_label = ctk.CTkLabel(
            self.leaderboard_screen,
            text=UI["leaderboard_title"],
            font=self.title_font,
            text_color="#fef3c7",
        )
        self.leaderboard_title_label.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="w")

        self.leaderboard_list_frame = ctk.CTkScrollableFrame(self.leaderboard_screen, width=940)
        self.leaderboard_list_frame.grid(row=1, column=0, padx=24, pady=(0, 16), sticky="nsew")
        self.leaderboard_list_frame.configure(fg_color="#2b2046")

        self.leaderboard_action_row = ctk.CTkFrame(self.leaderboard_screen, fg_color="transparent")
        self.leaderboard_action_row.grid(row=2, column=0, padx=24, pady=(0, 20), sticky="ew")
        self.leaderboard_action_row.grid_columnconfigure(0, weight=1)
        self.leaderboard_back_button = ctk.CTkButton(
            self.leaderboard_action_row,
            text=UI["leaderboard_back"],
            command=self._back_from_leaderboard,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=False),
        )
        self.leaderboard_back_button.pack(side="right")

        # Bob attributes screen
        self.bob_attr_screen = ctk.CTkFrame(self.screen_stack, fg_color="#231a3a", border_width=2, border_color="#5b4b8a")
        self.bob_attr_screen.grid(row=0, column=0, sticky="nsew")
        self.bob_attr_screen.grid_remove()
        self.bob_attr_screen.grid_columnconfigure(0, weight=1)
        self.bob_attr_screen.grid_rowconfigure(1, weight=1)

        self._build_bob_attributes_screen()

        self.game_screen = ctk.CTkFrame(self.screen_stack, fg_color="#231a3a", border_width=2, border_color="#5b4b8a")
        self.game_screen.grid(row=0, column=0, sticky="nsew")
        self.game_screen.grid_remove()
        self.game_screen.grid_columnconfigure(0, weight=1)
        self.game_screen.grid_columnconfigure(1, weight=0)
        self.game_screen.grid_rowconfigure(1, weight=1)

        # Right sidebar for turn info
        self.game_sidebar = ctk.CTkFrame(
            self.game_screen,
            fg_color="#2b2046",
            border_width=2,
            border_color="#5b4b8a",
            corner_radius=10,
            width=180,
        )
        self.game_sidebar.grid(row=0, column=1, rowspan=4, padx=(0, 12), pady=(10, 16), sticky="ns")
        self.game_sidebar.grid_propagate(False)

        self.sidebar_title = ctk.CTkLabel(
            self.game_sidebar,
            text="回合记录",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#fef3c7",
        )
        self.sidebar_title.pack(pady=(16, 8))

        self.sidebar_turns = ctk.CTkScrollableFrame(self.game_sidebar, fg_color="transparent")
        self.sidebar_turns.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.sidebar_turn_label = ctk.CTkLabel(
            self.game_sidebar,
            text="第 0 轮",
            font=ctk.CTkFont(size=14),
            text_color="#a78bfa",
        )
        self.sidebar_turn_label.pack(pady=(0, 12))

        # Bob stats display (in-game)
        self.bob_stats_frame = ctk.CTkFrame(self.game_sidebar, fg_color="#1a1a2e", corner_radius=8)
        self.bob_stats_frame.pack(pady=(0, 8), padx=8, fill="x")
        self.bob_stats_frame.pack_forget()

        self.bob_stats_label = ctk.CTkLabel(
            self.bob_stats_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#a78bfa",
            justify="left",
            wraplength=160,
        )
        self.bob_stats_label.pack(padx=8, pady=8)

        self.story_header = ctk.CTkFrame(
            self.game_screen,
            fg_color="#2b2046",
            border_width=2,
            border_color="#7c3aed",
            corner_radius=10,
        )
        self.story_header.grid(row=0, column=0, padx=12, pady=(10, 6), sticky="ew")
        self.story_header.grid_columnconfigure(0, weight=1)
        self.story_header_title = ctk.CTkLabel(
            self.story_header,
            text=UI["game_story_surface"],
            font=self.status_font,
            text_color="#fef3c7",
            image=self.pixel_images.get("agent_avatar"),
            compound="left",
            anchor="w",
        )
        self.story_header_title.grid(row=0, column=0, padx=16, pady=(10, 4), sticky="w")
        self.story_header_text = ctk.CTkLabel(
            self.story_header,
            text=UI["game_story_header_empty"],
            font=self.base_font,
            text_color="#f8fafc",
            justify="left",
            wraplength=1160,
            anchor="w",
        )
        self.story_header_text.grid(row=1, column=0, padx=16, pady=(0, 12), sticky="w")

        self.chat_stream = ctk.CTkScrollableFrame(self.game_screen)
        self.chat_stream.grid(row=1, column=0, padx=12, pady=(6, 6), sticky="nsew")
        self.chat_stream.grid_columnconfigure(0, weight=1)
        self.chat_stream.configure(fg_color="#17142a")
        self._bind_chat_scroll()

        self.thinking_label = ctk.CTkLabel(self.game_screen, text="", font=self.status_font, text_color="#60a5fa")
        self.thinking_label.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="w")

        self.action_row = ctk.CTkFrame(self.game_screen, fg_color="transparent")
        self.action_row.grid(row=3, column=0, padx=16, pady=(0, 16), sticky="ew")
        self.action_row.grid_columnconfigure(0, weight=1)

        self.question_entry = ctk.CTkEntry(
            self.action_row,
            placeholder_text=UI["game_question_placeholder"],
            font=self.base_font,
            fg_color="#140f25",
            border_width=2,
            border_color="#8b5cf6",
            text_color="#f8fafc",
        )
        self.question_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.question_entry.bind("<Return>", lambda _event: self.on_ask_question())

        self.voice_button = ctk.CTkButton(
            self.action_row,
            text="",
            width=50,
            command=self._start_voice_input,
            font=ctk.CTkFont(size=20),
            fg_color="#4a3f6c",
            hover_color="#6b5f8c",
            text_color="#fef3c7",
            corner_radius=8,
        )
        self.voice_button.grid(row=0, column=1, padx=(0, 8))

        self.ask_button = ctk.CTkButton(
            self.action_row,
            text=UI["game_send"],
            width=110,
            command=self.on_ask_question,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=True),
        )
        self.ask_button.grid(row=0, column=2, padx=(0, 8))

        self.guess_button = ctk.CTkButton(
            self.action_row,
            text=UI["game_final_guess"],
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
            text=UI["game_back_to_menu"],
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

    def _toggle_language(self) -> None:
        self.sounds.play("click")
        new_lang = "en" if LANGUAGE == "zh" else "zh"
        messagebox.showinfo(
            UI["dialog_notice"],
            UI["lang_restart_notice"].format(lang=new_lang),
        )
        import os
        os.environ["TS_LANGUAGE"] = new_lang
        self.destroy()
        import subprocess
        import sys
        subprocess.Popen([sys.executable, sys.argv[0]])

    def _toggle_bob_from_menu(self) -> None:
        self.sounds.play("click")
        global BOB_ENABLED
        BOB_ENABLED = not BOB_ENABLED
        import os
        os.environ["TS_BOB_ENABLED"] = "true" if BOB_ENABLED else "false"
        # Update menu bob bubble appearance
        if BOB_ENABLED:
            self.menu_bob_bubble.configure(
                fg_color="#253044",
                text=UI["menu_bob_intro"],
            )
        else:
            self.menu_bob_bubble.configure(
                fg_color="#1a1a2e",
                text=UI["menu_bob_intro"],
            )

    def _on_bob_bubble_enter(self) -> None:
        current = self.menu_bob_bubble.cget("fg_color")
        if current == "#253044":
            self.menu_bob_bubble.configure(fg_color="#2a3a54")
        elif current == "#1a1a2e":
            self.menu_bob_bubble.configure(fg_color="#252540")

    def _on_bob_bubble_leave(self) -> None:
        if BOB_ENABLED:
            self.menu_bob_bubble.configure(fg_color="#253044")
        else:
            self.menu_bob_bubble.configure(fg_color="#1a1a2e")

    def _build_bob_attributes_screen(self) -> None:
        """Build the separate Bob attributes page."""
        # Header
        header = ctk.CTkLabel(
            self.bob_attr_screen,
            text="Bob 属性",
            font=self.title_font,
            text_color="#fef3c7",
        )
        header.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="w")

        # Main content area
        content = ctk.CTkFrame(self.bob_attr_screen, fg_color="#2b2046", corner_radius=12)
        content.grid(row=1, column=0, padx=24, pady=(0, 16), sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        # Avatar on left
        avatar_frame = ctk.CTkFrame(content, fg_color="transparent")
        avatar_frame.grid(row=0, column=0, padx=(40, 20), pady=40, sticky="n")
        avatar_label = ctk.CTkLabel(
            avatar_frame,
            text="",
            image=self.pixel_images.get("bob_avatar"),
        )
        avatar_label.pack()

        # Settings on right
        settings_frame = ctk.CTkFrame(content, fg_color="transparent")
        settings_frame.grid(row=0, column=1, padx=(0, 40), pady=40, sticky="nsew")

        # Name
        name_label = ctk.CTkLabel(
            settings_frame,
            text="名称: BOB",
            font=ctk.CTkFont(size=28),
            text_color="#fef3c7",
        )
        name_label.pack(anchor="w", pady=(0, 30))

        # Question strategy slider
        q_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        q_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(
            q_frame, text="提问策略: 谨慎",
            font=ctk.CTkFont(size=18),
            text_color="#c7d2fe",
        ).pack(side="left")
        self.bob_q_slider = ctk.CTkSlider(
            q_frame,
            from_=1, to=10, number_of_steps=9,
            width=300,
            progress_color="#4a7cc9",
            button_color="#6b9fd4",
            button_hover_color="#8bb8e0",
        )
        self.bob_q_slider.pack(side="left", padx=12)
        self.bob_q_slider.set(BOB_QUESTION_STRATEGY)
        ctk.CTkLabel(
            q_frame, text="跳越",
            font=ctk.CTkFont(size=18),
            text_color="#c7d2fe",
        ).pack(side="left")

        # Answer strategy slider
        a_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        a_frame.pack(fill="x", pady=10)
        ctk.CTkLabel(
            a_frame, text="回答策略: 保守",
            font=ctk.CTkFont(size=18),
            text_color="#c7d2fe",
        ).pack(side="left")
        self.bob_a_slider = ctk.CTkSlider(
            a_frame,
            from_=1, to=10, number_of_steps=9,
            width=300,
            progress_color="#4a7cc9",
            button_color="#6b9fd4",
            button_hover_color="#8bb8e0",
        )
        self.bob_a_slider.set(BOB_ANSWER_STRATEGY)
        self.bob_a_slider.pack(side="left", padx=12)
        ctk.CTkLabel(
            a_frame, text="激进",
            font=ctk.CTkFont(size=18),
            text_color="#c7d2fe",
        ).pack(side="left")

        # Trait segmented control (villain / normal / genius)
        trait_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        trait_frame.pack(fill="x", pady=(20, 10))
        ctk.CTkLabel(
            trait_frame, text="特性:",
            font=ctk.CTkFont(size=18),
            text_color="#c7d2fe",
        ).pack(side="left", padx=(0, 16))

        # Create segmented control container
        trait_segment_frame = ctk.CTkFrame(trait_frame, fg_color="#3a2f5c", corner_radius=8)
        trait_segment_frame.pack(side="left")

        trait_options = [
            ("坏蛋", "villain"),
            ("普通", "normal"),
            ("天才", "genius"),
        ]
        self._bob_trait_buttons: dict[str, ctk.CTkButton] = {}
        self._bob_trait_selected = BOB_TRAIT

        for i, (label, value) in enumerate(trait_options):
            is_selected = value == self._bob_trait_selected
            btn = ctk.CTkButton(
                trait_segment_frame,
                text=label,
                width=100,
                height=40,
                font=ctk.CTkFont(size=20, weight="bold"),
                fg_color="#e8833a" if is_selected else "transparent",
                hover_color="#e8833a" if is_selected else "#4a3f6c",
                text_color="#ffffff" if is_selected else "#8a8a9a",
                corner_radius=6,
                command=lambda v=value: self._set_bob_trait(v),
            )
            btn.pack(side="left", padx=2, pady=2)
            self._bob_trait_buttons[value] = btn

        # Bottom: back button
        bottom_frame = ctk.CTkFrame(self.bob_attr_screen, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, padx=24, pady=(10, 20), sticky="w")

        self.bob_attr_back_button = ctk.CTkButton(
            bottom_frame,
            text="返回",
            command=self._back_to_menu_from_bob_attr,
            font=self.base_font,
            image=self.pixel_images.get("button_icon"),
            compound="left",
            **self._pixel_button_style(primary=False),
        )
        self.bob_attr_back_button.pack(side="left")

    def _set_bob_trait(self, value: str) -> None:
        """Update Bob's trait selection and update button styles."""
        self._bob_trait_selected = value
        for trait_val, btn in self._bob_trait_buttons.items():
            is_selected = trait_val == value
            btn.configure(
                fg_color="#e8833a" if is_selected else "transparent",
                hover_color="#e8833a" if is_selected else "#4a3f6c",
                text_color="#ffffff" if is_selected else "#8a8a9a",
            )

    def _show_bob_attributes_page(self) -> None:
        self.sounds.play("click")
        self.menu_screen.grid_remove()
        self.story_manage_screen.grid_remove()
        self.game_screen.grid_remove()
        self.bob_attr_screen.tkraise()
        self.bob_attr_screen.grid()
        # Update sliders to current values
        self.bob_q_slider.set(BOB_QUESTION_STRATEGY)
        self.bob_a_slider.set(BOB_ANSWER_STRATEGY)
        self._set_bob_trait(BOB_TRAIT)

    def _back_to_menu_from_bob_attr(self) -> None:
        self.sounds.play("click")
        # Save values
        global BOB_QUESTION_STRATEGY, BOB_ANSWER_STRATEGY, BOB_TRAIT
        BOB_QUESTION_STRATEGY = int(self.bob_q_slider.get())
        BOB_ANSWER_STRATEGY = int(self.bob_a_slider.get())
        BOB_TRAIT = self._bob_trait_selected
        import os
        os.environ["TS_BOB_QUESTION_STRATEGY"] = str(BOB_QUESTION_STRATEGY)
        os.environ["TS_BOB_ANSWER_STRATEGY"] = str(BOB_ANSWER_STRATEGY)
        os.environ["TS_BOB_TRAIT"] = BOB_TRAIT

        self.bob_attr_screen.grid_remove()
        self._show_menu_layer_one()

    def _show_bob_attributes(self) -> None:
        """Show Bob's in-game stats in the sidebar."""
        self.sounds.play("click")
        if self.bob_stats_frame.winfo_viewable():
            self.bob_stats_frame.pack_forget()
            return

        if self.session.story is None:
            self.bob_stats_label.configure(text="暂无游戏数据")
        else:
            status = "已退场" if self.session.bob_crying else "活跃中"
            q_desc = "谨慎" if BOB_QUESTION_STRATEGY <= 3 else ("一般" if BOB_QUESTION_STRATEGY <= 7 else "跳越")
            a_desc = "保守" if BOB_ANSWER_STRATEGY <= 3 else ("一般" if BOB_ANSWER_STRATEGY <= 7 else "激进")
            trait_label = {"villain": "坏蛋", "normal": "正常", "genius": "天才"}.get(BOB_TRAIT, "正常")
            self.bob_stats_label.configure(
                text=(
                    f"状态: {status}\n"
                    f"提问数: {self._bob_question_count}\n"
                    f"猜测数: {self._bob_guess_count}\n"
                    f"提问策略: {q_desc} ({BOB_QUESTION_STRATEGY}/10)\n"
                    f"回答策略: {a_desc} ({BOB_ANSWER_STRATEGY}/10)\n"
                    f"特性: {trait_label}"
                )
            )
        self.bob_stats_frame.pack(pady=(0, 8), padx=8, fill="x")

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
        self.status_label.configure(text=UI["boot_loading"])
        self._start_startup_sequence()
        self.after(200, self._boot_async)

    def _boot_async(self) -> None:
        def worker() -> None:
            self.stories = [s.get_localized(LANGUAGE) for s in load_stories(STORIES_DIR)]
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
            self.status_label.configure(text=UI["boot_ready"].format(count=len(self.stories)))
        else:
            self.status_label.configure(text=UI["boot_no_stories"])
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
            text=UI["startup_title"],
            font=self.title_font,
            text_color="#fef3c7",
        )
        title.pack(padx=24)
        subtitle = ctk.CTkLabel(
            card,
            text=UI["startup_subtitle"],
            font=self.status_font,
            text_color="#d8b4fe",
            justify="center",
            wraplength=STARTUP_SUBTITLE_WRAP,
        )
        subtitle.pack(padx=24, pady=(10, 12))
        status = ctk.CTkLabel(
            card,
            text=UI["startup_booting"] + ".",
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
            self._startup_status_label.configure(text=UI["startup_booting"] + dots, text_color=colors[self._startup_step % len(colors)])
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
        self.status_label.configure(text=UI["status_font_limited"])

    def _warn_if_audio_environment_is_limited(self) -> None:
        if self._audio_env_warning_shown:
            return
        message = self.sounds.warning_message()
        if message is None:
            return
        self._audio_env_warning_shown = True
        self._append_bubble("System", message, role="system")
        self.status_label.configure(text=UI["status_audio_unavailable"])

    def _render_story_buttons(self) -> None:
        for widget in self.story_list_frame.winfo_children():
            widget.destroy()

        for index, story in enumerate(self.stories):
            button = ctk.CTkButton(
                self.story_list_frame,
                text=story.title,
                anchor="w",
                font=self.base_font,
                image=self.pixel_images.get("story_icon"),
                compound="left",
                **self._pixel_button_style(primary=False),
                command=lambda i=index: self._select_story_and_start(i),
            )
            button.pack(fill="x", padx=6, pady=6)

    def _render_story_manage_buttons(self) -> None:
        for widget in self.story_manage_list_frame.winfo_children():
            widget.destroy()

        for story in self.stories:
            row = ctk.CTkFrame(self.story_manage_list_frame, fg_color="transparent")
            row.pack(fill="x", padx=6, pady=4)

            title_btn = ctk.CTkButton(
                row,
                text=story.title,
                anchor="w",
                font=self.base_font,
                image=self.pixel_images.get("story_icon"),
                compound="left",
                **self._pixel_button_style(primary=False),
                command=lambda s=story: self._open_custom_story_edit_dialog(s),
            )
            title_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

            delete_btn = ctk.CTkButton(
                row,
                text="✕",
                font=self.base_font,
                width=40,
                fg_color="#dc2626",
                hover_color="#b91c1c",
                corner_radius=6,
                text_color="#fef3c7",
                command=lambda s=story: self._delete_story(s),
            )
            delete_btn.pack(side="right")

    def _open_story_management(self) -> None:
        self.sounds.play("click")
        self._render_story_manage_buttons()
        self.menu_screen.grid_remove()
        self.bob_attr_screen.grid_remove()
        self.game_screen.grid_remove()
        self.story_manage_screen.grid()
        self.story_manage_screen.tkraise()

    def _back_to_menu(self) -> None:
        self.sounds.play("click")
        self.story_manage_screen.grid_remove()
        self.bob_attr_screen.grid_remove()
        self.game_screen.grid_remove()
        self.menu_screen.grid()
        self.menu_screen.tkraise()

    def _open_custom_story_dialog_from_manage(self) -> None:
        self._open_custom_story_dialog(from_manage=True)

    def _delete_story(self, story: Story) -> None:
        filename = story.source_file.name
        if messagebox.askyesno(UI["dialog_notice"], UI["story_management_delete_confirm"].format(story=filename)):
            try:
                story.source_file.unlink()
                self.stories = [s.get_localized(LANGUAGE) for s in load_stories(STORIES_DIR)]
                self._render_story_manage_buttons()
                self._render_story_buttons()
                messagebox.showinfo(UI["dialog_notice"], UI["story_management_deleted"])
            except Exception as e:
                messagebox.showerror(UI["dialog_notice"], f"Failed to delete: {e}")

    def _show_menu_layer_one(self) -> None:
        self._menu_layer = 1
        self.menu_screen.grid()
        self.menu_screen.tkraise()
        self.story_title_label.grid_remove()
        self.story_list_frame.grid_remove()
        self.menu_action_button.grid()
        self.menu_action_button.configure(state="normal")
        self.menu_bubble.configure(
            text=UI["menu_soupie_intro"]
        )
        if BOB_ENABLED:
            self.menu_bob_bubble.grid()
            self.menu_bob_bubble.configure(
                text=UI["menu_bob_intro"]
            )
            self.menu_bob_gear.grid()
        else:
            self.menu_bob_bubble.grid_remove()
            self.menu_bob_gear.grid_remove()

    def _go_to_story_layer(self) -> None:
        self.sounds.play("click")
        self._show_menu_layer_two(first_prompt=True)

    def _show_menu_layer_two(self, first_prompt: bool = False) -> None:
        self._menu_layer = 2
        self.story_manage_screen.grid_remove()
        self.bob_attr_screen.grid_remove()
        self.game_screen.grid_remove()
        self.menu_screen.grid()
        self.menu_screen.tkraise()
        self.menu_action_button.grid_remove()
        self.story_title_label.grid()
        self.story_list_frame.grid()
        self.menu_bob_bubble.grid_remove()
        self.menu_bob_gear.grid_remove()
        self.menu_back_button.grid()
        if not self.stories:
            prompt = UI["menu_no_stories"]
        elif first_prompt:
            prompt = UI["menu_first_prompt"]
        else:
            prompt = UI["menu_retry_prompt"]
        self.menu_bubble.configure(text=prompt)
        if self.stories:
            self.status_label.configure(text=UI["status_choose_story"])

    def _back_to_menu_layer_one(self) -> None:
        self.sounds.play("click")
        self._show_menu_layer_one()
        self.menu_back_button.grid_remove()

    def _show_game_screen(self) -> None:
        self.game_screen.grid()
        self.game_screen.tkraise()
        self.back_to_menu_button.grid_remove()
        self._set_player_controls(True)

    def _select_story_and_start(self, index: int) -> None:
        self.selected_story_index = index
        self.on_start_story()

    def on_start_story(self) -> None:
        self.sounds.play("click")
        if self.selected_story_index is None:
            messagebox.showinfo(UI["dialog_notice"], UI["dialog_choose_story"])
            return
        story = self.stories[self.selected_story_index]
        self.session.start_story(story)
        self._story_epoch += 1
        self._turn_count = 0
        self._bob_question_count = 0
        self._bob_guess_count = 0
        self._clear_chat_bubbles()
        self._clear_sidebar_turns()
        self._set_story_header(story)
        self._update_sidebar_turn_label()
        self._append_bubble(
            UI["speaker_soupy"],
            UI["bubble_story"],
            role="agent",
        )
        self.status_label.configure(text=UI["status_playing"].format(title=story.title))
        self._show_game_screen()

    def on_reset(self) -> None:
        self.sounds.play("click")
        self.session.reset()
        self._story_epoch += 1
        self._set_thinking(False)
        self.question_entry.delete(0, tk.END)
        self._clear_chat_bubbles()
        self._set_story_header(None)
        self.selected_story_index = None
        self.back_to_menu_button.grid_remove()
        self.status_label.configure(text=UI["dialog_new_round"])
        self._show_menu_layer_two(first_prompt=False)

    def on_ask_question(self) -> None:
        self.sounds.play("click")
        if self.session.story is None:
            messagebox.showinfo(UI["dialog_notice"], UI["dialog_start_story"])
            return
        if self.is_thinking:
            messagebox.showinfo(UI["dialog_notice"], UI["dialog_wait_reply"])
            return
        if not self.session.can_ask():
            messagebox.showinfo(UI["dialog_notice"], UI["dialog_wait_bob"])
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
                    lambda: self._on_worker_error(UI["dialog_story_unavailable"], request_epoch),
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
                        UI["dialog_model_no_response"],
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
        self._add_sidebar_turn(f"玩家: {question[:30]}...", "#60a5fa")
        if BOB_ENABLED and self.session.bob_can_act():
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
        self.status_label.configure(text=UI["dialog_bob_thinking"])
        request_epoch = self._story_epoch

        # Answer strategy affects Bob's response speed (1=slow, 10=fast)
        # Map 1-10 to delay: 1 -> 3s, 10 -> 0.3s
        bob_delay = max(0.3, 3.3 - 0.3 * BOB_ANSWER_STRATEGY)

        def worker() -> None:
            import time
            time.sleep(bob_delay)
            story = self.session.story
            if story is None:
                self.after(
                    0,
                    lambda: self._on_worker_error(UI["dialog_story_unavailable"], request_epoch),
                )
                return
            try:
                action = self.llm.generate_bob_action(
                    surface=story.surface,
                    bottom=story.bottom if BOB_TRAIT != "normal" else None,
                    history=self.session.history,
                    turn_count=self._turn_count,
                    question_strategy=BOB_QUESTION_STRATEGY,
                    answer_strategy=BOB_ANSWER_STRATEGY,
                    trait=BOB_TRAIT,
                )
            except OpenAIError:
                self.after(
                    0,
                    lambda: self._on_worker_error(
                        UI["dialog_bob_no_response"],
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
            self.status_label.configure(text=UI["dialog_soupy_answering"])
            request_epoch = self._story_epoch

            def worker() -> None:
                story = self.session.story
                if story is None:
                    self.after(
                        0,
                        lambda: self._on_worker_error(
                            UI["dialog_story_unavailable"],
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
                            UI["dialog_model_no_response"],
                            request_epoch,
                        ),
                    )
                    return
                self.after(0, lambda: self._on_bob_question_answered(action.text, answer, request_epoch))

            threading.Thread(target=worker, daemon=True).start()
            return

        self.session.to_bob_guessing()
        # Show Bob's reasoning before the guess
        if action.reasoning:
            self._append_bubble("Bob", f"[思考] {action.reasoning}", role="bob")
        self._append_bubble("Bob", f"Final guess: {action.text}", role="bob")
        self.status_label.configure(text=UI["status_judging_bob"])
        request_epoch = self._story_epoch

        def worker() -> None:
            story = self.session.story
            if story is None:
                self.after(
                    0,
                    lambda: self._on_worker_error(UI["dialog_story_unavailable"], request_epoch),
                )
                return
            try:
                result = self.llm.judge_bob_guess(bottom=story.bottom, guess=action.text)
            except OpenAIError:
                self.after(
                    0,
                    lambda: self._on_worker_error(
                        UI["dialog_judge_unavailable"],
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
        self._bob_question_count += 1
        self._append_bubble("Soupy", answer, role="agent")
        self._add_sidebar_turn(f"Bob: {question[:30]}...", "#34d399")
        self.status_label.configure(text=UI["status_next_question"])
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

        if success:
            self._bob_guess_count += 1
            self._append_bubble("Soupy", f"Bob's theory scored {result.score}/100. {comment}", role="agent")
            self._add_sidebar_turn(f"Bob 猜测: {result.score}分", "#34d399")
            self.status_label.configure(text=UI["status_bob_cracked"])
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

        # Bob guessed wrong - no score, no story reveal
        self._bob_guess_count += 1
        self._add_sidebar_turn("Bob 猜测错误", "#f87171")
        self.session.mark_bob_crying()
        self._append_bubble("Bob", "I'll step back to reassess. Please continue your line of questioning.", role="bob")
        self.status_label.configure(text=UI["status_bob_reassess"])
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
            messagebox.showinfo(UI["dialog_notice"], UI["dialog_start_story"])
            return
        if self.is_thinking:
            messagebox.showinfo(UI["dialog_notice"], UI["dialog_wait_reply"])
            return
        if self.session.state not in {GameState.QUESTIONING, GameState.BOB_CRYING}:
            messagebox.showinfo(
                UI["dialog_notice"],
                UI["dialog_wait_bob_guess"],
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
        self.status_label.configure(text=UI["status_judging_player"])
        request_epoch = self._story_epoch

        def worker() -> None:
            story = self.session.story
            if story is None:
                self.after(
                    0,
                    lambda: self._on_worker_error(UI["dialog_story_unavailable"], request_epoch),
                )
                return
            try:
                result = self.llm.judge_guess(bottom=story.bottom, guess=guess)
            except OpenAIError:
                self.after(
                    0,
                    lambda: self._on_worker_error(UI["dialog_judge_unavailable"], request_epoch),
                )
                return
            self.after(0, lambda: self._on_guess_judged(result, request_epoch))

        threading.Thread(target=worker, daemon=True).start()

    def _on_guess_judged(self, result: JudgeResult, request_epoch: int) -> None:
        if request_epoch != self._story_epoch or self.session.story is None:
            return
        full_story = self.session.story.bottom
        success = result.hit or result.score >= FINAL_GUESS_SUCCESS_SCORE
        verdict = UI["dialog_correct"] if success else UI["dialog_not_quite"]
        if success:
            self.sounds.play("success")
        else:
            self.sounds.play("fail")
        self._append_bubble("Judge", f"{verdict} (match score {result.score}/100) {result.comment}", role="agent")
        self._add_sidebar_turn(f"玩家猜测: {result.score}分", "#f87171" if not success else "#34d399")

        # Record score for the active player
        if self.session.player_name:
            try:
                self.session.apply_final_score(self.user_manager, result.score)
            except RuntimeError:
                pass  # No active player, skip scoring

        if success:
            self.status_label.configure(text=UI["status_player_solved"])
            self.session.state = GameState.IDLE
        else:
            self.status_label.configure(text=UI["status_player_close"])
            self.session.state = GameState.IDLE
        self._append_bubble("Soupy", f"Here is the full story: {full_story}", role="agent")
        self._append_bubble("Soupy", "Which one would you like to play next? Click Back to Story Menu to continue.", role="agent")
        self._set_player_controls(False)
        self.back_to_menu_button.grid()
        self._set_thinking(False)

    def _prompt_final_guess(self) -> str | None:
        dialog = ctk.CTkToplevel(self)
        dialog.title(UI["dialog_final_title"])
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
            text=UI["dialog_final_prompt"],
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
            text=UI["dialog_cancel"],
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
            text=UI["dialog_submit"],
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

    def _detect_language(self, text: str) -> str:
        """Simple heuristic: if text contains Chinese characters, it's Chinese."""
        for ch in text:
            if "\u4e00" <= ch <= "\u9fff":
                return "zh"
        return "en"

    def _open_custom_story_dialog(self, from_manage: bool = False, edit_story: Story | None = None) -> None:
        self.sounds.play("click")
        dialog = ctk.CTkToplevel(self)
        is_edit = edit_story is not None
        dialog.title(UI["custom_story_title"] if not is_edit else f"{UI['custom_story_title']} - {edit_story.title}")
        dialog.geometry("700x600")
        dialog.minsize(600, 500)
        dialog.configure(fg_color="#1f1635")
        dialog.transient(self)
        dialog.grab_set()

        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(4, weight=1)

        # Pre-fill if editing
        orig_title = edit_story.title_zh or edit_story.title_en if is_edit else ""
        orig_surface = edit_story.surface_zh or edit_story.surface_en if is_edit else ""
        orig_bottom = edit_story.bottom_zh or edit_story.bottom_en if is_edit else ""

        # Title
        ctk.CTkLabel(
            dialog,
            text=UI["custom_story_label_title"],
            font=self.base_font,
            anchor="w",
            text_color="#fef3c7",
        ).grid(row=0, column=0, padx=24, pady=(20, 4), sticky="w")
        title_entry = ctk.CTkEntry(
            dialog,
            placeholder_text=UI["custom_story_placeholder_title"],
            font=self.base_font,
            fg_color="#140f25",
            border_width=2,
            border_color="#8b5cf6",
            text_color="#f8fafc",
        )
        title_entry.grid(row=1, column=0, padx=24, pady=(0, 12), sticky="ew")
        if orig_title:
            title_entry.insert(0, orig_title)

        # Surface
        ctk.CTkLabel(
            dialog,
            text=UI["custom_story_label_surface"],
            font=self.base_font,
            anchor="w",
            text_color="#fef3c7",
        ).grid(row=2, column=0, padx=24, pady=(4, 4), sticky="w")
        surface_text = ctk.CTkTextbox(
            dialog,
            font=self.base_font,
            fg_color="#140f25",
            border_width=2,
            border_color="#8b5cf6",
            text_color="#f8fafc",
            height=100,
        )
        surface_text.grid(row=3, column=0, padx=24, pady=(0, 12), sticky="ew")
        if orig_surface:
            surface_text.insert("1.0", orig_surface)

        # Bottom
        ctk.CTkLabel(
            dialog,
            text=UI["custom_story_label_bottom"],
            font=self.base_font,
            anchor="w",
            text_color="#fef3c7",
        ).grid(row=4, column=0, padx=24, pady=(4, 4), sticky="w")
        bottom_text = ctk.CTkTextbox(
            dialog,
            font=self.base_font,
            fg_color="#140f25",
            border_width=2,
            border_color="#8b5cf6",
            text_color="#f8fafc",
            height=120,
        )
        bottom_text.grid(row=5, column=0, padx=24, pady=(0, 16), sticky="nsew")
        if orig_bottom:
            bottom_text.insert("1.0", orig_bottom)

        # Buttons
        button_row = ctk.CTkFrame(dialog, fg_color="transparent")
        button_row.grid(row=6, column=0, padx=24, pady=(0, 20), sticky="e")

        def _translate_story(title: str, surface: str, bottom: str, target_lang: str) -> dict:
            """Translate entire story using the local LLM. Returns dict with title, surface, bottom."""
            if target_lang == "zh":
                system_prompt = """你是一个专业的翻译助手。请将以下海龟汤故事翻译成中文。
要求：
1. 保持悬疑感和故事氛围
2. 语言简洁流畅，符合中文表达习惯
3. 严格按照以下JSON格式返回，不要添加任何其他内容：
{"title": "翻译后的标题", "surface": "翻译后的汤面", "bottom": "翻译后的汤底"}"""
            else:
                system_prompt = """You are a professional translation assistant. Please translate the following Turtle Soup story into English.
Requirements:
1. Maintain the suspenseful atmosphere
2. Use concise and natural English
3. Return ONLY a valid JSON object in this exact format, nothing else:
{"title": "translated title", "surface": "translated surface", "bottom": "translated bottom"}"""

            try:
                from openai import OpenAI
                import json
                client = OpenAI(base_url=MODEL_BASE_URL, api_key=MODEL_API_KEY)
                user_content = f"Title: {title}\nSurface: {surface}\nBottom: {bottom}"
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_content},
                    ],
                )
                result_text = response.choices[0].message.content.strip()
                # Try to parse JSON
                try:
                    result = json.loads(result_text)
                    return {
                        "title": result.get("title", ""),
                        "surface": result.get("surface", ""),
                        "bottom": result.get("bottom", ""),
                    }
                except json.JSONDecodeError:
                    # Fallback: try to extract from markdown code block
                    if "```" in result_text:
                        json_str = result_text.split("```")[1]
                        if json_str.startswith("json"):
                            json_str = json_str[4:]
                        result = json.loads(json_str.strip())
                        return {
                            "title": result.get("title", ""),
                            "surface": result.get("surface", ""),
                            "bottom": result.get("bottom", ""),
                        }
                    return {"title": "", "surface": "", "bottom": ""}
            except Exception:
                return {"title": "", "surface": "", "bottom": ""}

        def save_story() -> None:
            title = title_entry.get().strip()
            surface = surface_text.get("1.0", tk.END).strip()
            bottom = bottom_text.get("1.0", tk.END).strip()

            if not title or not surface or not bottom:
                messagebox.showwarning(UI["dialog_notice"], UI["custom_story_fill_all"])
                return

            # Auto-detect language
            lang = self._detect_language(title + surface + bottom)
            target_lang = "en" if lang == "zh" else "zh"

            # Show translating status
            save_btn.configure(state="disabled", text=UI["custom_story_translating"])
            dialog.update()

            # Translate entire story at once
            translated = _translate_story(title, surface, bottom, target_lang)
            title_translated = translated["title"] or title
            surface_translated = translated["surface"] or surface
            bottom_translated = translated["bottom"] or bottom

            # Build bilingual file content
            if lang == "zh":
                content = (
                    f"[Title_zh]\n{title}\n\n"
                    f"[Surface_zh]\n{surface}\n\n"
                    f"[Bottom_zh]\n{bottom}\n\n"
                    f"[Title_en]\n{title_translated}\n\n"
                    f"[Surface_en]\n{surface_translated}\n\n"
                    f"[Bottom_en]\n{bottom_translated}\n"
                )
            else:
                content = (
                    f"[Title_en]\n{title}\n\n"
                    f"[Surface_en]\n{surface}\n\n"
                    f"[Bottom_en]\n{bottom}\n\n"
                    f"[Title_zh]\n{title_translated}\n\n"
                    f"[Surface_zh]\n{surface_translated}\n\n"
                    f"[Bottom_zh]\n{bottom_translated}\n"
                )

            # Generate filename
            safe_title = re.sub(r"[^\w\s-]", "", title).strip().replace(" ", "_")
            if not safe_title:
                safe_title = "custom_story"
            filename = f"{safe_title}.txt"
            filepath = STORIES_DIR / filename

            # Avoid overwriting (skip existing file if editing)
            counter = 1
            while filepath.exists() and (not is_edit or filepath != edit_story.source_file):
                filename = f"{safe_title}_{counter}.txt"
                filepath = STORIES_DIR / filename
                counter += 1

            filepath.write_text(content, encoding="utf-8")

            # Reload stories
            self.stories = [s.get_localized(LANGUAGE) for s in load_stories(STORIES_DIR)]
            self._render_story_buttons()
            if from_manage:
                self._render_story_manage_buttons()

            messagebox.showinfo(UI["dialog_notice"], UI["custom_story_saved"])
            dialog.destroy()

        cancel_btn = ctk.CTkButton(
            button_row,
            text=UI["dialog_cancel"],
            command=dialog.destroy,
            font=self.base_font,
            **self._pixel_button_style(primary=False),
        )
        cancel_btn.pack(side="right", padx=(10, 0))

        save_btn = ctk.CTkButton(
            button_row,
            text=UI["dialog_submit"],
            command=save_story,
            font=self.base_font,
            **self._pixel_button_style(primary=True),
        )
        save_btn.pack(side="right")

        self.wait_window(dialog)

    def _open_custom_story_edit_dialog(self, story: Story) -> None:
        self._open_custom_story_dialog(from_manage=True, edit_story=story)

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

    def _bind_chat_scroll(self) -> None:
        canvas = getattr(self.chat_stream, "_parent_canvas", None)
        if canvas is None:
            return

        def is_descendant(widget: tk.Widget | None, parent: tk.Widget) -> bool:
            current = widget
            while current is not None:
                if current == parent:
                    return True
                current = current.master
            return False

        def on_mousewheel(event: tk.Event) -> None:
            if not is_descendant(event.widget, self.chat_stream):
                return
            if event.delta:
                step = int(-1 * (event.delta / 120))
                if step == 0:
                    step = -1 if event.delta > 0 else 1
                canvas.yview_scroll(step, "units")
                return
            if getattr(event, "num", None) == 4:
                canvas.yview_scroll(-3, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(3, "units")

        self.bind_all("<MouseWheel>", on_mousewheel, add="+")
        self.bind_all("<Button-4>", on_mousewheel, add="+")
        self.bind_all("<Button-5>", on_mousewheel, add="+")

    def _set_story_header(self, story: Story | None) -> None:
        if story is None:
            self.story_header_title.configure(text=UI["game_story_surface"])
            self.story_header_text.configure(text=UI["game_story_header_empty"])
            return
        self.story_header_title.configure(text=UI["game_story_surface_title"].format(title=story.title))
        self.story_header_text.configure(text=story.surface)

    def _animate_thinking(self) -> None:
        if not self.is_thinking:
            return
        patterns = UI["game_thinking"]
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
        self._reset_chat_scroll()

    def _reset_chat_scroll(self) -> None:
        canvas = getattr(self.chat_stream, "_parent_canvas", None)
        if canvas is None:
            return
        canvas.configure(scrollregion=(0, 0, 0, 0))
        canvas.yview_moveto(0.0)

    def _scroll_chat_to_bottom(self) -> None:
        canvas = getattr(self.chat_stream, "_parent_canvas", None)
        if canvas is None:
            return
        canvas.update_idletasks()
        bbox = canvas.bbox("all")
        if bbox is not None:
            canvas.configure(scrollregion=bbox)
        canvas.yview_moveto(1.0)

    def _clear_sidebar_turns(self) -> None:
        for widget in self.sidebar_turns.winfo_children():
            widget.destroy()
        self._sidebar_labels.clear()

    def _update_sidebar_turn_label(self) -> None:
        self.sidebar_turn_label.configure(text=f"第 {self._turn_count} 轮")

    def _add_sidebar_turn(self, label: str, color: str = "#a78bfa") -> None:
        self._turn_count += 1
        self._sidebar_labels.append(label)
        turn_frame = ctk.CTkFrame(self.sidebar_turns, fg_color="transparent")
        turn_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(
            turn_frame,
            text=f"{self._turn_count}. {label}",
            font=ctk.CTkFont(size=12),
            text_color=color,
            anchor="w",
        ).pack(fill="x")
        self._update_sidebar_turn_label()
        # Auto-scroll sidebar to bottom
        canvas = getattr(self.sidebar_turns, "_parent_canvas", None)
        if canvas is not None:
            canvas.update_idletasks()
            bbox = canvas.bbox("all")
            if bbox is not None:
                canvas.configure(scrollregion=bbox)
            canvas.yview_moveto(1.0)

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
            text=speaker,
            justify="left",
            anchor="w",
            wraplength=370,
            text_color=speaker_color,
            font=self.base_font,
            image=avatar,
            compound="left",
        ).pack(padx=14, pady=(10, 4), fill="x")
        ctk.CTkLabel(
            bubble,
            text=text,
            justify="left",
            anchor="w",
            wraplength=370,
            text_color=message_color,
            font=self.base_font,
        ).pack(padx=14, pady=(0, 10), fill="x")
        self._chat_row += 1

        canvas = getattr(self.chat_stream, "_parent_canvas", None)
        if canvas is not None:
            self.after(20, self._scroll_chat_to_bottom)

    # ── Player selection & leaderboard ──────────────────────────────────────

    def _go_to_player_screen(self) -> None:
        self.sounds.play("click")
        self.menu_screen.grid_remove()
        self.player_screen.grid()
        self._refresh_player_list()

    def _show_player_screen(self) -> None:
        self.menu_screen.grid_remove()
        self.player_screen.grid()
        self._refresh_player_list()

    def _go_to_leaderboard(self) -> None:
        self.sounds.play("click")
        self.menu_screen.grid_remove()
        self.leaderboard_screen.grid()
        self._refresh_leaderboard()

    def _show_leaderboard_screen(self) -> None:
        self.menu_screen.grid_remove()
        self.leaderboard_screen.grid()
        self._refresh_leaderboard()

    def _back_from_leaderboard(self) -> None:
        self.sounds.play("click")
        self.leaderboard_screen.grid_remove()
        self.menu_screen.grid()

    def _refresh_player_list(self) -> None:
        for widget in self.player_list_frame.winfo_children():
            widget.destroy()

        users = self.user_manager.list_users()
        if not users:
            ctk.CTkLabel(
                self.player_list_frame,
                text=UI["leaderboard_empty"],
                font=self.base_font,
                text_color="#c7d2fe",
            ).pack(pady=40)
            return

        for user in users:
            row = ctk.CTkFrame(self.player_list_frame, fg_color="#2b2046")
            row.pack(fill="x", padx=8, pady=4)

            ctk.CTkLabel(
                row,
                text=user.name,
                font=self.base_font,
                text_color="#fef3c7",
                anchor="w",
            ).pack(side="left", padx=16, pady=10)

            ctk.CTkLabel(
                row,
                text=f'{UI["leaderboard_score"]}: {user.total_score}',
                font=ctk.CTkFont(size=16),
                text_color="#a78bfa",
                anchor="w",
            ).pack(side="left", padx=16, pady=10)

            ctk.CTkButton(
                row,
                text=UI["player_select"],
                width=100,
                command=lambda name=user.name: self._select_user(name),
                font=ctk.CTkFont(size=14),
                **self._pixel_button_style(primary=True),
            ).pack(side="right", padx=8)

            if user.name.casefold() != "bob":
                ctk.CTkButton(
                    row,
                    text=UI["player_delete"],
                    width=80,
                    command=lambda name=user.name: self._delete_user(name),
                    font=ctk.CTkFont(size=14),
                    fg_color="#dc2626",
                    hover_color="#ef4444",
                    text_color="#fef3c7",
                    corner_radius=6,
                ).pack(side="right", padx=8)

    def _create_user_flow(self) -> None:
        self.sounds.play("click")
        self._prompt_new_user()

    def _prompt_new_user(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title(UI["player_create_title"])
        dialog.geometry("500x300")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=UI["player_name_label"],
            font=self.base_font,
        ).pack(pady=(20, 4))

        name_entry = ctk.CTkEntry(
            dialog,
            placeholder_text=UI["player_name_placeholder"],
            font=self.base_font,
            width=300,
        )
        name_entry.pack(pady=(0, 16))

        def on_create() -> None:
            name = name_entry.get().strip()
            if not name:
                messagebox.showwarning(UI["dialog_notice"], UI["player_name_empty"])
                return
            try:
                profile = self.user_manager.add_user(name, "default")
                messagebox.showinfo(UI["dialog_notice"], UI["player_created"].format(name=name))
                dialog.destroy()
                self._refresh_player_list()
            except ValueError:
                messagebox.showwarning(UI["dialog_notice"], UI["player_name_exists"])

        ctk.CTkButton(
            dialog,
            text=UI["dialog_submit"],
            command=on_create,
            font=self.base_font,
            **self._pixel_button_style(primary=True),
        ).pack(pady=16)

        name_entry.focus_set()
        name_entry.bind("<Return>", lambda _e: on_create())

    def _select_user(self, name: str) -> None:
        self.sounds.play("click")
        self.session.set_player(name)
        self.player_screen.grid_remove()
        self._show_menu_layer_one()

    def _delete_user(self, name: str) -> None:
        if messagebox.askyesno(
            UI["dialog_notice"],
            UI["player_delete_confirm"].format(player=name),
        ):
            try:
                self.user_manager.delete_user(name)
                messagebox.showinfo(UI["dialog_notice"], UI["player_deleted"])
                self._refresh_player_list()
            except ValueError as e:
                messagebox.showwarning(UI["dialog_notice"], str(e))

    def _refresh_leaderboard(self) -> None:
        for widget in self.leaderboard_list_frame.winfo_children():
            widget.destroy()

        users = self.user_manager.leaderboard()
        if not users:
            ctk.CTkLabel(
                self.leaderboard_list_frame,
                text=UI["leaderboard_empty"],
                font=self.base_font,
                text_color="#c7d2fe",
            ).pack(pady=40)
            return

        for i, user in enumerate(users, 1):
            row = ctk.CTkFrame(self.leaderboard_list_frame, fg_color="#2b2046")
            row.pack(fill="x", padx=8, pady=4)

            ctk.CTkLabel(
                row,
                text=f'{UI["leaderboard_rank"]} {i}',
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#fef3c7",
                width=80,
                anchor="w",
            ).pack(side="left", padx=16, pady=10)

            ctk.CTkLabel(
                row,
                text=user.name,
                font=self.base_font,
                text_color="#fef3c7",
                anchor="w",
            ).pack(side="left", padx=16, pady=10)

            ctk.CTkLabel(
                row,
                text=str(user.total_score),
                font=ctk.CTkFont(size=18, weight="bold"),
                text_color="#a78bfa",
                width=80,
                anchor="e",
            ).pack(side="right", padx=16, pady=10)

    # ── Voice input ─────────────────────────────────────────────────────────

    def _start_voice_input(self) -> None:
        """Start voice recognition in a background thread."""
        self.sounds.play("click")
        try:
            import speech_recognition as sr
        except ImportError:
            messagebox.showwarning(
                UI["dialog_notice"],
                "语音输入需要安装 speech_recognition 库。\n请运行: pip install SpeechRecognition pyaudio",
            )
            return

        self.voice_button.configure(text="🎤", fg_color="#e8833a")
        self.status_label.configure(text="正在聆听...")

        import threading

        def _recognize() -> None:
            try:
                recognizer = sr.Recognizer()
                with sr.Microphone() as source:
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=15)

                # Try Chinese first, then English
                try:
                    text = recognizer.recognize_google(audio, language="zh-CN")
                except sr.UnknownValueError:
                    try:
                        text = recognizer.recognize_google(audio, language="en-US")
                    except sr.UnknownValueError:
                        self.after(0, lambda: self._voice_done(None, "未能识别语音,请重试。"))
                        return

                self.after(0, lambda: self._voice_done(text, None))

            except sr.WaitTimeoutError:
                self.after(0, lambda: self._voice_done(None, "未检测到语音输入,请重试。"))
            except sr.RequestError as e:
                self.after(0, lambda: self._voice_done(None, f"语音识别服务错误: {e}"))
            except Exception as e:
                self.after(0, lambda: self._voice_done(None, f"语音输入错误: {e}"))

        threading.Thread(target=_recognize, daemon=True).start()

    def _voice_done(self, text: str | None, error: str | None) -> None:
        """Handle voice recognition result on the main thread."""
        self.voice_button.configure(text="🎤", fg_color="#4a3f6c")
        self.status_label.configure(text=UI["status_ready"])

        if error:
            messagebox.showinfo(UI["dialog_notice"], error)
            return

        if text:
            self.question_entry.delete(0, tk.END)
            self.question_entry.insert(0, text)
