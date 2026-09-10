from datetime import datetime

from src.spbu_calendar.api import TimetableClient, parse_day
from src.spbu_calendar.calendar import included
from src.spbu_calendar.config import Settings
from src.spbu_calendar.models import Lesson


SETTINGS = Settings(
    group_id=1,
    group_name="test",
    division="TEST",
    electives=["Электив. Теория игр"],
    facultatives=["Факультатив. Французский язык"],
)


def lesson(subject, *, cancelled=False, elective=False, facultative=False):
    return Lesson(
        source_id="",
        subject=subject,
        start=datetime(2026, 9, 12, 10, 0),
        end=datetime(2026, 9, 12, 11, 30),
        cancelled=cancelled,
        elective=elective,
        facultative=facultative,
    )


def test_cancelled_is_excluded():
    assert not included(lesson("Обязательный", cancelled=True), SETTINGS)


def test_selected_elective_is_included():
    assert included(lesson("Электив. Теория игр, семинар", elective=True), SETTINGS)


def test_other_elective_is_excluded():
    assert not included(lesson("Электив. Управление искусством", elective=True), SETTINGS)


def test_selected_facultative_is_included():
    assert included(
        lesson("Факультатив. Французский язык", facultative=True),
        SETTINGS,
    )


def test_required_is_included():
    assert included(lesson("Операционный менеджмент"), SETTINGS)


def test_group_url_parsing():
    group = TimetableClient.group_from_url(
        "https://timetable.spbu.ru/GSOM/StudentGroupEvents/Primary/474266"
    )
    assert group is not None
    assert group.id == 474266
    assert group.division == "GSOM"


def test_parse_russian_day():
    from datetime import date
    assert parse_day("суббота, 12 сентября", date(2026, 9, 7)) == date(2026, 9, 12)
