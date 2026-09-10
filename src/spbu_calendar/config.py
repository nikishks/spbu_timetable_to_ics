from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config.json"


@dataclass
class Settings:
    group_id: int
    group_name: str
    division: str
    electives: list[str]
    facultatives: list[str]
    months_ahead: int = 8
    timezone: str = "Europe/Moscow"
    calendar_name: str = ""

    @classmethod
    def load(cls) -> "Settings":
        if not CONFIG_PATH.exists():
            raise SystemExit("config.json не найден. Сначала запустите: python setup.py")

        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        required = ("group_id", "group_name", "division")
        missing = [key for key in required if not data.get(key)]
        if missing:
            raise SystemExit(
                "В config.json отсутствуют поля: " + ", ".join(missing)
                + ". Запустите python setup.py заново."
            )

        return cls(
            group_id=int(data["group_id"]),
            group_name=str(data["group_name"]),
            division=str(data["division"]),
            electives=list(data.get("electives", [])),
            facultatives=list(data.get("facultatives", [])),
            months_ahead=int(data.get("months_ahead", 8)),
            timezone=str(data.get("timezone", "Europe/Moscow")),
            calendar_name=str(data.get("calendar_name", "")),
        )

    def save(self) -> None:
        data = asdict(self)
        if not data["calendar_name"]:
            data["calendar_name"] = f"СПбГУ — {self.group_name}"

        CONFIG_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
