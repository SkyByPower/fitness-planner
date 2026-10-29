from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import (
    DateField,
    FloatField,
    IntegerField,
    PasswordField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    Length,
    NumberRange,
    Optional,
    Regexp,
    ValidationError,
)
from wtforms.widgets import CheckboxInput, ListWidget

from .models import Exercise, User, Workout

ALLOWED_FILES = ["png", "jpg", "jpeg", "gif", "webp", "pdf"]
ALLOWED_IMAGES = ["png", "jpg", "jpeg", "gif", "webp"]


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class RegisterForm(FlaskForm):
    username = StringField(
        "Пайдаланушы аты",
        validators=[
            DataRequired(message="Міндетті өріс"),
            Length(3, 50, message="3–50 таңба"),
            Regexp(r"^[A-Za-z0-9_]+$", message="Тек латын әріптері, сандар және _"),
        ],
    )
    email = StringField("Email", validators=[DataRequired(message="Міндетті өріс"), Email(message="Email дұрыс емес")])
    phone = StringField(
        "Телефон",
        validators=[Optional(), Regexp(r"^\+?7\d{10}$", message="Формат: +77001234567")],
    )
    password = PasswordField("Құпиясөз", validators=[DataRequired(message="Міндетті өріс"), Length(6, 128, message="Кемінде 6 таңба")])
    confirm = PasswordField("Құпиясөзді қайталаңыз", validators=[EqualTo("password", message="Құпиясөздер сәйкес емес")])
    submit = SubmitField("Тіркелу")

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("Бұл атау бос емес")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError("Бұл email тіркелген")


class LoginForm(FlaskForm):
    username = StringField("Пайдаланушы аты", validators=[DataRequired(message="Міндетті өріс")])
    password = PasswordField("Құпиясөз", validators=[DataRequired(message="Міндетті өріс")])
    submit = SubmitField("Кіру")


class WorkoutForm(FlaskForm):
    title = StringField("Атауы", validators=[DataRequired(message="Міндетті өріс"), Length(3, 120, message="3–120 таңба")])
    description = TextAreaField("Сипаттама", validators=[Optional(), Length(max=2000)])
    scheduled_date = DateField("Күні", default=date.today, validators=[DataRequired(message="Күнді таңдаңыз")])
    duration_min = IntegerField(
        "Ұзақтығы (мин)",
        default=45,
        validators=[DataRequired(message="Міндетті өріс"), NumberRange(5, 300, message="5–300 минут аралығы")],
    )
    difficulty = SelectField("Күрделілігі", choices=Workout.DIFFICULTIES)
    exercises = MultiCheckboxField("Жаттығулар", coerce=int)
    attachment = FileField("Файл (сурет немесе PDF)", validators=[FileAllowed(ALLOWED_FILES, "Тек сурет немесе PDF")])
    submit = SubmitField("Сақтау")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exercises.choices = [(e.id, f"{e.name} ({e.muscle_group})") for e in Exercise.query.order_by(Exercise.name)]


class ExerciseForm(FlaskForm):
    name = StringField("Атауы", validators=[DataRequired(message="Міндетті өріс"), Length(2, 100)])
    muscle_group = SelectField(
        "Бұлшықет тобы",
        choices=[(g, g) for g in ["Кеуде", "Арқа", "Аяқ", "Иық", "Қол", "Іш", "Кардио", "Бүкіл дене"]],
    )
    description = TextAreaField("Сипаттама", validators=[Optional(), Length(max=2000)])
    image = FileField("Сурет", validators=[FileAllowed(ALLOWED_IMAGES, "Тек сурет файлдары")])
    submit = SubmitField("Сақтау")

    def __init__(self, *args, original_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, field):
        if field.data != self.original_name and Exercise.query.filter_by(name=field.data).first():
            raise ValidationError("Мұндай жаттығу бар")


class LogForm(FlaskForm):
    workout_id = SelectField("Жоспар", coerce=int, validators=[DataRequired(message="Жоспарды таңдаңыз")])
    exercise_id = SelectField("Жаттығу", coerce=int)
    date = DateField("Күні", default=date.today, validators=[DataRequired(message="Күнді таңдаңыз")])
    sets = IntegerField("Сет", validators=[Optional(), NumberRange(1, 50, message="1–50")])
    reps = IntegerField("Қайталау", validators=[Optional(), NumberRange(1, 500, message="1–500")])
    weight_kg = FloatField("Салмақ (кг)", validators=[Optional(), NumberRange(0, 500, message="0–500 кг")])
    duration_min = IntegerField("Ұзақтығы (мин)", validators=[Optional(), NumberRange(1, 600, message="1–600")])
    notes = TextAreaField("Ескертпе", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Сақтау")

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        workouts = Workout.query if user.is_admin else Workout.query.filter_by(user_id=user.id)
        self.workout_id.choices = [(w.id, f"{w.scheduled_date:%d.%m} — {w.title}") for w in workouts.order_by(Workout.scheduled_date.desc())]
        self.exercise_id.choices = [(0, "— жоқ —")] + [(e.id, e.name) for e in Exercise.query.order_by(Exercise.name)]


class RoleForm(FlaskForm):
    role = SelectField("Рөл", choices=[("user", "user"), ("admin", "admin")])
    submit = SubmitField("Өзгерту")
