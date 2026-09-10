from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from .models import Group, Lesson


BASE_URL = "https://timetable.spbu.ru"

GROUP_PATH_RE = re.compile(
    r"^/(?P<division>[^/]+)/"
    r"StudentGroupEvents/"
    r"(?:Primary|Secondary)/"
    r"(?P<id>\d+)"
    r"(?:/.*)?$",
    re.IGNORECASE,
)


RUSSIAN_MONTHS = {
    "января": 1,
    "февраля": 2,
    "марта": 3,
    "апреля": 4,
    "мая": 5,
    "июня": 6,
    "июля": 7,
    "августа": 8,
    "сентября": 9,
    "октября": 10,
    "ноября": 11,
    "декабря": 12,
}


ENGLISH_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}


def normalize(value: object) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "")
        .replace("\xa0", " ")
        .strip(),
    )


def parse_time(value: str):
    text = normalize(value)

    text = (
        text
        .replace("—", "-")
        .replace("–", "-")
    )

    parts = [
        part.strip()
        for part in text.split("-")
    ]

    if len(parts) != 2:
        return None

    try:
        start = datetime.strptime(
            parts[0],
            "%H:%M",
        ).time()

        end = datetime.strptime(
            parts[1],
            "%H:%M",
        ).time()

        return start, end

    except ValueError:
        return None


def parse_day(
    value: str,
    monday: date,
):
    text = normalize(value).casefold()

    # Русская версия:
    # "суббота, 12 сентября"
    russian_match = re.search(
        r"\b(\d{1,2})\s+"
        r"(января|февраля|марта|апреля|мая|"
        r"июня|июля|августа|сентября|октября|"
        r"ноября|декабря)\b",
        text,
    )

    if russian_match:
        day = int(
            russian_match.group(1)
        )

        month = RUSSIAN_MONTHS[
            russian_match.group(2)
        ]

        return _make_date(
            day,
            month,
            monday,
        )

    # Английская версия:
    # "Saturday, September 12"
    english_match = re.search(
        r"\b("
        r"january|february|march|april|may|"
        r"june|july|august|september|october|"
        r"november|december"
        r")\s+(\d{1,2})\b",
        text,
    )

    if english_match:
        month = ENGLISH_MONTHS[
            english_match.group(1)
        ]

        day = int(
            english_match.group(2)
        )

        return _make_date(
            day,
            month,
            monday,
        )

    # На случай формата:
    # "12 September"
    english_reverse_match = re.search(
        r"\b(\d{1,2})\s+("
        r"january|february|march|april|may|"
        r"june|july|august|september|october|"
        r"november|december"
        r")\b",
        text,
    )

    if english_reverse_match:
        day = int(
            english_reverse_match.group(1)
        )

        month = ENGLISH_MONTHS[
            english_reverse_match.group(2)
        ]

        return _make_date(
            day,
            month,
            monday,
        )

    return None


def _make_date(
    day: int,
    month: int,
    monday: date,
):
    year = monday.year

    # Неделя может пересекать Новый год.
    if (
        monday.month == 12
        and month == 1
    ):
        year += 1

    elif (
        monday.month == 1
        and month == 12
    ):
        year -= 1

    try:
        return date(
            year,
            month,
            day,
        )

    except ValueError:
        return None


def is_elective(
    subject: str,
) -> bool:
    key = normalize(
        subject
    ).casefold()

    return (
        key.startswith("электив")
        or key.startswith("elective")
    )


def is_facultative(
    subject: str,
) -> bool:
    key = normalize(
        subject
    ).casefold()

    return (
        key.startswith("факультатив")
        or key.startswith("facultative")
        or key.startswith("optional course")
    )


