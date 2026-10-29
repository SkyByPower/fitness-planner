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

from .i18n import gettext as _
from .i18n import lazy_gettext as _l
from .models import MUSCLE_GROUPS, Exercise, User, Workout

ALLOWED_FILES = ["png", "jpg", "jpeg", "gif", "webp", "pdf"]
ALLOWED_IMAGES = ["png", "jpg", "jpeg", "gif", "webp"]

REQUIRED = _l("Міндетті өріс")


class MultiCheckboxField(SelectMultipleField):
    widget = ListWidget(prefix_label=False)
    option_widget = CheckboxInput()


class RegisterForm(FlaskForm):
    username = StringField(
        _l("Пайдаланушы аты"),
        validators=[
            DataRequired(message=REQUIRED),
            Length(3, 50, message=_l("3–50 таңба")),
            Regexp(r"^[A-Za-z0-9_]+$", message=_l("Тек латын әріптері, сандар және _")),
        ],
    )
    email = StringField("Email", validators=[DataRequired(message=REQUIRED), Email(message=_l("Email дұрыс емес"))])
    phone = StringField(
        _l("Телефон"),
        validators=[Optional(), Regexp(r"^\+?7\d{10}$", message=_l("Формат: +77001234567"))],
    )
    password = PasswordField(_l("Құпиясөз"), validators=[DataRequired(message=REQUIRED), Length(6, 128, message=_l("Кемінде 6 таңба"))])
    confirm = PasswordField(_l("Құпиясөзді қайталаңыз"), validators=[EqualTo("password", message=_l("Құпиясөздер сәйкес емес"))])
    submit = SubmitField(_l("Тіркелу"))

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError(_("Бұл атау бос емес"))

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            raise ValidationError(_("Бұл email тіркелген"))


class LoginForm(FlaskForm):
    username = StringField(_l("Пайдаланушы аты"), validators=[DataRequired(message=REQUIRED)])
    password = PasswordField(_l("Құпиясөз"), validators=[DataRequired(message=REQUIRED)])
    submit = SubmitField(_l("Кіру"))


class WorkoutForm(FlaskForm):
    title = StringField(_l("Атауы"), validators=[DataRequired(message=REQUIRED), Length(3, 120, message=_l("3–120 таңба"))])
    description = TextAreaField(_l("Сипаттама"), validators=[Optional(), Length(max=2000)])
    scheduled_date = DateField(_l("Күні"), default=date.today, validators=[DataRequired(message=_l("Күнді таңдаңыз"))])
    duration_min = IntegerField(
        _l("Ұзақтығы (мин)"),
        default=45,
        validators=[DataRequired(message=REQUIRED), NumberRange(5, 300, message=_l("5–300 минут аралығы"))],
    )
    difficulty = SelectField(_l("Күрделілігі"), choices=Workout.DIFFICULTIES)
    exercises = MultiCheckboxField(_l("Жаттығулар"), coerce=int)
    attachment = FileField(_l("Файл (сурет немесе PDF)"), validators=[FileAllowed(ALLOWED_FILES, _l("Тек сурет немесе PDF"))])
    submit = SubmitField(_l("Сақтау"))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exercises.choices = [(e.id, f"{e.name} ({_(e.muscle_group)})") for e in Exercise.query.order_by(Exercise.name)]


class ExerciseForm(FlaskForm):
    name = StringField(_l("Атауы"), validators=[DataRequired(message=REQUIRED), Length(2, 100)])
    muscle_group = SelectField(_l("Бұлшықет тобы"), choices=[(g, _l(g)) for g in MUSCLE_GROUPS])
    description = TextAreaField(_l("Сипаттама"), validators=[Optional(), Length(max=2000)])
    image = FileField(_l("Сурет"), validators=[FileAllowed(ALLOWED_IMAGES, _l("Тек сурет файлдары"))])
    submit = SubmitField(_l("Сақтау"))

    def __init__(self, *args, original_name=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_name = original_name

    def validate_name(self, field):
        if field.data != self.original_name and Exercise.query.filter_by(name=field.data).first():
            raise ValidationError(_("Мұндай жаттығу бар"))


class LogForm(FlaskForm):
    workout_id = SelectField(_l("Жоспар"), coerce=int, validators=[DataRequired(message=_l("Жоспарды таңдаңыз"))])
    exercise_id = SelectField(_l("Жаттығу"), coerce=int)
    date = DateField(_l("Күні"), default=date.today, validators=[DataRequired(message=_l("Күнді таңдаңыз"))])
    sets = IntegerField(_l("Сет"), validators=[Optional(), NumberRange(1, 50, message="1–50")])
    reps = IntegerField(_l("Қайталау"), validators=[Optional(), NumberRange(1, 500, message="1–500")])
    weight_kg = FloatField(_l("Салмақ (кг)"), validators=[Optional(), NumberRange(0, 500, message=_l("0–500 кг"))])
    duration_min = IntegerField(_l("Ұзақтығы (мин)"), validators=[Optional(), NumberRange(1, 600, message="1–600")])
    notes = TextAreaField(_l("Ескертпе"), validators=[Optional(), Length(max=500)])
    submit = SubmitField(_l("Сақтау"))

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        workouts = Workout.query if user.is_admin else Workout.query.filter_by(user_id=user.id)
        self.workout_id.choices = [(w.id, f"{w.scheduled_date:%d.%m} — {w.title}") for w in workouts.order_by(Workout.scheduled_date.desc())]
        self.exercise_id.choices = [(0, _("— жоқ —"))] + [(e.id, e.name) for e in Exercise.query.order_by(Exercise.name)]


class RoleForm(FlaskForm):
    role = SelectField(_l("Рөл"), choices=[("user", "user"), ("admin", "admin")])
    submit = SubmitField(_l("Өзгерту"))
