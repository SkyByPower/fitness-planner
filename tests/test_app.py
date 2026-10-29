import base64
import io

import pytest

from app import create_app, db
from app.seed import seed_data
from config import TestConfig


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        seed_data()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, username="user", password="user123"):
    return client.post("/auth/login", data={"username": username, "password": password}, follow_redirects=True)


def basic(username="user", password="user123"):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_register_validation(client):
    r = client.post("/auth/register", data={"username": "a", "email": "bad", "phone": "123", "password": "1", "confirm": "2"})
    text = r.get_data(as_text=True)
    assert "3–50 таңба" in text and "Email дұрыс емес" in text and "+77001234567" in text


def test_register_and_login(client):
    r = client.post("/auth/register", data={"username": "new_user", "email": "n@test.kz", "password": "secret1", "confirm": "secret1"},
                    follow_redirects=True)
    assert "Тіркелу сәтті" in r.get_data(as_text=True)
    assert "Қош келдіңіз" in login(client, "new_user", "secret1").get_data(as_text=True)


def test_login_required(client):
    r = client.get("/workouts")
    assert r.status_code == 302 and "/auth/login" in r.headers["Location"]


def test_workout_crud_search_pagination(client):
    login(client)
    r = client.post("/workouts/new", data={
        "title": "Тест жоспар", "scheduled_date": "2026-10-30", "duration_min": 40, "difficulty": "easy",
        "exercises": [1, 2], "attachment": (io.BytesIO(b"%PDF-1.4"), "plan.pdf"),
    }, content_type="multipart/form-data", follow_redirects=True)
    assert "Жоспар қосылды" in r.get_data(as_text=True)
    assert "PDF ашу" in r.get_data(as_text=True)

    r = client.get("/workouts?q=Тест&difficulty=easy")
    assert "Тест жоспар" in r.get_data(as_text=True)
    assert "Аяқ күні" not in r.get_data(as_text=True)
    assert "Кеуде күні" in client.get("/workouts?q=кеуде").get_data(as_text=True)  # кириллица, кіші әріп

    assert "pagination" in client.get("/workouts").get_data(as_text=True)  # 9 жоспар > 6
    r = client.post("/workouts/10/edit", data={"title": "Өзгертілген", "scheduled_date": "2026-10-30", "duration_min": 50,
                                               "difficulty": "hard"}, follow_redirects=True)
    assert "Өзгертілген" in r.get_data(as_text=True)
    r = client.post("/workouts/10/delete", follow_redirects=True)
    assert "Жоспар өшірілді" in r.get_data(as_text=True)


def test_bad_upload_rejected(client):
    login(client)
    r = client.post("/workouts/new", data={"title": "Вирус", "scheduled_date": "2026-10-30", "duration_min": 40,
                                           "difficulty": "easy", "attachment": (io.BytesIO(b"x"), "evil.exe")},
                    content_type="multipart/form-data")
    assert "Тек сурет немесе PDF" in r.get_data(as_text=True)


def test_user_cannot_access_others_or_admin(client):
    login(client)
    assert client.get("/workouts/9").status_code == 403  # admin жоспары
    assert client.get("/admin/").status_code == 403
    assert client.get("/exercises/new").status_code == 403


def test_admin_panel(client):
    login(client, "admin", "admin123")
    assert "Админ панель" in client.get("/admin/").get_data(as_text=True)


def test_calendar_and_404(client):
    login(client)
    r = client.get("/calendar")
    assert r.status_code == 200 and "Бүгін" in r.get_data(as_text=True)
    r = client.get("/no-such-page")
    assert r.status_code == 404 and "Бет табылмады" in r.get_data(as_text=True)


def test_api_logs(client):
    assert client.get("/api/logs").status_code == 401
    r = client.get("/api/logs", headers=basic())
    assert r.status_code == 200 and r.json["count"] == 6

    r = client.post("/api/logs", json={"workout_id": 1, "exercise_id": 1, "sets": 3, "reps": 10, "weight_kg": 50}, headers=basic())
    assert r.status_code == 201
    log_id = r.json["id"]

    r = client.post("/api/logs", json={"workout_id": 9, "sets": 999}, headers=basic())
    assert r.status_code == 422 and set(r.json["errors"]) == {"workout_id", "sets"}

    r = client.put(f"/api/logs/{log_id}", json={"reps": 12}, headers=basic())
    assert r.json["reps"] == 12
    assert client.get(f"/api/logs/{log_id}", headers=basic("admin", "admin123")).status_code == 200
    assert client.delete(f"/api/logs/{log_id}", headers=basic()).status_code == 200
    assert client.get(f"/api/logs/{log_id}", headers=basic()).status_code == 404
