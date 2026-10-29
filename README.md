# 🏋️ Fitness Planner — Жаттығу жоспары

**Нұсқа 9** · Flask веб-қосымшасы: жаттығу жоспарларын құру, орындалған жаттығуларды журналға жазу
және оларды күнтізбе (тізім) түрінде көру.

**Автор:** Иманбек

![Басты бет](screenshots/02_dashboard.jpg)

---

## Технологиялар

| | |
|---|---|
| Тіл | Python 3.10+ |
| Фреймворк | Flask 3, Blueprints |
| ORM / ДҚ | Flask-SQLAlchemy, SQLite (PostgreSQL-ге ауысуға болады), Flask-Migrate |
| Аутентификация | Flask-Login (session) |
| Формалар / валидация | Flask-WTF, WTForms, email-validator, CSRF қорғау |
| Шаблондар | Jinja2, Bootstrap 5 |
| Тест | pytest |

## Талаптардың орындалуы

| № | Талап | Қай жерде |
|---|---|---|
| 1 | Тіркелу / кіру / шығу | `/auth/register`, `/auth/login`, `/auth/logout` — `app/routes.py` |
| 2 | 2 рөл: `admin`, `user` | `User.role`; admin — барлық жоспар/журналды көреді, жаттығулар каталогын басқарады, админ панель (`/admin`), рөл өзгерту, қолданушыны өшіру |
| 3 | ≥3 модель + байланыс | `User`, `Workout`, `Exercise`, `Log` (`app/models.py`). **1–көп:** User→Workout, User→Log, Workout→Log, Exercise→Log. **Көп–көп:** Workout↔Exercise (`workout_exercises` кестесі) |
| 4 | Толық CRUD | **Workout** (қосу/көру/өңдеу/өшіру), сонымен қатар Log және Exercise |
| 5 | Іздеу + сүзгі + сорттау | `/workouts` — атауы/сипаттамасы бойынша іздеу, күрделілік сүзгісі, 4 түрлі сорттау; `/exercises` — бұлшықет тобы сүзгісі |
| 6 | Пагинация | `/workouts` (6 элемент/бет), `/logs` (12 элемент/бет) |
| 7 | Форма валидациясы | `app/forms.py`: міндетті өрістер, ұзындық (3–50, 6+ таңба), сан диапазоны (5–300 мин, 0–500 кг), email, телефон (`+7XXXXXXXXXX`), қайталанатын username/email тексеру |
| 8 | Файл жүктеу | Жоспарға сурет/PDF, жаттығуға сурет. `secure_filename` + UUID префикс, кеңейтім тексеру (`png, jpg, jpeg, gif, webp, pdf`), 5 МБ шектеу (`app/utils.py`) |
| 9 | 404 / 500 custom бет | `app/templates/errors/` (сонымен қатар 403, 413) |
| 10 | API (≥3 endpoint) | `app/api.py` — GET/POST/PUT/DELETE, төменде қараңыз |
| 11 | README | осы файл |
| ⭐ | Ерекшелік: күнтізбе | `/calendar` — айлық тізім: әр күнге жоспарлар + орындалған жазбалар, ай бойынша ауысу, бос күндерді көрсету қосқышы |

## Жоба құрылымы

```
├── app/
│   ├── __init__.py        # create_app(), қате өңдеушілер, CLI командалары
│   ├── models.py          # User, Workout, Exercise, Log
│   ├── routes.py          # Blueprints: main, auth, admin
│   ├── api.py             # REST API blueprint (/api)
│   ├── forms.py           # WTForms формалары + валидация
│   ├── utils.py           # admin_required, файл жүктеу
│   ├── seed.py            # тест деректер
│   ├── templates/         # Jinja2 шаблондары (auth, workouts, exercises, logs, admin, errors)
│   └── static/            # css/, uploads/
├── tests/test_app.py      # pytest тесттері
├── screenshots/
├── config.py
├── run.py
├── requirements.txt
├── .env.example           # .env үлгісі (.env өзі git-ке кірмейді)
└── .gitignore
```

## Орнату және іске қосу

```bash
git clone <репозиторий-сілтемесі>
cd fitness-planner

# 1. Виртуалды орта
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS:
source .venv/bin/activate

# 2. Тәуелділіктер
pip install -r requirements.txt

# 3. Құпия кілттер (.env)
copy .env.example .env      # Linux/macOS: cp .env.example .env
# .env ішінде SECRET_KEY мәнін өзгертіңіз
```

