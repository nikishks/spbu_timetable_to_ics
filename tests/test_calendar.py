from datetime import datetime

from src.spbu_calendar.calendar import included
from src.spbu_calendar.config import Settings
from src.spbu_calendar.models import Lesson


SETTINGS = Settings(
    group_id=1,
    group_name="test",
    electives=["Elective. Game Theory"],
    facultatives=["Facultative. French"],
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
    assert not included(lesson("Required", cancelled=True), SETTINGS)


def test_selected_elective_is_included():
    assert included(
        lesson("Elective. Game Theory", elective=True),
        SETTINGS,
    )


def test_other_elective_is_excluded():
    assert not included(
        lesson("Elective. Art Management", elective=True),
        SETTINGS,
    )


def test_selected_facultative_is_included():
    assert included(
        lesson("Facultative. French", facultative=True),
        SETTINGS,
    )


def test_required_is_included():
    assert included(lesson("Operations Management"), SETTINGS)
