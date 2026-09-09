from __future__ import annotations

import re
from datetime import date, datetime, time
from typing import Any, Iterable
from urllib.parse import quote, urljoin

import requests

from .models import Group, Lesson


API_BASE = "https://timetable.spbu.ru/api/v1/"
GROUP_URL_RE = re.compile(
    r"/StudentGroupEvents/(?:Primary|Secondary)/(?P<id>\d+)",
    re.IGNORECASE,
)


class TimetableError(RuntimeError):
    pass


def value_of(obj: dict[str, Any], *names: str, default: Any = None) -> Any:
    if not isinstance(obj, dict):
        return default

    lowered = {str(key).casefold(): value for key, value in obj.items()}
    for name in names:
        if name in obj:
            return obj[name]
        key = name.casefold()
        if key in lowered:
            return lowered[key]
    return default


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split())


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    match = re.fullmatch(r"/Date\((-?\d+)(?:[+-]\d+)?\)/", text)
    if match:
        try:
            return datetime.fromtimestamp(int(match.group(1)) / 1000)
        except (ValueError, OSError, OverflowError):
            return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass

    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue

    return None


def iter_event_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        has_subject = value_of(value, "Subject") is not None
        has_start = value_of(value, "Start") is not None
        has_end = value_of(value, "End") is not None

        if has_subject and has_start and has_end:
            yield value
            return

        for child in value.values():
            yield from iter_event_dicts(child)

    elif isinstance(value, list):
        for child in value:
            yield from iter_event_dicts(child)


def iter_group_dicts(
    value: Any,
    division: str = "",
    program: str = "",
) -> Iterable[Group]:
    if isinstance(value, list):
        for item in value:
            yield from iter_group_dicts(item, division, program)
        return

    if not isinstance(value, dict):
        return

    current_division = clean_text(
        value_of(
            value,
            "StudyDivisionName",
            "DivisionName",
            "Division",
            default=division,
        )
    ) or division

    current_program = clean_text(
        value_of(
            value,
            "StudyProgramName",
            "ProgramName",
            "ProgrammeName",
            "Program",
            default=program,
        )
    ) or program

    raw_id = value_of(
        value,
        "StudentGroupId",
        "GroupId",
        "StudentGroupOid",
    )
    name = clean_text(
        value_of(
            value,
            "StudentGroupName",
            "GroupName",
            default="",
        )
    )

    if raw_id is not None and name:
        try:
            yield Group(
                id=int(raw_id),
                name=name,
                program=current_program,
                division=current_division,
            )
        except (TypeError, ValueError):
            pass

    for child in value.values():
        if isinstance(child, (dict, list)):
            yield from iter_group_dicts(
                child,
                current_division,
                current_program,
            )


class TimetableClient:
    def __init__(self, timeout: int = 45) -> None:
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": "spbu-calendar/1.0",
            }
        )

    def _json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        url = urljoin(API_BASE, path.lstrip("/"))
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()

        try:
            return response.json()
        except ValueError as exc:
            raise TimetableError(f"Некорректный ответ timetable.spbu.ru: {url}") from exc

    def lessons(self, group_id: int, start: date, end: date) -> list[Lesson]:
        start_text = datetime.combine(start, time.min).strftime("%Y%m%d%H%M")
        end_text = datetime.combine(end, time.max).strftime("%Y%m%d%H%M")

        data = self._json(
            f"groups/{group_id}/events/{start_text}/{end_text}",
            params={"timetable": "Primary"},
        )

        lessons: list[Lesson] = []
        seen: set[tuple] = set()

        for raw in iter_event_dicts(data):
            lesson = self._lesson(raw)
            if lesson is None:
                continue

            key = (
                lesson.source_id,
                lesson.subject,
                lesson.start,
                lesson.end,
                lesson.location,
                lesson.educator,
            )
            if key in seen:
                continue

            seen.add(key)
            lessons.append(lesson)

        return sorted(lessons, key=lambda item: (item.start, item.subject.casefold()))

    def _lesson(self, raw: dict[str, Any]) -> Lesson | None:
        subject = clean_text(value_of(raw, "Subject", default=""))
        start = parse_datetime(value_of(raw, "Start"))
        end = parse_datetime(value_of(raw, "End"))

        if not subject or not start or not end:
            return None

        subject_key = subject.casefold()

        elective = bool(value_of(raw, "IsElective", default=False))
        if subject_key.startswith(("elective.", "электив")):
            elective = True

        # In the current GSOM timetable facultatives are marked in Subject
        # as "Facultative. ..."; there is no stable public IsFacultative flag.
        facultative = subject_key.startswith(("facultative.", "факультатив"))

        location = clean_text(
            value_of(
                raw,
                "LocationsDisplayText",
                "LocationDisplayText",
                default="",
            )
        )
        educator = clean_text(
            value_of(
                raw,
                "EducatorsDisplayText",
                "EducatorDisplayText",
                default="",
            )
        )

        source_id = clean_text(
            value_of(
                raw,
                "EventId",
                "Id",
                "Oid",
                "StudyEventsTimeTableKindCode",
                default="",
            )
        )

        return Lesson(
            source_id=source_id,
            subject=subject,
            start=start,
            end=end,
            location=location,
            educator=educator,
            cancelled=bool(value_of(raw, "IsCancelled", default=False)),
            elective=elective,
            facultative=facultative,
        )

    def groups(self) -> list[Group]:
        """
        Best-effort discovery.

        The group catalogue has changed shape across timetable.spbu.ru
        versions. We try the public catalogue endpoints and recursively
        accept several known field names. setup.py always has a URL/ID
        fallback, so a catalogue change does not block configuration.
        """
        groups: dict[int, Group] = {}

        for path in (
            "study/divisions",
            "study/divisions/programs/levels",
        ):
            try:
                data = self._json(path)
            except (requests.RequestException, TimetableError):
                continue

            for group in iter_group_dicts(data):
                groups[group.id] = group

        return sorted(
            groups.values(),
            key=lambda item: (item.name.casefold(), item.id),
        )

    @staticmethod
    def group_id_from_url(value: str) -> int | None:
        value = value.strip()
        if value.isdigit():
            return int(value)

        match = GROUP_URL_RE.search(value)
        return int(match.group("id")) if match else None
