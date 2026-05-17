from __future__ import annotations

import os
import re
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import messagebox

import customtkinter as ctk
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame
from openai import OpenAIError

from app.audio.sound_manager import SoundManager
from app.config import (
    CONTEXT_WINDOW,
    MODEL_API_KEY,
    MODEL_BASE_URL,
    MODEL_NAME,
    MODEL_TEMPERATURE,
    SFX_DIR,
    STORIES_DIR,
)
from app.data.story_loader import Story, load_stories
from app.game.manager import GameSession
from app.game.state import GameState
from app.llm.client import JudgeResult, LLMEngine

UNICODE_ESCAPE_PATTERN = re.compile(r"\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}")
FONT_SCALE = float(os.getenv("TS_FONT_SCALE", "1.0"))
BASE_FONT_SIZE = max(24, int(42 * FONT_SCALE))
STATUS_FONT_SIZE = max(20, int(34 * FONT_SCALE))
TITLE_FONT_SIZE = max(32, int(58 * FONT_SCALE))
UI_SCALE = 1.0


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
        self.geometry("1200x760")
        self.minsize(980, 640)

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
        available_families = {name.lower() for name in tkfont.families(self)}
        family = "helvetica" if "helvetica" in available_families else "fixed"
        self.base_font = ctk.CTkFont(family=family, size=BASE_FONT_SIZE)
        self.status_font = ctk.CTkFont(family=family, size=STATUS_FONT_SIZE)
        self.title_font = ctk.CTkFont(family=family, size=TITLE_FONT_SIZE, weight="bold")
        self._font_env_warning_shown = False

        self._build_layout()
        self._load_boot_sequence()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_panel = ctk.CTkFrame(self, corner_radius=0)
        self.main_panel.grid(row=0, column=0, sticky="nsew")
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(1, weight=1)

        self.status_label = ctk.CTkLabel(
            self.main_panel,
            text=_ui_text("Getting things ready..."),
            font=self.status_font,
            text_color="#9ca3af",
        )
        self.status_label.grid(row=0, column=0, padx=24, pady=(20, 8), sticky="w")

        self.screen_stack = ctk.CTkFrame(self.main_panel, fg_color="transparent")
        self.screen_stack.grid(row=1, column=0, padx=20, pady=8, sticky="nsew")
        self.screen_stack.grid_columnconfigure(0, weight=1)
        self.screen_stack.grid_rowconfigure(0, weight=1)

        self.menu_screen = ctk.CTkFrame(self.screen_stack)
        self.menu_screen.grid(row=0, column=0, sticky="nsew")
        self.menu_screen.grid_columnconfigure(0, weight=1)
        self.menu_screen.grid_rowconfigure(3, weight=1)

        self.menu_bubble_wrap = ctk.CTkFrame(self.menu_screen, fg_color="transparent")
        self.menu_bubble_wrap.grid(row=0, column=0, padx=24, pady=(24, 10), sticky="w")
        self.menu_bubble = ctk.CTkLabel(
            self.menu_bubble_wrap,
            text="",
            font=self.base_font,
            text_color="#e5e7eb",
            justify="left",
            wraplength=740,
            fg_color="#1f2937",
            corner_radius=16,
            padx=16,
            pady=12,
        )
        self.menu_bubble.grid(row=0, column=0, sticky="w")

        self.menu_action_button = ctk.CTkButton(
            self.menu_screen,
            text=_ui_text("Nice to meet you"),
            command=self._go_to_story_layer,
            font=self.base_font,
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

        self.game_screen = ctk.CTkFrame(self.screen_stack)
        self.game_screen.grid(row=0, column=0, sticky="nsew")
        self.game_screen.grid_columnconfigure(0, weight=1)
        self.game_screen.grid_rowconfigure(0, weight=1)

        self.chat_stream = ctk.CTkScrollableFrame(self.game_screen)
        self.chat_stream.grid(row=0, column=0, padx=12, pady=(8, 6), sticky="nsew")
        self.chat_stream.grid_columnconfigure(0, weight=1)

        self.thinking_label = ctk.CTkLabel(self.game_screen, text="", font=self.status_font, text_color="#60a5fa")
        self.thinking_label.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="w")

        self.action_row = ctk.CTkFrame(self.game_screen, fg_color="transparent")
        self.action_row.grid(row=2, column=0, padx=16, pady=(0, 16), sticky="ew")
        self.action_row.grid_columnconfigure(0, weight=1)

        self.question_entry = ctk.CTkEntry(
            self.action_row,
            placeholder_text=_ui_text("Ask anything to uncover the truth..."),
            font=self.base_font,
        )
        self.question_entry.grid(row=0, column=0, padx=(0, 8), sticky="ew")
        self.question_entry.bind("<Return>", lambda _event: self.on_ask_question())

        self.ask_button = ctk.CTkButton(
            self.action_row,
            text=_ui_text("Send"),
            width=110,
            command=self.on_ask_question,
            font=self.base_font,
        )
        self.ask_button.grid(row=0, column=1, padx=(0, 8))

        self.guess_button = ctk.CTkButton(
            self.action_row,
            text=_ui_text("Final Guess"),
            width=170,
            command=self.on_submit_guess,
            font=self.base_font,
        )
        self.guess_button.grid(row=0, column=2, padx=(0, 8))

        self.back_to_menu_button = ctk.CTkButton(
            self.action_row,
            text=_ui_text("Back to Story Menu"),
            command=self.on_reset,
            font=self.base_font,
        )
        self.back_to_menu_button.grid(row=0, column=3)
        self.back_to_menu_button.grid_remove()

        self.boot_progress = ctk.CTkProgressBar(self.main_panel, mode="indeterminate")
        self.boot_progress.grid(row=2, column=0, padx=24, pady=(0, 18), sticky="ew")
        self.boot_progress.start()
        self._show_menu_layer_one()

    def _load_boot_sequence(self) -> None:
        self.status_label.configure(text=_ui_text("Loading stories and sounds..."))
        self.after(200, self._boot_async)

    def _boot_async(self) -> None:
        def worker() -> None:
            self.stories = load_stories(STORIES_DIR)
            try:
                self.sounds.initialize()
            except pygame.error:
                pass
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
        self._warn_if_font_environment_is_limited()

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

    def _render_story_buttons(self) -> None:
        for widget in self.story_list_frame.winfo_children():
            widget.destroy()

        for index, story in enumerate(self.stories):
            button = ctk.CTkButton(
                self.story_list_frame,
                text=_ui_text(story.title),
                anchor="w",
                font=self.base_font,
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

    def _go_to_story_layer(self) -> None:
        self.sounds.play("click")
        self._show_menu_layer_two(first_prompt=True)

    def _show_menu_layer_two(self, first_prompt: bool = False) -> None:
        self._menu_layer = 2
        self.menu_screen.tkraise()
        self.menu_action_button.grid_remove()
        self.story_title_label.grid()
        self.story_list_frame.grid()
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
        self.question_entry.configure(state="normal")
        self.ask_button.configure(state="normal")
        self.guess_button.configure(state="normal")

    def _select_story_and_start(self, index: int) -> None:
        self.selected_story_index = index
        self.sounds.play("click")
        self.on_start_story()

    def on_start_story(self) -> None:
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
        self.sounds.play("click")

    def on_reset(self) -> None:
        self.session.reset()
        self._story_epoch += 1
        self._set_thinking(False)
        self.question_entry.delete(0, tk.END)
        self.status_label.configure(text=_ui_text("New round ready"))
        self._show_menu_layer_two(first_prompt=False)
        self.sounds.play("click")

    def on_ask_question(self) -> None:
        if not self.session.can_ask():
            messagebox.showinfo(_ui_text("Notice"), _ui_text("Please start a story first."))
            return
        question = self.question_entry.get().strip()
        if not question:
            return

        self.question_entry.delete(0, tk.END)
        self._append_bubble("You", question, role="user")
        self._set_thinking(True)
        self.sounds.play("thinking")
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
        self._set_thinking(False)
        self.sounds.play("reply")

    def on_submit_guess(self) -> None:
        if self.session.story is None:
            messagebox.showinfo(_ui_text("Notice"), _ui_text("Please start a story first."))
            return
        if self.session.state != GameState.QUESTIONING:
            messagebox.showinfo(
                _ui_text("Notice"),
                _ui_text("You can submit a final theory only while a story is active."),
            )
            return

        self.session.to_guessing()
        guess = self._prompt_final_guess()
        if not guess:
            self.session.state = GameState.QUESTIONING
            return

        self._append_bubble("You", f"Final guess: {guess}", role="user")
        self._set_thinking(True)
        self.sounds.play("thinking")
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
        verdict = _ui_text("Correct!") if result.hit else _ui_text("Not quite.")
        self._append_bubble("Judge", f"{verdict} (match score {result.score}/100) {result.comment}", role="agent")
        self._append_bubble("Soupy", f"Here is the full story: {full_story}", role="agent")
        if result.hit:
            self.status_label.configure(text=_ui_text("Amazing! You solved it."))
            self.session.state = GameState.IDLE
            self.sounds.play("success")
        else:
            self.status_label.configure(text=_ui_text("Nice try. Full story revealed."))
            self.session.state = GameState.IDLE
            self.sounds.play("fail")
        self._append_bubble("Soupy", "Which one would you like to play next? Click Back to Story Menu to continue.", role="agent")
        self.question_entry.configure(state="disabled")
        self.ask_button.configure(state="disabled")
        self.guess_button.configure(state="disabled")
        self.back_to_menu_button.grid()
        self._set_thinking(False)

    def _prompt_final_guess(self) -> str | None:
        dialog = ctk.CTkToplevel(self)
        dialog.title(_ui_text("Final Theory"))
        dialog.geometry("920x560")
        dialog.minsize(760, 460)
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
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        guess_box = ctk.CTkTextbox(dialog, wrap="word", font=self.base_font)
        guess_box.grid(row=1, column=0, padx=20, pady=(0, 12), sticky="nsew")
        guess_box.focus_set()

        button_row = ctk.CTkFrame(dialog, fg_color="transparent")
        button_row.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="e")

        result: dict[str, str | None] = {"value": None}

        def submit() -> None:
            value = guess_box.get("1.0", "end").strip()
            if value:
                result["value"] = value
            dialog.destroy()

        def cancel() -> None:
            dialog.destroy()

        ctk.CTkButton(button_row, text=_ui_text("Cancel"), command=cancel, font=self.base_font).pack(
            side="right", padx=(10, 0)
        )
        ctk.CTkButton(button_row, text=_ui_text("Submit"), command=submit, font=self.base_font).pack(side="right")
        dialog.bind("<Escape>", lambda _event: cancel())
        dialog.bind("<Control-Return>", lambda _event: submit())
        dialog.protocol("WM_DELETE_WINDOW", cancel)
        self.wait_window(dialog)
        return result["value"]

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
            self.session.state = GameState.QUESTIONING

    def _clear_chat_bubbles(self) -> None:
        for widget in self.chat_stream.winfo_children():
            widget.destroy()

    def _append_bubble(self, speaker: str, text: str, role: str) -> None:
        is_user = role == "user"
        if is_user:
            row_frame = ctk.CTkFrame(self.chat_stream, fg_color="transparent")
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid(sticky="ew", padx=4, pady=6)
            bubble = ctk.CTkFrame(row_frame, fg_color="#2563eb", corner_radius=16)
            bubble.grid(row=0, column=1, sticky="e", padx=(130, 0))
            text_color = "#ffffff"
        elif role == "system":
            row_frame = ctk.CTkFrame(self.chat_stream, fg_color="transparent")
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid(sticky="ew", padx=4, pady=6)
            bubble = ctk.CTkFrame(row_frame, fg_color="#7c3aed", corner_radius=16)
            bubble.grid(row=0, column=0, sticky="w", padx=(0, 130))
            text_color = "#f5f3ff"
        else:
            row_frame = ctk.CTkFrame(self.chat_stream, fg_color="transparent")
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid(sticky="ew", padx=4, pady=6)
            bubble = ctk.CTkFrame(row_frame, fg_color="#1f2937", corner_radius=16)
            bubble.grid(row=0, column=0, sticky="w", padx=(0, 130))
            text_color = "#e5e7eb"

        ctk.CTkLabel(
            bubble,
            text=_ui_text(f"{speaker}\n{text}"),
            justify="left",
            anchor="w",
            wraplength=760,
            text_color=text_color,
            font=self.base_font,
        ).pack(padx=14, pady=10, fill="both")

        canvas = getattr(self.chat_stream, "_parent_canvas", None)
        if canvas is not None:
            self.after(20, lambda: canvas.yview_moveto(1.0))
