from dataclasses import dataclass
from pathlib import Path
import re

from app.config import LANGUAGE


@dataclass(slots=True)
class Story:
    title: str
    surface: str
    bottom: str
    source_file: Path
    title_en: str = ""
    surface_en: str = ""
    bottom_en: str = ""
    title_zh: str = ""
    surface_zh: str = ""
    bottom_zh: str = ""

    def get_localized(self, lang: str) -> "Story":
        """Return a Story with title/surface/bottom in the requested language."""
        if lang == "zh":
            return Story(
                title=self.title_zh or self.title_en,
                surface=self.surface_zh or self.surface_en,
                bottom=self.bottom_zh or self.bottom_en,
                source_file=self.source_file,
            )
        return Story(
            title=self.title_en or self.title_zh,
            surface=self.surface_en or self.surface_zh,
            bottom=self.bottom_en or self.bottom_zh,
            source_file=self.source_file,
        )


TAG_PATTERN = re.compile(
    r"^\[(Title|Surface|Bottom)(?:_(en|zh))?\]\s*$", re.IGNORECASE
)
UNICODE_ESCAPE_PATTERN = re.compile(r"\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}")


def _decode_unicode_escapes(text: str) -> str:
    if "\\" not in text:
        return text

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        return chr(int(token[2:], 16))

    return UNICODE_ESCAPE_PATTERN.sub(replace, text)


def _parse_story_text(content: str, source_file: Path) -> Story:
    # Bilingual sections
    sections: dict[str, list[str]] = {
        "title_en": [], "surface_en": [], "bottom_en": [],
        "title_zh": [], "surface_zh": [], "bottom_zh": [],
        # Legacy fallback (no suffix = en)
        "title": [], "surface": [], "bottom": [],
    }
    current_key = ""

    for raw_line in content.splitlines():
        line = raw_line.rstrip("\n")
        match = TAG_PATTERN.match(line.strip())
        if match:
            tag = match.group(1).lower()
            suffix = match.group(2)
            if suffix:
                current_key = f"{tag}_{suffix}"
            else:
                current_key = tag  # legacy: title, surface, bottom
            continue
        if current_key:
            sections[current_key].append(line)

    # Decode
    title_en = _decode_unicode_escapes("\n".join(sections["title_en"]).strip())
    surface_en = _decode_unicode_escapes("\n".join(sections["surface_en"]).strip())
    bottom_en = _decode_unicode_escapes("\n".join(sections["bottom_en"]).strip())

    title_zh = _decode_unicode_escapes("\n".join(sections["title_zh"]).strip())
    surface_zh = _decode_unicode_escapes("\n".join(sections["surface_zh"]).strip())
    bottom_zh = _decode_unicode_escapes("\n".join(sections["bottom_zh"]).strip())

    # Legacy fallback: if no _en tags, use legacy as en
    if not title_en:
        title_en = _decode_unicode_escapes("\n".join(sections["title"]).strip())
    if not surface_en:
        surface_en = _decode_unicode_escapes("\n".join(sections["surface"]).strip())
    if not bottom_en:
        bottom_en = _decode_unicode_escapes("\n".join(sections["bottom"]).strip())

    # Default display values (will be overridden by get_localized)
    title = title_en or title_zh
    surface = surface_en or surface_zh
    bottom = bottom_en or bottom_zh

    if not title or not surface or not bottom:
        raise ValueError(
            f"Invalid story file: {source_file.name}. "
            "Required tags: [Title] / [Title_en] and [Surface] / [Surface_en] and [Bottom] / [Bottom_en]."
        )
    return Story(
        title=title, surface=surface, bottom=bottom, source_file=source_file,
        title_en=title_en, surface_en=surface_en, bottom_en=bottom_en,
        title_zh=title_zh, surface_zh=surface_zh, bottom_zh=bottom_zh,
    )


def load_stories(stories_dir: Path) -> list[Story]:
    stories: list[Story] = []
    if not stories_dir.exists():
        return stories

    for txt_file in sorted(stories_dir.glob("*.txt")):
        content = txt_file.read_text(encoding="utf-8")
        try:
            story = _parse_story_text(content, txt_file)
        except ValueError:
            continue
        stories.append(story)
    return stories
