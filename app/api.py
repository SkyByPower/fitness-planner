"""REST API: жаттығу журналын (Log) қосу/алу/өңдеу/өшіру.

Аутентификация: браузер сессиясы немесе HTTP Basic Auth (curl/Postman үшін).
"""
from datetime import date
from functools import wraps

from flask import Blueprint, abort, g, jsonify, request
from flask_login import current_user

from . import db
from .models import Exercise, Log, User, Workout

api_bp = Blueprint("api", __name__)


def api_auth(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user.is_authenticated:
            g.user = current_user._get_current_object()
        else:
            auth = request.authorization
            user = User.query.filter_by(username=auth.username).first() if auth and auth.username else None
            if not user or not user.check_password(auth.password or ""):
                return jsonify(error="Аутентификация қажет"), 401, {"WWW-Authenticate": 'Basic realm="api"'}
            g.user = user
        return view(*args, **kwargs)

    return wrapped


def _own_log(log_id):
    log = db.get_or_404(Log, log_id)
    if not g.user.is_admin and log.user_id != g.user.id:
        abort(403)
    return log


def _validate_log_payload(data, partial=False):
    """Қателер тізімін және тазартылған мәндерді қайтарады."""
    errors, clean = {}, {}

    if "workout_id" in data or not partial:
        workout = db.session.get(Workout, data.get("workout_id")) if isinstance(data.get("workout_id"), int) else None
        if not workout or (not g.user.is_admin and workout.user_id != g.user.id):
            errors["workout_id"] = "Жоспар табылмады"
        else:
            clean["workout_id"] = workout.id

    if data.get("exercise_id") is not None:
        if not isinstance(data["exercise_id"], int) or not db.session.get(Exercise, data["exercise_id"]):
            errors["exercise_id"] = "Жаттығу табылмады"
        else:
            clean["exercise_id"] = data["exercise_id"]
    elif "exercise_id" in data:
        clean["exercise_id"] = None

    if "date" in data or not partial:
        try:
            clean["date"] = date.fromisoformat(data["date"]) if data.get("date") else date.today()
        except (TypeError, ValueError):
            errors["date"] = "Формат: YYYY-MM-DD"

    ranges = {"sets": (1, 50), "reps": (1, 500), "weight_kg": (0, 500), "duration_min": (1, 600)}
    for field, (lo, hi) in ranges.items():
        if field in data and data[field] is not None:
            value = data[field]
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not lo <= value <= hi:
                errors[field] = f"{lo}–{hi} аралығындағы сан"
            else:
                clean[field] = float(value) if field == "weight_kg" else int(value)
        elif field in data:
            clean[field] = None

    if "notes" in data:
        notes = data["notes"] or ""
        if not isinstance(notes, str) or len(notes) > 500:
            errors["notes"] = "Ең көбі 500 таңба"
        else:
            clean["notes"] = notes
    return errors, clean


@api_bp.get("/logs")
@api_auth
def list_logs():
    """GET /api/logs?from=2026-10-01&to=2026-10-31&workout_id=1"""
    query = Log.query if g.user.is_admin else Log.query.filter_by(user_id=g.user.id)
    try:
        if request.args.get("from"):
            query = query.filter(Log.date >= date.fromisoformat(request.args["from"]))
        if request.args.get("to"):
            query = query.filter(Log.date <= date.fromisoformat(request.args["to"]))
    except ValueError:
        return jsonify(error="Күн форматы: YYYY-MM-DD"), 400
    if request.args.get("workout_id", type=int):
        query = query.filter_by(workout_id=request.args.get("workout_id", type=int))
    logs = query.order_by(Log.date.desc(), Log.id.desc()).all()
    return jsonify(count=len(logs), logs=[lg.to_dict() for lg in logs])


@api_bp.get("/logs/<int:log_id>")
@api_auth
def get_log(log_id):
    return jsonify(_own_log(log_id).to_dict())


@api_bp.post("/logs")
@api_auth
def create_log():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="JSON дене қажет"), 400
    errors, clean = _validate_log_payload(data)
    if errors:
        return jsonify(errors=errors), 422
    log = Log(user_id=g.user.id, **clean)
    db.session.add(log)
    db.session.commit()
    return jsonify(log.to_dict()), 201


@api_bp.put("/logs/<int:log_id>")
@api_auth
def update_log(log_id):
    log = _own_log(log_id)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="JSON дене қажет"), 400
    errors, clean = _validate_log_payload(data, partial=True)
    if errors:
        return jsonify(errors=errors), 422
    for key, value in clean.items():
        setattr(log, key, value)
    db.session.commit()
    return jsonify(log.to_dict())


@api_bp.delete("/logs/<int:log_id>")
@api_auth
def delete_log(log_id):
    log = _own_log(log_id)
    db.session.delete(log)
    db.session.commit()
    return jsonify(message="Өшірілді", id=log_id)


@api_bp.get("/workouts")
@api_auth
def list_workouts():
    query = Workout.query if g.user.is_admin else Workout.query.filter_by(user_id=g.user.id)
    return jsonify([w.to_dict() for w in query.order_by(Workout.scheduled_date.desc())])
