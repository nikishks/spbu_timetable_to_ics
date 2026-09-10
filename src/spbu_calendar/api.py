from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .models import Group, Lesson


BASE_URL = "https://timetable.spbu.ru"
GROUP_PATH_RE = re.compile(
    r"^/(?P<division>[^/]+)/StudentGroupEvents/(?:Primary|Secondary)/(?P<id>\d+)(?:/.*)?$",
    re.IGNORECASE,
)


def normalize(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ").strip())


def parse_time(value: str):
    text = normalize(value).replace("—", "-").replace("–", "-")
    parts = [part.strip() for part in text.split("-")]
    if len(parts) != 2:
        return None
    try:
        return (
            datetime.strptime(parts[0], "%H:%M").time(),
            datetime.strptime(parts[1], "%H:%M").time(),
        )
    except ValueError:
        return None


def parse_day(value: str, monday: date):
    months = {
        "января": 1, "февраля": 2, "марта": 3, "апреля": 4,
        "мая": 5, "июня": 6, "июля": 7, "августа": 8,
        "сентября": 9, "октября": 10, "ноября": 11, "декабря": 12,
    }
    match = re.search(
        r"\b(\d{1,2})\s+(января|февраля|марта|апреля|мая|июня|июля|"
        r"августа|сентября|октября|ноября|декабря)\b",
        normalize(value).casefold(),
    )
    if not match:
        return None

    day = int(match.group(1))
    month = months[match.group(2)]
    year = monday.year

    if monday.month == 12 and month == 1:
        year += 1
    elif monday.month == 1 and month == 12:
        year -= 1

    try:
        return date(year, month, day)
    except ValueError:
        return None


class TimetableClient:
    def __init__(self, timeout: int = 60):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/140.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9",
        })
        self._set_russian_locale()

    def _set_russian_locale(self) -> None:
        response = self.session.post(
            f"{BASE_URL}/Base/SetClientCultureCookie",
            data={"clientCultureName": "ru"},
            timeout=self.timeout,
            allow_redirects=True,
        )
        response.raise_for_status()

    @staticmethod
    def group_from_url(value: str, name: str = "") -> Group | None:
        raw = value.strip()
        if not raw:
            return None

        if "://" not in raw:
            raw = "https://" + raw.lstrip("/")

        parsed = urlparse(raw)
        if parsed.netloc.casefold() not in {"timetable.spbu.ru", "www.timetable.spbu.ru"}:
            return None

        match = GROUP_PATH_RE.match(parsed.path.rstrip("/"))
        if not match:
            return None

        return Group(
            id=int(match.group("id")),
            name=name or match.group("id"),
            division=match.group("division"),
        )

    def _week_html(self, group: Group, monday: date) -> str:
        url = (
            f"{BASE_URL}/{group.division}/StudentGroupEvents/"
            f"Primary/{group.id}/{monday.isoformat()}"
        )
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    def _parse_week(self, html: str, monday: date) -> list[Lesson]:
        soup = BeautifulSoup(html, "html.parser")
        lessons: list[Lesson] = []

        for panel in soup.select("div.panel.panel-default"):
            heading = panel.select_one(".panel-heading .panel-title")
            if heading is None:
                continue

            lesson_date = parse_day(heading.get_text(" ", strip=True), monday)
            if lesson_date is None:
                continue

            for item in panel.select("li.common-list-item"):
                time_node = item.select_one(".studyevent-datetime .moreinfo")
                subject_node = item.select_one(".studyevent-subject .moreinfo")
                if time_node is None or subject_node is None:
                    continue

                times = parse_time(time_node.get_text(" ", strip=True))
                if times is None:
                    continue
                start_time, end_time = times

                subject = normalize(subject_node.get_text(" ", strip=True))
                if not subject:
                    continue

                location = ""
                location_node = item.select_one(".studyevent-locations .address-modal-btn")
                if location_node is not None:
                    location = normalize(location_node.get("data-address", ""))
                    if not location:
                        location = normalize(location_node.get_text(" ", strip=True))

                educators: list[str] = []
                for node in item.select(".studyevent-educators a"):
                    educator = normalize(node.get_text(" ", strip=True))
                    if educator and educator not in educators:
                        educators.append(educator)

                subject_key = subject.casefold()
                start = datetime.combine(lesson_date, start_time)
                end = datetime.combine(lesson_date, end_time)

                lessons.append(Lesson(
                    source_id=f"{lesson_date.isoformat()}|{start_time.isoformat()}|{subject}",
                    subject=subject,
                    start=start,
                    end=end,
                    location=location,
                    educator=", ".join(educators),
                    cancelled=item.select_one(".cancelled") is not None,
                    elective=subject_key.startswith("электив"),
                    facultative=subject_key.startswith("факультатив"),
                ))

        return lessons

    def lessons(self, group: Group, start: date, end: date) -> list[Lesson]:
        monday = start - timedelta(days=start.weekday())
        lessons: list[Lesson] = []

        while monday <= end:
            print(f"Загрузка недели: {monday:%d.%m.%Y}")
            weekly = self._parse_week(self._week_html(group, monday), monday)
            print(f"Получено за неделю: {len(weekly)}")
            lessons.extend(weekly)
            monday += timedelta(days=7)

        unique: dict[tuple, Lesson] = {}
        for lesson in lessons:
            if not start <= lesson.start.date() <= end:
                continue
            key = (lesson.start, lesson.end, lesson.subject, lesson.location, lesson.educator)
            unique[key] = lesson

        return sorted(unique.values(), key=lambda lesson: (lesson.start, lesson.subject.casefold()))
