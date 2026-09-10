from __future__ import annotations

from calendar import monthrange
from datetime import date

from src.spbu_calendar.api import TimetableClient
from src.spbu_calendar.calendar import build_calendar, included
from src.spbu_calendar.config import ROOT, Settings
from src.spbu_calendar.models import Group


def add_months(value: date, months: int) -> date:
    index = value.month - 1 + months
    year = value.year + index // 12
    month = index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def main() -> None:
    settings = Settings.load()
    group = Group(settings.group_id, settings.group_name, settings.division)

    start = date.today()
    end = add_months(start, settings.months_ahead)

    print(f"Группа: {group.name}")
    print(f"Период: {start:%d.%m.%Y} — {end:%d.%m.%Y}")

    lessons = TimetableClient().lessons(group, start, end)
    selected = [lesson for lesson in lessons if included(lesson, settings)]
    cancelled = [lesson for lesson in lessons if lesson.cancelled]

    output = ROOT / "docs" / "schedule.ics"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(build_calendar(lessons, settings))

    print(f"Получено занятий: {len(lessons)}")
    print(f"Отменено: {len(cancelled)}")
    print(f"В календаре: {len(selected)}")
    print(f"Готово: {output}")


if __name__ == "__main__":
    main()
