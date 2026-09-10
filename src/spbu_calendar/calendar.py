from __future__ import annotations

import hashlib
from datetime import datetime
from zoneinfo import ZoneInfo

from icalendar import Calendar, Event

from .config import Settings
from .models import Lesson


def normalize(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").casefold().split())


def matches(subject: str, selected: list[str]) -> bool:
    subject_key = normalize(subject)
    return any(
        normalize(item) in subject_key or subject_key in normalize(item)
        for item in selected
        if item.strip()
    )


def included(lesson: Lesson, settings: Settings) -> bool:
    if lesson.cancelled:
        return False
    if lesson.facultative:
        return matches(lesson.subject, settings.facultatives)
    if lesson.elective:
        return matches(lesson.subject, settings.electives)
    return True


def make_uid(lesson: Lesson, group_id: int) -> str:
    key = (
        f"{group_id}|{lesson.start:%Y-%m-%d %H:%M}|"
        f"{normalize(lesson.subject)}"
    )
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()
    return f"{digest}@spbu-timetable-to-ics"


def build_calendar(lessons: list[Lesson], settings: Settings) -> bytes:
    timezone = ZoneInfo(settings.timezone)
    generated_at = datetime.now(timezone)

    calendar = Calendar()
    calendar.add("prodid", "-//spbu-timetable-to-ics//RU")
    calendar.add("version", "2.0")
    calendar.add("calscale", "GREGORIAN")
    calendar.add("method", "PUBLISH")
    calendar.add("X-WR-CALNAME", settings.calendar_name or f"СПбГУ — {settings.group_name}")
    calendar.add("X-WR-TIMEZONE", settings.timezone)

    for lesson in lessons:
        if not included(lesson, settings):
            continue

        start = lesson.start.replace(tzinfo=timezone) if lesson.start.tzinfo is None else lesson.start.astimezone(timezone)
        end = lesson.end.replace(tzinfo=timezone) if lesson.end.tzinfo is None else lesson.end.astimezone(timezone)

        event = Event()
        event.add("uid", make_uid(lesson, settings.group_id))
        event.add("dtstamp", generated_at)
        event.add("last-modified", generated_at)
        event.add("dtstart", start)
        event.add("dtend", end)
        event.add("summary", lesson.subject)

        if lesson.location:
            event.add("location", lesson.location)

        description = []
        if lesson.educator:
            description.append(f"Преподаватель: {lesson.educator}")
        if lesson.location:
            description.append(f"Аудитория: {lesson.location}")
        description.append("Источник: timetable.spbu.ru")
        event.add("description", "\n".join(description))

        calendar.add_component(event)

    return calendar.to_ical()
