from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(slots=True)
class UserProfile:
    name: str
    avatar_path: str
    total_score: int = 0


class UserManager:
    def __init__(self, storage_path: Path, *, default_bob_avatar: str) -> None:
        self.storage_path = storage_path
        self.default_bob_avatar = default_bob_avatar
        self.users: dict[str, UserProfile] = {}
        self._load()

    def _load(self) -> None:
        if self.storage_path.exists():
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
            for item in payload.get("users", []):
                name = str(item.get("name", "")).strip()
                if not name:
                    continue
                avatar_path = str(item.get("avatar_path", "")).strip()
                try:
                    total_score = int(item.get("total_score", 0))
                except (TypeError, ValueError):
                    total_score = 0
                self.users[name] = UserProfile(
                    name=name,
                    avatar_path=avatar_path,
                    total_score=max(0, total_score),
                )
        self._ensure_bob()
        self._save()

    def _save(self) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "users": [
                {
                    "name": user.name,
                    "avatar_path": user.avatar_path,
                    "total_score": user.total_score,
                }
                for user in sorted(self.users.values(), key=lambda u: u.name.casefold())
            ]
        }
        self.storage_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _ensure_bob(self) -> None:
        if self._find_user_key("bob") is None:
            self.users["bob"] = UserProfile(name="bob", avatar_path=self.default_bob_avatar, total_score=0)

    def _find_user_key(self, name: str) -> str | None:
        target = name.casefold()
        for key in self.users:
            if key.casefold() == target:
                return key
        return None

    def list_users(self) -> list[UserProfile]:
        return sorted(self.users.values(), key=lambda u: u.name.casefold())

    def leaderboard(self) -> list[UserProfile]:
        return sorted(
            self.users.values(),
            key=lambda u: (-u.total_score, u.name.casefold()),
        )

    def get_user(self, name: str) -> UserProfile | None:
        key = self._find_user_key(name)
        if key is None:
            return None
        return self.users[key]

    def add_user(self, name: str, avatar_path: str) -> UserProfile:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("User name cannot be empty.")
        if self._find_user_key(clean_name) is not None:
            raise ValueError("User name already exists.")
        profile = UserProfile(name=clean_name, avatar_path=avatar_path, total_score=0)
        self.users[clean_name] = profile
        self._save()
        return profile

    def delete_user(self, name: str) -> None:
        key = self._find_user_key(name)
        if key is None:
            raise KeyError("User not found.")
        if key.casefold() == "bob":
            raise ValueError("Bob cannot be deleted.")
        del self.users[key]
        self._save()

    def add_score(self, name: str, score: int) -> None:
        key = self._find_user_key(name)
        if key is None:
            raise KeyError("User not found.")
        try:
            delta = int(score)
        except (TypeError, ValueError):
            delta = 0
        self.users[key].total_score = max(0, self.users[key].total_score + delta)
        self._save()
