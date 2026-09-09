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
    electives: list[str]
    facultatives: list[str]
    months_ahead: int = 8
    timezone: str = "Europe/Moscow"
    calendar_name: str = ""

    @classmethod
    def load(cls) -> "Settings":
        if not CONFIG_PATH.exists():
            raise SystemExit(
                "Файл config.json не найден. Сначала запустите: python setup.py"
            )

        raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))

        group_id = raw.get("group_id", raw.get("student_group_id"))
        if group_id is None:
            raise SystemExit("В config.json не указан group_id.")

        return cls(
            group_id=int(group_id),
            group_name=str(raw.get("group_name", "")),
            electives=list(raw.get("electives", raw.get("selected_electives", []))),
            facultatives=list(raw.get("facultatives", [])),
            months_ahead=int(raw.get("months_ahead", 8)),
            timezone=str(raw.get("timezone", "Europe/Moscow")),
            calendar_name=str(raw.get("calendar_name", "")),
        )

    def save(self) -> None:
        data = asdict(self)
        if not data["calendar_name"]:
            data["calendar_name"] = f"СПбГУ — {self.group_name}"

        CONFIG_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
