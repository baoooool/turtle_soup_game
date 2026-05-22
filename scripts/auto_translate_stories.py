"""
Auto-translate stories that are missing a language version.
Uses the local LLM (Ollama) to translate English → Chinese or Chinese → English.

Usage:
    python scripts/auto_translate_stories.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from openai import OpenAI
from app.config import MODEL_BASE_URL, MODEL_API_KEY, MODEL_NAME
from app.data.story_loader import load_stories, Story

STORIES_DIR = PROJECT_ROOT / "stories"

client = OpenAI(base_url=MODEL_BASE_URL, api_key=MODEL_API_KEY)


def translate_text(text: str, target_lang: str) -> str:
    """Translate text using the local LLM."""
    if target_lang == "zh":
        system_prompt = """你是一个专业的翻译助手。请将以下海龟汤故事内容翻译成中文。
要求：
1. 保持悬疑感和故事氛围
2. 语言简洁流畅，符合中文表达习惯
3. 不要添加额外内容，只输出翻译结果"""
    else:
        system_prompt = """You are a professional translation assistant. Please translate the following Turtle Soup story content into English.
Requirements:
1. Maintain the suspenseful atmosphere
2. Use concise and natural English
3. Do not add extra content, only output the translation"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
    )
    return response.choices[0].message.content.strip()


def translate_story(story: Story) -> Story:
    """Translate missing language version of a story."""
    has_en = bool(story.title_en)
    has_zh = bool(story.title_zh)

    if has_en and has_zh:
        print(f"  ✓ {story.source_file.name}: already bilingual")
        return story

    if has_en and not has_zh:
        print(f"  → {story.source_file.name}: translating EN → ZH")
        title_zh = translate_text(story.title_en, "zh")
        surface_zh = translate_text(story.surface_en, "zh")
        bottom_zh = translate_text(story.bottom_en, "zh")
        return Story(
            title=story.title,
            surface=story.surface,
            bottom=story.bottom,
            source_file=story.source_file,
            title_en=story.title_en,
            surface_en=story.surface_en,
            bottom_en=story.bottom_en,
            title_zh=title_zh,
            surface_zh=surface_zh,
            bottom_zh=bottom_zh,
        )

    if has_zh and not has_en:
        print(f"  → {story.source_file.name}: translating ZH → EN")
        title_en = translate_text(story.title_zh, "en")
        surface_en = translate_text(story.surface_zh, "en")
        bottom_en = translate_text(story.bottom_zh, "en")
        return Story(
            title=story.title,
            surface=story.surface,
            bottom=story.bottom,
            source_file=story.source_file,
            title_en=title_en,
            surface_en=surface_en,
            bottom_en=bottom_en,
            title_zh=story.title_zh,
            surface_zh=story.surface_zh,
            bottom_zh=story.bottom_zh,
        )

    return story


def write_story_file(story: Story) -> None:
    """Write a bilingual story file."""
    lines = []

    if story.title_en:
        lines.append("[Title_en]")
        lines.append(story.title_en)
        lines.append("")
    if story.surface_en:
        lines.append("[Surface_en]")
        lines.append(story.surface_en)
        lines.append("")
    if story.bottom_en:
        lines.append("[Bottom_en]")
        lines.append(story.bottom_en)
        lines.append("")

    if story.title_zh:
        lines.append("[Title_zh]")
        lines.append(story.title_zh)
        lines.append("")
    if story.surface_zh:
        lines.append("[Surface_zh]")
        lines.append(story.surface_zh)
        lines.append("")
    if story.bottom_zh:
        lines.append("[Bottom_zh]")
        lines.append(story.bottom_zh)
        lines.append("")

    story.source_file.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    print("Loading stories...")
    stories = load_stories(STORIES_DIR)
    print(f"Found {len(stories)} stories.\n")

    # Find stories that need translation
    needs_translation = [
        s for s in stories
        if not (bool(s.title_en) and bool(s.title_zh))
    ]

    if not needs_translation:
        print("All stories are already bilingual!")
        return

    print(f"Found {len(needs_translation)} stories needing translation:\n")

    for story in needs_translation:
        translated = translate_story(story)
        if translated is not story:
            write_story_file(translated)
            print(f"  ✓ Saved: {story.source_file.name}\n")

    print("Done!")


if __name__ == "__main__":
    main()
