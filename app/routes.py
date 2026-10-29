import calendar
from collections import defaultdict
from datetime import date, timedelta

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func, or_

from . import db
from .i18n import LANGUAGES, MONTHS, WEEKDAYS, WEEKDAYS_SHORT, get_locale
from .i18n import gettext as _
from .forms import ExerciseForm, LoginForm, LogForm, RegisterForm, RoleForm, WorkoutForm
from .models import Exercise, Log, User, Workout
from .utils import admin_required, delete_upload, save_upload

main_bp = Blueprint("main", __name__)
auth_bp = Blueprint("auth", __name__)
admin_bp = Blueprint("admin", __name__)

@main_bp.app_context_processor
def inject_helpers():
    lang = get_locale()
    return {"WEEKDAYS": WEEKDAYS[lang], "WEEKDAYS_SHORT": WEEKDAYS_SHORT[lang], "today": date.today(), "lang": lang, "LANGUAGES": LANGUAGES}


@main_bp.route("/lang/<code>")
def set_language(code):
    if code in LANGUAGES:
        session["lang"] = code
    ref = request.referrer
    if ref and ref.startswith(request.host_url):
        return redirect(ref)
    return redirect(url_for("main.index"))


def get_own_or_404(model, obj_id):
    """Объектіні қайтарады; admin емес болса — тек өзінікін."""
    obj = db.get_or_404(model, obj_id)
    if not current_user.is_admin and obj.user_id != current_user.id:
        abort(403)
    return obj


