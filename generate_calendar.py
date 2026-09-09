from __future__ import annotations

from calendar import monthrange
from datetime import date

from src.spbu_calendar.api import TimetableClient
from src.spbu_calendar.calendar import build_calendar, included
from src.spbu_calendar.config import ROOT, Settings


def add_months(value: date, months: int) -> date:
    index = value.month - 1 + months
    year = value.year + index // 12
    month = index % 12 + 1
    day = min(value.day, monthrange(year, month)[1])
    return date(year, month, day)


def main() -> None:
    settings = Settings.load()
    client = TimetableClient()

    start = date.today()
    end = add_months(start, settings.months_ahead)

    print(f"Группа: {settings.group_name} ({settings.group_id})")
    print(f"Период: {start:%d.%m.%Y} — {end:%d.%m.%Y}")

    lessons = client.lessons(settings.group_id, start, end)

    cancelled = [lesson for lesson in lessons if lesson.cancelled]
    selected = [lesson for lesson in lessons if included(lesson, settings)]

    for lesson in cancelled:
        print(f"Отмена: {lesson.start:%d.%m %H:%M} — {lesson.subject}")

    output = ROOT / "docs" / "schedule.ics"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(build_calendar(lessons, settings))

    print(f"Получено: {len(lessons)}")
    print(f"Отменено: {len(cancelled)}")
    print(f"В календаре: {len(selected)}")
    print(f"Файл: {output}")


if __name__ == "__main__":
    main()
