# SPbU Timetable to ICS

Небольшой генератор подписного календаря из расписания СПбГУ.

Он загружает расписание группы с `timetable.spbu.ru`, оставляет выбранные элективы и факультативы, исключает отменённые занятия и создаёт `docs/schedule.ics`. GitHub Actions обновляет файл каждый час.

## Как настроить под себя

### 1. Сделайте Fork

Нажмите **Fork** в правом верхнем углу страницы репозитория и создайте свою копию проекта.

### 2. Клонируйте свой Fork

```bash
git clone https://github.com/ВАШ-USERNAME/spbu_timetable_to_ics.git
cd spbu_timetable_to_ics
```

Нужен Python 3.11 или новее.

Создайте окружение и установите зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

На Windows вместо команды активации:

```powershell
.venv\Scripts\activate
```

### 3. Запустите настройку

```bash
python setup.py
```

Откройте `timetable.spbu.ru`, найдите свою группу и вставьте в программу полную ссылку на её расписание.

Например:

```text
https://timetable.spbu.ru/GSOM/StudentGroupEvents/Primary/474266
```

Программа сама определит ID и подразделение группы, загрузит расписание и предложит выбрать найденные элективы и факультативы.

Настройки сохранятся в `config.json`.

### 4. Проверьте календарь

```bash
python generate_calendar.py
```

Готовый файл появится здесь:

```text
docs/schedule.ics
```

### 5. Отправьте настройки в свой Fork

```bash
git add .
git commit -m "Configure my timetable"
git push
```

После этого GitHub Actions будет пересобирать календарь каждый час.

Если Action не может записать обновлённый ICS, откройте в своём Fork:

**Settings → Actions → General → Workflow permissions → Read and write permissions**

### 6. Опубликуйте календарь

Откройте:

**Settings → Pages**

В разделе **Build and deployment** выберите:

- **Source:** Deploy from a branch
- **Branch:** main
- **Folder:** /docs

После публикации адрес будет иметь вид:

```text
https://ВАШ-USERNAME.github.io/spbu_timetable_to_ics/schedule.ics
```

Используйте именно адрес своего Fork. Его можно добавить в календарное приложение как подписной интернет-календарь. При последующих обновлениях расписания ссылка останется той же.

## Что учитывается

- обязательные занятия добавляются автоматически;
- из элективов добавляются только выбранные при настройке;
- из факультативов добавляются только выбранные при настройке;
- занятия с официальным маркером `cancelled` на странице СПбГУ не попадают в ICS;
- расписание запрашивается на русском языке;
- календарь строится на несколько месяцев вперёд — период задаётся во время настройки.

## Повторная настройка

Если нужно сменить группу, элективы или факультативы:

```bash
python setup.py
python generate_calendar.py
git add .
git commit -m "Update timetable settings"
git push
```

## Структура

```text
.
├── .github/workflows/update-calendar.yml
├── docs/schedule.ics
├── src/spbu_calendar/
│   ├── api.py
│   ├── calendar.py
│   ├── config.py
│   └── models.py
├── tests/test_calendar.py
├── config.example.json
├── config.json
├── generate_calendar.py
├── requirements.txt
└── setup.py
```

## Источник данных

Расписание берётся с `timetable.spbu.ru`.

Проект не является официальным сервисом Санкт-Петербургского государственного университета.