### Дерекқорды инициализациялау

```bash
flask init-db        # кестелерді құру (қайта құру үшін: flask init-db --drop)
flask seed           # тест аккаунттар + үлгі деректер
```

**Миграциялар (Flask-Migrate) арқылы** — модельдер өзгерген кезде:

```bash
flask db init                     # бір рет қана
flask db migrate -m "initial"
flask db upgrade
```

### Іске қосу

```bash
flask run            # немесе: python run.py
```

Браузерде: <http://127.0.0.1:5000>

### Тесттер

```bash
pytest -v
```

9 тест: тіркелу валидациясы, кіру, CRUD, іздеу/сүзгі/пагинация, файл тексеру, рөлдер (403), 404 беті, API.

## Тест аккаунттар

| Рөл | Логин | Құпиясөз |
|---|---|---|
| admin | `admin` | `admin123` |
| user | `user` | `user123` |

> `flask seed` командасы осы аккаунттарды және 11 жаттығу, 9 жоспар, 6 журнал жазбасын қосады.

## API

Аутентификация: браузер сессиясы **немесе** HTTP Basic Auth. Қарапайым қолданушы тек өз жазбаларын көреді, admin — барлығын.

| Әдіс | Endpoint | Сипаттама |
|---|---|---|
| GET | `/api/logs` | Журнал жазбалары. Сүзгілер: `?from=YYYY-MM-DD&to=YYYY-MM-DD&workout_id=1` |
| GET | `/api/logs/<id>` | Бір жазба |
| POST | `/api/logs` | Жазба қосу (201) |
| PUT | `/api/logs/<id>` | Жазбаны өзгерту (ішінара) |
| DELETE | `/api/logs/<id>` | Жазбаны өшіру |
| GET | `/api/workouts` | Жоспарлар тізімі жаттығуларымен |

Жауап кодтары: `200`, `201`, `400` (JSON жоқ), `401`, `403`, `404`, `422` (валидация қатесі).

**Мысалдар:**

```bash
# Журналды алу
curl -u user:user123 "http://127.0.0.1:5000/api/logs?from=2026-10-01"

# Жазба қосу
curl -u user:user123 -X POST http://127.0.0.1:5000/api/logs \
     -H "Content-Type: application/json" \
     -d '{"workout_id": 1, "exercise_id": 1, "sets": 4, "reps": 8, "weight_kg": 60, "notes": "Жақсы"}'

# Өзгерту
curl -u user:user123 -X PUT http://127.0.0.1:5000/api/logs/1 \
     -H "Content-Type: application/json" -d '{"reps": 10}'

# Өшіру
curl -u user:user123 -X DELETE http://127.0.0.1:5000/api/logs/1
```

POST денесінің өрістері: `workout_id` (міндетті, int), `exercise_id` (int), `date` (`YYYY-MM-DD`, әдепкі — бүгін),
`sets` (1–50), `reps` (1–500), `weight_kg` (0–500), `duration_min` (1–600), `notes` (≤500 таңба).

Валидация қатесінің мысалы:

```json
{ "errors": { "workout_id": "Жоспар табылмады", "sets": "1–50 аралығындағы сан" } }
```

## PostgreSQL қолдану

`pip install psycopg2-binary`, содан кейін `.env` файлында:

```
DATABASE_URL=postgresql://user:password@localhost:5432/fitness
```

## Скриншоттар

| | |
|---|---|
| **Басты бет** ![](screenshots/01_home.jpg) | **Dashboard** ![](screenshots/02_dashboard.jpg) |
| **Жоспарлар + пагинация** ![](screenshots/03_workouts_pagination.jpg) | **Іздеу / сүзгі / сорттау** ![](screenshots/04_search_filter.jpg) |
| **Жоспар формасы (файл жүктеу)** ![](screenshots/05_workout_form.jpg) | **Жоспар беті** ![](screenshots/06_workout_detail.jpg) |
| **Күнтізбе** ![](screenshots/07_calendar.jpg) | **Журнал** ![](screenshots/08_logs.jpg) |
| **Жаттығулар (admin)** ![](screenshots/09_exercises_admin.jpg) | **Админ панель** ![](screenshots/10_admin_panel.jpg) |
| **404 беті** ![](screenshots/11_error_404.jpg) | |
