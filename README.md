# spbu-calendar

Подписной календарь из расписания СПбГУ.

Скрипт получает занятия с `timetable.spbu.ru`, исключает отмены, оставляет выбранные элективы и факультативы и сохраняет результат в `docs/schedule.ics`.

## Установка

Нужен Python 3.11 или новее.

```bash
git clone https://github.com/nikishks/spbu-calendar.git
cd spbu-calendar

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup.py
```

На Windows:

```powershell
.venv\Scripts\activate
```

## Настройка

Запустите:

```bash
python setup.py
```

Мастер настройки:

1. предлагает найти группу по названию;
2. если каталог СПбГУ временно недоступен, принимает ссылку на страницу расписания или ID группы;
3. загружает расписание выбранной группы;
4. показывает найденные элективы;
5. показывает найденные факультативы;
6. сохраняет выбор в `config.json`.

Элективы определяются по признаку `IsElective` API и по префиксу `Elective.`.  
Факультативы в текущем расписании СПбГУ определяются по префиксу `Facultative.`.

Повторный запуск `python setup.py` просто перезапишет настройки.

## Создание календаря

```bash
python generate_calendar.py
```

Результат:

```text
docs/schedule.ics
```

Отменённые занятия не добавляются: API СПбГУ передаёт для них `IsCancelled`.

## Автообновление

GitHub Actions запускает генератор каждый час:

```text
0 * * * *
```

Также генерация запускается вручную и после изменения кода или `config.json`.

В репозитории нужно разрешить workflow записывать изменения:

`Settings → Actions → General → Workflow permissions → Read and write permissions`

## GitHub Pages

Включите публикацию папки `docs` из ветки `main`.

После этого календарь будет доступен по адресу:

```text
https://nikishks.github.io/spbu-calendar/schedule.ics
```

Этот URL можно добавить в Apple Calendar как подписной календарь.

## config.json

Пример:

```json
{
  "group_id": 474266,
  "group_name": "24.Б02-вшм",
  "electives": [
    "Elective. Game Theory"
  ],
  "facultatives": [],
  "months_ahead": 8,
  "timezone": "Europe/Moscow",
  "calendar_name": "СПбГУ — 24.Б02-вшм"
}
```

Редактировать его вручную необязательно.

## Структура

```text
.
├── .github/workflows/update-calendar.yml
├── docs/
├── src/spbu_calendar/
│   ├── api.py
│   ├── calendar.py
│   ├── config.py
│   └── models.py
├── config.json
├── generate_calendar.py
├── setup.py
└── requirements.txt
```