# ----------------------------- Auth -----------------------------

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data.lower(), phone=form.phone.data or None)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(_("Тіркелу сәтті өтті! Енді жүйеге кіріңіз."), "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(_("Қош келдіңіз, {name}!", name=user.username), "success")
            next_url = request.args.get("next")
            if not next_url or not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("main.dashboard")
            return redirect(next_url)
        flash(_("Пайдаланушы аты немесе құпиясөз қате."), "danger")
    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash(_("Жүйеден шықтыңыз."), "info")
    return redirect(url_for("main.index"))


# ----------------------------- Main -----------------------------

@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    week_ago = date.today() - timedelta(days=7)
    upcoming = (
        current_user.workouts.filter(Workout.scheduled_date >= date.today())
        .order_by(Workout.scheduled_date).limit(5).all()
    )
    recent_logs = current_user.logs.order_by(Log.date.desc(), Log.id.desc()).limit(5).all()

    # Соңғы 7 күндегі белсенділік (минут) — шағын диаграмма үшін
    days = [date.today() - timedelta(days=i) for i in range(6, -1, -1)]
    rows = dict(
        db.session.query(Log.date, func.coalesce(func.sum(Log.duration_min), 0))
        .filter(Log.user_id == current_user.id, Log.date >= days[0]).group_by(Log.date).all()
    )
    peak = max(rows.values(), default=0) or 1
    activity = [(d, rows.get(d, 0), round(rows.get(d, 0) / peak * 100)) for d in days]
    stats = {
        "workouts": current_user.workouts.count(),
        "logs": current_user.logs.count(),
        "week_logs": current_user.logs.filter(Log.date >= week_ago).count(),
        "minutes": db.session.query(func.coalesce(func.sum(Log.duration_min), 0))
        .filter(Log.user_id == current_user.id).scalar(),
    }
    return render_template("dashboard.html", upcoming=upcoming, recent_logs=recent_logs, stats=stats, activity=activity)


# --- Workouts: толық CRUD + іздеу, сүзгі, сорттау, пагинация ---

SORTS = {
    "date_desc": Workout.scheduled_date.desc(),
    "date_asc": Workout.scheduled_date.asc(),
    "title": Workout.title.asc(),
    "duration": Workout.duration_min.desc(),
}


@main_bp.route("/workouts")
@login_required
def workouts():
    q = request.args.get("q", "").strip()
    difficulty = request.args.get("difficulty", "")
    sort = request.args.get("sort", "date_desc")
    page = request.args.get("page", 1, type=int)

    query = Workout.query if current_user.is_admin else Workout.query.filter_by(user_id=current_user.id)
    if q:
        # SQLite кириллицада регистрді елемейді, сондықтан бірнеше нұсқамен іздейміз
        variants = {q, q.lower(), q.upper(), q.capitalize()}
        query = query.filter(or_(*(col.ilike(f"%{v}%") for v in variants for col in (Workout.title, Workout.description))))
    if difficulty in dict(Workout.DIFFICULTIES):
        query = query.filter_by(difficulty=difficulty)
    query = query.order_by(SORTS.get(sort, SORTS["date_desc"]), Workout.id.desc())

    pagination = query.paginate(page=page, per_page=current_app.config["ITEMS_PER_PAGE"], error_out=False)
    return render_template(
        "workouts/list.html", pagination=pagination, q=q, difficulty=difficulty, sort=sort,
        difficulties=Workout.DIFFICULTIES,
    )


@main_bp.route("/workouts/new", methods=["GET", "POST"])
@login_required
def workout_create():
    form = WorkoutForm()
    if form.validate_on_submit():
        workout = Workout(owner=current_user)
        db.session.add(workout)
        _fill_workout(workout, form)
        db.session.commit()
        flash(_("Жоспар қосылды."), "success")
        return redirect(url_for("main.workout_detail", workout_id=workout.id))
    return render_template("workouts/form.html", form=form, title=_("Жаңа жаттығу жоспары"))


@main_bp.route("/workouts/<int:workout_id>")
@login_required
def workout_detail(workout_id):
    workout = get_own_or_404(Workout, workout_id)
    logs = workout.logs.order_by(Log.date.desc()).all()
    return render_template("workouts/detail.html", workout=workout, logs=logs)


@main_bp.route("/workouts/<int:workout_id>/edit", methods=["GET", "POST"])
@login_required
def workout_edit(workout_id):
    workout = get_own_or_404(Workout, workout_id)
    form = WorkoutForm(obj=workout)
    if request.method == "GET":
        form.exercises.data = [e.id for e in workout.exercises]
    if form.validate_on_submit():
        _fill_workout(workout, form)
        db.session.commit()
        flash(_("Жоспар жаңартылды."), "success")
        return redirect(url_for("main.workout_detail", workout_id=workout.id))
    return render_template("workouts/form.html", form=form, title=_("Жоспарды өңдеу"), workout=workout)


@main_bp.route("/workouts/<int:workout_id>/delete", methods=["POST"])
@login_required
def workout_delete(workout_id):
    workout = get_own_or_404(Workout, workout_id)
    delete_upload(workout.attachment)
    db.session.delete(workout)
    db.session.commit()
    flash(_("Жоспар өшірілді."), "info")
    return redirect(url_for("main.workouts"))


def _fill_workout(workout, form):
    workout.title = form.title.data
    workout.description = form.description.data
    workout.scheduled_date = form.scheduled_date.data
    workout.duration_min = form.duration_min.data
    workout.difficulty = form.difficulty.data
    workout.exercises = Exercise.query.filter(Exercise.id.in_(form.exercises.data or [])).all()
    if form.attachment.data and getattr(form.attachment.data, "filename", ""):
        saved = save_upload(form.attachment.data)
        if saved:
            delete_upload(workout.attachment)
            workout.attachment = saved


# --- Exercises: каталог (көру — бәріне, өзгерту — admin) ---

@main_bp.route("/exercises")
@login_required
def exercises():
    group = request.args.get("group", "")
    query = Exercise.query
    if group:
        query = query.filter_by(muscle_group=group)
    groups = [g for (g,) in db.session.query(Exercise.muscle_group).distinct().order_by(Exercise.muscle_group)]
    return render_template("exercises/list.html", exercises=query.order_by(Exercise.name).all(), groups=groups, group=group)


@main_bp.route("/exercises/new", methods=["GET", "POST"])
@admin_required
def exercise_create():
    form = ExerciseForm()
    if form.validate_on_submit():
        ex = Exercise(name=form.name.data, muscle_group=form.muscle_group.data, description=form.description.data)
        ex.image = save_upload(form.image.data)
        db.session.add(ex)
        db.session.commit()
        flash(_("Жаттығу қосылды."), "success")
        return redirect(url_for("main.exercises"))
    return render_template("exercises/form.html", form=form, title=_("Жаңа жаттығу"))


@main_bp.route("/exercises/<int:exercise_id>/edit", methods=["GET", "POST"])
@admin_required
def exercise_edit(exercise_id):
    ex = db.get_or_404(Exercise, exercise_id)
    form = ExerciseForm(obj=ex, original_name=ex.name)
    if form.validate_on_submit():
        ex.name = form.name.data
        ex.muscle_group = form.muscle_group.data
        ex.description = form.description.data
        saved = save_upload(form.image.data)
        if saved:
            delete_upload(ex.image)
            ex.image = saved
        db.session.commit()
        flash(_("Жаттығу жаңартылды."), "success")
        return redirect(url_for("main.exercises"))
    return render_template("exercises/form.html", form=form, title=_("Жаттығуды өңдеу"), exercise=ex)


@main_bp.route("/exercises/<int:exercise_id>/delete", methods=["POST"])
@admin_required
def exercise_delete(exercise_id):
    ex = db.get_or_404(Exercise, exercise_id)
    Log.query.filter_by(exercise_id=ex.id).update({"exercise_id": None})
    delete_upload(ex.image)
    db.session.delete(ex)
    db.session.commit()
    flash(_("Жаттығу өшірілді."), "info")
    return redirect(url_for("main.exercises"))


# --- Logs: орындалған жаттығулар журналы ---

@main_bp.route("/logs")
@login_required
def logs():
    page = request.args.get("page", 1, type=int)
    query = Log.query if current_user.is_admin else current_user.logs
    pagination = query.order_by(Log.date.desc(), Log.id.desc()).paginate(
        page=page, per_page=current_app.config["ITEMS_PER_PAGE"] * 2, error_out=False
    )
    return render_template("logs/list.html", pagination=pagination)


@main_bp.route("/logs/new", methods=["GET", "POST"])
@login_required
def log_create():
    form = LogForm(current_user)
    if request.method == "GET":
        form.workout_id.data = request.args.get("workout_id", type=int)
    if not form.workout_id.choices:
        flash(_("Алдымен жаттығу жоспарын құрыңыз."), "warning")
        return redirect(url_for("main.workout_create"))
    if form.validate_on_submit():
        log = Log(user=current_user)
        _fill_log(log, form)
        db.session.add(log)
        db.session.commit()
        flash(_("Жазба қосылды."), "success")
        return redirect(url_for("main.logs"))
    return render_template("logs/form.html", form=form, title=_("Жаңа жазба"))


@main_bp.route("/logs/<int:log_id>/edit", methods=["GET", "POST"])
@login_required
def log_edit(log_id):
    log = get_own_or_404(Log, log_id)
    form = LogForm(current_user, obj=log)
    if request.method == "GET":
        form.exercise_id.data = log.exercise_id or 0
    if form.validate_on_submit():
        _fill_log(log, form)
        db.session.commit()
        flash(_("Жазба жаңартылды."), "success")
        return redirect(url_for("main.logs"))
    return render_template("logs/form.html", form=form, title=_("Жазбаны өңдеу"))


@main_bp.route("/logs/<int:log_id>/delete", methods=["POST"])
@login_required
def log_delete(log_id):
    log = get_own_or_404(Log, log_id)
    db.session.delete(log)
    db.session.commit()
    flash(_("Жазба өшірілді."), "info")
    return redirect(request.referrer or url_for("main.logs"))


def _fill_log(log, form):
    log.workout_id = form.workout_id.data
    log.exercise_id = form.exercise_id.data or None
    log.date = form.date.data
    log.sets = form.sets.data
    log.reps = form.reps.data
    log.weight_kg = form.weight_kg.data
    log.duration_min = form.duration_min.data
    log.notes = form.notes.data


# --- Күнтізбе көрінісі (тізім түрінде) ---

@main_bp.route("/calendar")
@login_required
def calendar_view():
    today = date.today()
    year = request.args.get("year", today.year, type=int)
    month = request.args.get("month", today.month, type=int)
    if not 1 <= month <= 12 or not 2000 <= year <= 2100:
        abort(404)

    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    workouts = current_user.workouts.filter(Workout.scheduled_date.between(first, last)).all()
    logs = current_user.logs.filter(Log.date.between(first, last)).all()

    days = defaultdict(lambda: {"workouts": [], "logs": []})
    for w in workouts:
        days[w.scheduled_date]["workouts"].append(w)
    for lg in logs:
        days[lg.date]["logs"].append(lg)

    show_empty = request.args.get("all") == "1"
    all_dates = [first + timedelta(days=i) for i in range(last.day)]
    entries = [(d, days.get(d, {"workouts": [], "logs": []})) for d in all_dates if show_empty or d in days]

    prev_month = (first - timedelta(days=1)).replace(day=1)
    next_month = last + timedelta(days=1)
    return render_template(
        "calendar.html", entries=entries, month_name=f"{MONTHS[get_locale()][month]} {year}",
        prev_month=prev_month, next_month=next_month, show_empty=show_empty, year=year, month=month,
    )


# ----------------------------- Admin -----------------------------

@admin_bp.route("/")
@admin_required
def panel():
    stats = {
        "users": User.query.count(),
        "workouts": Workout.query.count(),
        "exercises": Exercise.query.count(),
        "logs": Log.query.count(),
    }
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/panel.html", stats=stats, users=users, role_form=RoleForm())


@admin_bp.route("/users/<int:user_id>/role", methods=["POST"])
@admin_required
def change_role(user_id):
    user = db.get_or_404(User, user_id)
    form = RoleForm()
    if user.id == current_user.id:
        flash(_("Өз рөліңізді өзгерте алмайсыз."), "warning")
    elif form.validate_on_submit():
        user.role = form.role.data
        db.session.commit()
        flash(_("{name} рөлі: {role}", name=user.username, role=user.role), "success")
    return redirect(url_for("admin.panel"))


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def delete_user(user_id):
    user = db.get_or_404(User, user_id)
    if user.id == current_user.id:
        flash(_("Өзіңізді өшіре алмайсыз."), "warning")
    else:
        for w in user.workouts:
            delete_upload(w.attachment)
        db.session.delete(user)
        db.session.commit()
        flash(_("{name} өшірілді.", name=user.username), "info")
    return redirect(url_for("admin.panel"))
