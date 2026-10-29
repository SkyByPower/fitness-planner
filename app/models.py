from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from . import db, login_manager

# Көп–көп байланыс: бір жаттығу жоспарында көп жаттығу, бір жаттығу көп жоспарда
workout_exercises = db.Table(
    "workout_exercises",
    db.Column("workout_id", db.Integer, db.ForeignKey("workouts.id"), primary_key=True),
    db.Column("exercise_id", db.Integer, db.ForeignKey("exercises.id"), primary_key=True),
)


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), nullable=False, default="user")
    created_at = db.Column(db.DateTime, default=datetime.now)

    # Бір–көп байланыстар
    workouts = db.relationship("Workout", backref="owner", lazy="dynamic", cascade="all, delete-orphan")
    logs = db.relationship("Log", backref="user", lazy="dynamic", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == "admin"

    def __repr__(self):
        return f"<User {self.username}>"


class Exercise(db.Model):
    __tablename__ = "exercises"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    muscle_group = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    image = db.Column(db.String(255))

    logs = db.relationship("Log", backref="exercise", lazy="dynamic")

    def to_dict(self):
        return {"id": self.id, "name": self.name, "muscle_group": self.muscle_group}


class Workout(db.Model):
    __tablename__ = "workouts"

    DIFFICULTIES = [("easy", "Жеңіл"), ("medium", "Орташа"), ("hard", "Қиын")]

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    scheduled_date = db.Column(db.Date, nullable=False, default=date.today)
    duration_min = db.Column(db.Integer, nullable=False, default=45)
    difficulty = db.Column(db.String(10), nullable=False, default="medium")
    attachment = db.Column(db.String(255))  # сурет немесе PDF
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    exercises = db.relationship("Exercise", secondary=workout_exercises, backref="workouts")
    logs = db.relationship("Log", backref="workout", lazy="dynamic", cascade="all, delete-orphan")

    @property
    def difficulty_label(self):
        return dict(self.DIFFICULTIES).get(self.difficulty, self.difficulty)

    @property
    def attachment_is_pdf(self):
        return bool(self.attachment) and self.attachment.lower().endswith(".pdf")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "scheduled_date": self.scheduled_date.isoformat(),
            "duration_min": self.duration_min,
            "difficulty": self.difficulty,
            "exercises": [e.to_dict() for e in self.exercises],
            "owner": self.owner.username,
        }


class Log(db.Model):
    __tablename__ = "logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    workout_id = db.Column(db.Integer, db.ForeignKey("workouts.id"), nullable=False)
    exercise_id = db.Column(db.Integer, db.ForeignKey("exercises.id"))
    date = db.Column(db.Date, nullable=False, default=date.today)
    sets = db.Column(db.Integer)
    reps = db.Column(db.Integer)
    weight_kg = db.Column(db.Float)
    duration_min = db.Column(db.Integer)
    notes = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "id": self.id,
            "user": self.user.username,
            "workout_id": self.workout_id,
            "workout": self.workout.title,
            "exercise_id": self.exercise_id,
            "exercise": self.exercise.name if self.exercise else None,
            "date": self.date.isoformat(),
            "sets": self.sets,
            "reps": self.reps,
            "weight_kg": self.weight_kg,
            "duration_min": self.duration_min,
            "notes": self.notes,
        }


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
