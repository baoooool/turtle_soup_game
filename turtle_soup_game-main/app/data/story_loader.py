from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(slots=True)
class Story:
    title: str
    surface: str
    bottom: str
    source_file: Path


TAG_PATTERN = re.compile(r"^\[(Title|Surface|Bottom)\]\s*$", re.IGNORECASE)
UNICODE_ESCAPE_PATTERN = re.compile(r"\\u[0-9a-fA-F]{4}|\\U[0-9a-fA-F]{8}")


def _decode_unicode_escapes(text: str) -> str:
    if "\\" not in text:
        return text

    def replace(match: re.Match[str]) -> str:
        token = match.group(0)
        return chr(int(token[2:], 16))

    return UNICODE_ESCAPE_PATTERN.sub(replace, text)


def _parse_story_text(content: str, source_file: Path) -> Story:
    sections: dict[str, list[str]] = {"title": [], "surface": [], "bottom": []}
    current_key = ""

    for raw_line in content.splitlines():
        line = raw_line.rstrip("\n")
        match = TAG_PATTERN.match(line.strip())
        if match:
            current_key = match.group(1).lower()
            continue
        if current_key:
            sections[current_key].append(line)

    title = _decode_unicode_escapes("\n".join(sections["title"]).strip())
    surface = _decode_unicode_escapes("\n".join(sections["surface"]).strip())
    bottom = _decode_unicode_escapes("\n".join(sections["bottom"]).strip())

    if not title or not surface or not bottom:
        raise ValueError(
            f"Invalid story file: {source_file.name}. "
            "Required tags: [Title], [Surface], [Bottom]."
        )
    return Story(title=title, surface=surface, bottom=bottom, source_file=source_file)


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