class TimetableClient:
    def __init__(
        self,
        timeout: int = 60,
    ):
        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(X11; Linux x86_64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/140.0 Safari/537.36"
                ),
                "Accept": (
                    "text/html,"
                    "application/xhtml+xml,"
                    "application/xml;q=0.9,"
                    "*/*;q=0.8"
                ),
                "Accept-Language": (
                    "ru-RU,ru;q=0.9,"
                    "en;q=0.8"
                ),
            }
        )

        self._set_russian_locale()

    def _set_russian_locale(
        self,
    ) -> None:
        """
        Просим сайт отдавать русскую версию.

        Эта операция необязательна:
        timetable.spbu.ru иногда возвращает
        HTTP 500 на GitHub Actions.

        В таком случае продолжаем работу.
        Парсер понимает и русский, и английский.
        """

        try:
            response = self.session.post(
                (
                    f"{BASE_URL}/"
                    "Base/"
                    "SetClientCultureCookie"
                ),
                data={
                    "clientCultureName": "ru"
                },
                timeout=self.timeout,
                allow_redirects=True,
            )

            if response.ok:
                print(
                    "Язык сайта: русский"
                )

            else:
                print(
                    "Не удалось переключить "
                    "язык сайта "
                    f"(HTTP {response.status_code}). "
                    "Продолжаю."
                )

        except requests.RequestException as error:
            print(
                "Не удалось переключить "
                "язык сайта. "
                f"Продолжаю: {error}"
            )

    @staticmethod
    def group_from_url(
        value: str,
        name: str = "",
    ) -> Group | None:
        raw = value.strip()

        if not raw:
            return None

        if "://" not in raw:
            raw = (
                "https://"
                + raw.lstrip("/")
            )

        parsed = urlparse(raw)

        hostname = (
            parsed.hostname or ""
        ).casefold()

        if hostname not in {
            "timetable.spbu.ru",
            "www.timetable.spbu.ru",
        }:
            return None

        path = parsed.path.rstrip("/")

        match = GROUP_PATH_RE.match(
            path
        )

        if match is None:
            return None

        return Group(
            id=int(
                match.group("id")
            ),
            name=(
                name
                or match.group("id")
            ),
            division=match.group(
                "division"
            ),
        )

    def _week_html(
        self,
        group: Group,
        monday: date,
    ) -> str:
        url = (
            f"{BASE_URL}/"
            f"{group.division}/"
            "StudentGroupEvents/"
            "Primary/"
            f"{group.id}/"
            f"{monday.isoformat()}"
        )

        response = self.session.get(
            url,
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.text

    def _parse_week(
        self,
        html: str,
        monday: date,
    ) -> list[Lesson]:
        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        lessons: list[Lesson] = []

        panels = soup.select(
            "div.panel.panel-default"
        )

        for panel in panels:
            heading = panel.select_one(
                ".panel-heading "
                ".panel-title"
            )

            if heading is None:
                continue

            heading_text = heading.get_text(
                " ",
                strip=True,
            )

            lesson_date = parse_day(
                heading_text,
                monday,
            )

            if lesson_date is None:
                continue

            items = panel.select(
                "li.common-list-item"
            )

            for item in items:
                time_node = item.select_one(
                    ".studyevent-datetime "
                    ".moreinfo"
                )

                subject_node = item.select_one(
                    ".studyevent-subject "
                    ".moreinfo"
                )

                if (
                    time_node is None
                    or subject_node is None
                ):
                    continue

                time_text = (
                    time_node.get_text(
                        " ",
                        strip=True,
                    )
                )

                times = parse_time(
                    time_text
                )

                if times is None:
                    continue

                start_time, end_time = times

                subject = normalize(
                    subject_node.get_text(
                        " ",
                        strip=True,
                    )
                )

                if not subject:
                    continue

                # Главный признак отмены.
                # На сайте СПбГУ отменённое
                # занятие получает CSS-класс
                # "cancelled".
                cancelled = (
                    item.select_one(
                        ".cancelled"
                    )
                    is not None
                )

                location = ""

                location_node = (
                    item.select_one(
                        ".studyevent-locations "
                        ".address-modal-btn"
                    )
                )

                if location_node is not None:
                    location = normalize(
                        location_node.get(
                            "data-address",
                            "",
                        )
                    )

                    if not location:
                        location = normalize(
                            location_node.get_text(
                                " ",
                                strip=True,
                            )
                        )

                educators: list[str] = []

                educator_nodes = item.select(
                    ".studyevent-educators a"
                )

                for node in educator_nodes:
                    educator = normalize(
                        node.get_text(
                            " ",
                            strip=True,
                        )
                    )

                    if (
                        educator
                        and educator
                        not in educators
                    ):
                        educators.append(
                            educator
                        )

                start = datetime.combine(
                    lesson_date,
                    start_time,
                )

                end = datetime.combine(
                    lesson_date,
                    end_time,
                )

                source_id = (
                    f"{lesson_date.isoformat()}|"
                    f"{start_time.isoformat()}|"
                    f"{subject}"
                )

                lesson = Lesson(
                    source_id=source_id,
                    subject=subject,
                    start=start,
                    end=end,
                    location=location,
                    educator=", ".join(
                        educators
                    ),
                    cancelled=cancelled,
                    elective=is_elective(
                        subject
                    ),
                    facultative=is_facultative(
                        subject
                    ),
                )

                lessons.append(
                    lesson
                )

                if cancelled:
                    print(
                        "Отменено: "
                        f"{start:%d.%m.%Y %H:%M}"
                        f" — {subject}"
                    )

        return lessons

    def lessons(
        self,
        group: Group,
        start: date,
        end: date,
    ) -> list[Lesson]:
        monday = (
            start
            - timedelta(
                days=start.weekday()
            )
        )

        lessons: list[Lesson] = []

        while monday <= end:
            print(
                "Загрузка недели: "
                f"{monday:%d.%m.%Y}"
            )

            html = self._week_html(
                group,
                monday,
            )

            weekly_lessons = (
                self._parse_week(
                    html,
                    monday,
                )
            )

            print(
                "Получено за неделю: "
                f"{len(weekly_lessons)}"
            )

            lessons.extend(
                weekly_lessons
            )

            monday += timedelta(
                days=7
            )

        unique: dict[
            tuple,
            Lesson,
        ] = {}

        for lesson in lessons:
            if not (
                start
                <= lesson.start.date()
                <= end
            ):
                continue

            key = (
                lesson.start,
                lesson.end,
                lesson.subject,
                lesson.location,
                lesson.educator,
            )

            unique[key] = lesson

        result = sorted(
            unique.values(),
            key=lambda lesson: (
                lesson.start,
                lesson.subject.casefold(),
            ),
        )

        return result
