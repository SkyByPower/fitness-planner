from datetime import date, timedelta

from . import db
from .models import Exercise, Log, User, Workout

EXERCISES = [
    ("Жатып штанга көтеру", "Кеуде", "Скамьяда жатып штанганы кеудеден жоғары итеру."),
    ("Отжимание", "Кеуде", "Қолды иық енінде қойып, денені түзу ұстау."),
    ("Турник (тартылу)", "Арқа", "Иекті турниктен асырып тартылу."),
    ("Становая тартылыс", "Арқа", "Арқаны түзу ұстап, штанганы еденнен көтеру."),
    ("Присед", "Аяқ", "Штангамен немесе өз салмағымен отырып-тұру."),
    ("Выпад", "Аяқ", "Алға қадам жасап, тізені 90° бүгу."),
    ("Иықтан итеру", "Иық", "Гантельді иық деңгейінен жоғары көтеру."),
    ("Бицепс бүгу", "Қол", "Гантельді шынтақты бүгіп көтеру."),
    ("Планка", "Іш", "Шынтаққа сүйеніп, денені түзу ұстау."),
    ("Жүгіру", "Кардио", "Орташа қарқынмен жүгіру."),
    ("Берпи", "Бүкіл дене", "Отыру, планка, отжимание, секіру."),
]


def seed_data():
    if User.query.filter_by(username="admin").first():
        return "Деректер бұрыннан бар — өткізілді."

    admin = User(username="admin", email="admin@fitness.kz", role="admin")
    admin.set_password("admin123")
    user = User(username="user", email="user@fitness.kz", phone="+77001234567")
    user.set_password("user123")
    db.session.add_all([admin, user])

    ex = {name: Exercise(name=name, muscle_group=g, description=d) for name, g, d in EXERCISES}
    db.session.add_all(ex.values())

    today = date.today()
    plans = [
        ("Кеуде күні", "Кеуде мен үшбасқа арналған күш жаттығуы", -6, 60, "hard", ["Жатып штанга көтеру", "Отжимание", "Планка"]),
        ("Арқа және бицепс", "Тартылу жаттығулары", -4, 55, "medium", ["Турник (тартылу)", "Становая тартылыс", "Бицепс бүгу"]),
        ("Аяқ күні", "Аяққа арналған базалық жаттығулар", -2, 70, "hard", ["Присед", "Выпад"]),
        ("Жеңіл кардио", "Қалпына келу күні", -1, 30, "easy", ["Жүгіру", "Планка"]),
        ("Иық пен қол", "Иық және қол бұлшықеттері", 1, 50, "medium", ["Иықтан итеру", "Бицепс бүгу"]),
        ("Фулбади", "Бүкіл денеге интенсивті жаттығу", 3, 45, "hard", ["Берпи", "Присед", "Отжимание"]),
        ("Таңғы жүгіру", "5 км жүгіру", 5, 35, "easy", ["Жүгіру"]),
        ("Кеуде күні #2", "Прогрессия: салмақты арттыру", 8, 60, "hard", ["Жатып штанга көтеру", "Отжимание"]),
    ]
    workouts = []
    for title, desc, offset, dur, diff, names in plans:
        w = Workout(title=title, description=desc, scheduled_date=today + timedelta(days=offset),
                    duration_min=dur, difficulty=diff, owner=user, exercises=[ex[n] for n in names])
        workouts.append(w)
    admin_plan = Workout(title="Админ жоспары", description="Тексеру үшін", scheduled_date=today,
                         duration_min=40, difficulty="medium", owner=admin, exercises=[ex["Планка"]])
    db.session.add_all(workouts + [admin_plan])

    logs = [
        Log(user=user, workout=workouts[0], exercise=ex["Жатып штанга көтеру"], date=today - timedelta(days=6), sets=4, reps=8, weight_kg=60, duration_min=20),
        Log(user=user, workout=workouts[0], exercise=ex["Отжимание"], date=today - timedelta(days=6), sets=3, reps=20, duration_min=10),
        Log(user=user, workout=workouts[1], exercise=ex["Турник (тартылу)"], date=today - timedelta(days=4), sets=4, reps=10, duration_min=15),
        Log(user=user, workout=workouts[1], exercise=ex["Бицепс бүгу"], date=today - timedelta(days=4), sets=3, reps=12, weight_kg=12, duration_min=10),
        Log(user=user, workout=workouts[2], exercise=ex["Присед"], date=today - timedelta(days=2), sets=5, reps=5, weight_kg=80, duration_min=25, notes="Жаңа рекорд!"),
        Log(user=user, workout=workouts[3], exercise=ex["Жүгіру"], date=today - timedelta(days=1), duration_min=30, notes="5 км"),
    ]
    db.session.add_all(logs)
    db.session.commit()
    return "Тест деректер қосылды: admin/admin123, user/user123"
