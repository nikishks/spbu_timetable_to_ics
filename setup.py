from __future__ import annotations

from datetime import date, timedelta

from src.spbu_calendar.api import Group, TimetableClient
from src.spbu_calendar.config import Settings


def choose_one(title: str, labels: list[str]) -> int:
    print(f"\n{title}")
    for number, label in enumerate(labels, 1):
        print(f"{number:>3}. {label}")

    while True:
        answer = input("Номер: ").strip()
        if answer.isdigit():
            index = int(answer) - 1
            if 0 <= index < len(labels):
                return index
        print("Введите номер из списка.")


def choose_many(title: str, values: list[str]) -> list[str]:
    if not values:
        print(f"\n{title}: ничего не найдено.")
        return []

    print(f"\n{title}")
    for number, value in enumerate(values, 1):
        print(f"{number:>3}. {value}")

    print("Номера через запятую. Enter — ничего не выбирать.")

    while True:
        answer = input("Выбор: ").strip()
        if not answer:
            return []

        try:
            indexes = sorted(
                {int(part.strip()) - 1 for part in answer.split(",")}
            )
        except ValueError:
            print("Пример: 1,3,5")
            continue

        if all(0 <= index < len(values) for index in indexes):
            return [values[index] for index in indexes]

        print("В списке нет одного из указанных номеров.")


def choose_group(client: TimetableClient) -> Group:
    print("Настройка spbu-calendar")
    print("=======================")

    groups = client.groups()

    if groups:
        while True:
            query = input(
                "\nВведите часть названия группы "
                "(Enter — вставить ссылку на расписание): "
            ).strip()

            if not query:
                break

            matches = [
                group
                for group in groups
                if query.casefold() in group.name.casefold()
                or query.casefold() in group.program.casefold()
            ]

            if not matches:
                print("Совпадений нет.")
                continue

            labels = []
            for group in matches[:100]:
                details = " · ".join(
                    value for value in (group.program, group.division) if value
                )
                labels.append(
                    f"{group.name} — {details}" if details else group.name
                )

            return matches[choose_one("Найденные группы", labels)]

    print(
        "\nАвтоматический каталог групп недоступен. "
        "Вставьте ссылку на страницу расписания."
    )

    while True:
        raw = input("Ссылка или ID группы: ").strip()
        group_id = client.group_id_from_url(raw)

        if group_id is not None:
            name = input("Название группы: ").strip() or str(group_id)
            return Group(id=group_id, name=name)

        print(
            "Пример: "
            "https://timetable.spbu.ru/GSOM/StudentGroupEvents/Primary/474266"
        )


def optional_subjects(lessons, kind: str) -> list[str]:
    names = set()

    for lesson in lessons:
        if lesson.cancelled:
            continue

        if kind == "elective" and lesson.elective and not lesson.facultative:
            names.add(lesson.subject)

        if kind == "facultative" and lesson.facultative:
            names.add(lesson.subject)

    return sorted(names, key=str.casefold)


def main() -> None:
    client = TimetableClient()
    group = choose_group(client)

    print("\nЗагружаю расписание и ищу доступные предметы...")

    today = date.today()
    lessons = client.lessons(
        group.id,
        today - timedelta(days=14),
        today + timedelta(days=180),
    )

    if not lessons:
        raise SystemExit(
            "Расписание группы не найдено. Проверьте выбранную группу."
        )

    electives = optional_subjects(lessons, "elective")
    facultatives = optional_subjects(lessons, "facultative")

    selected_electives = choose_many(
        "Элективы",
        electives,
    )
    selected_facultatives = choose_many(
        "Факультативы",
        facultatives,
    )

    raw_months = input("\nПериод календаря в месяцах [8]: ").strip()
    months_ahead = int(raw_months) if raw_months.isdigit() else 8

    settings = Settings(
        group_id=group.id,
        group_name=group.name,
        electives=selected_electives,
        facultatives=selected_facultatives,
        months_ahead=months_ahead,
        timezone="Europe/Moscow",
        calendar_name=f"СПбГУ — {group.name}",
    )
    settings.save()

    print("\nГотово.")
    print(f"Группа: {group.name} ({group.id})")
    print(
        "Элективы: "
        + (", ".join(selected_electives) if selected_electives else "не выбраны")
    )
    print(
        "Факультативы: "
        + (
            ", ".join(selected_facultatives)
            if selected_facultatives
            else "не выбраны"
        )
    )
    print("\nДля проверки запустите: python generate_calendar.py")


if __name__ == "__main__":
    main()
