from __future__ import annotations

from datetime import date, timedelta

from src.spbu_calendar.api import TimetableClient
from src.spbu_calendar.config import Settings
from src.spbu_calendar.models import Group


def choose_many(title: str, values: list[str]) -> list[str]:
    if not values:
        print(f"\n{title}: ничего не найдено.")
        return []

    print(f"\n{title}:")
    for number, value in enumerate(values, 1):
        print(f"{number:>3}. {value}")

    while True:
        answer = input("Номера через запятую (Enter — ничего): ").strip()
        if not answer:
            return []
        try:
            indexes = sorted({int(part.strip()) - 1 for part in answer.split(",")})
        except ValueError:
            print("Введите номера, например: 1,3")
            continue

        if all(0 <= index < len(values) for index in indexes):
            return [values[index] for index in indexes]
        print("Один из номеров отсутствует в списке.")


def subject_names(lessons, attribute: str) -> list[str]:
    return sorted(
        {
            lesson.subject
            for lesson in lessons
            if not lesson.cancelled and getattr(lesson, attribute)
        },
        key=str.casefold,
    )


def main() -> None:
    print("Настройка календаря СПбГУ")
    print("=========================")
    print("Откройте расписание своей группы на https://timetable.spbu.ru")
    print("и вставьте полную ссылку на страницу группы.\n")

    client = TimetableClient()

    while True:
        url = input("Ссылка на группу: ").strip()
        parsed = client.group_from_url(url)
        if parsed is not None:
            break
        print("Не удалось распознать ссылку. Пример:")
        print("https://timetable.spbu.ru/GSOM/StudentGroupEvents/Primary/474266")

    name = input("Название группы: ").strip() or str(parsed.id)
    group = Group(parsed.id, name, parsed.division)

    print("\nЗагружаю расписание, чтобы найти элективы и факультативы...")
    today = date.today()
    lessons = client.lessons(
        group,
        today - timedelta(days=14),
        today + timedelta(days=180),
    )
    if not lessons:
        raise SystemExit("Расписание не найдено. Проверьте ссылку.")

    electives = choose_many("Элективы", subject_names(lessons, "elective"))
    facultatives = choose_many("Факультативы", subject_names(lessons, "facultative"))

    raw_months = input("\nМесяцев вперёд [8]: ").strip()
    months_ahead = int(raw_months) if raw_months.isdigit() and int(raw_months) > 0 else 8

    Settings(
        group_id=group.id,
        group_name=group.name,
        division=group.division,
        electives=electives,
        facultatives=facultatives,
        months_ahead=months_ahead,
        timezone="Europe/Moscow",
        calendar_name=f"СПбГУ — {group.name}",
    ).save()

    print("\nГотово. Создан config.json.")
    print("Теперь запустите: python generate_calendar.py")


if __name__ == "__main__":
    main()
