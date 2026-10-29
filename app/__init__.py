import os

import click
from flask import Flask, jsonify, render_template, request
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

from config import Config

db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Бұл бетті көру үшін жүйеге кіріңіз."
login_manager.login_message_category = "warning"


def create_app(config_class=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)
    app.json.ensure_ascii = False  # API жауабында кириллица оқылатын болсын

    from .i18n import gettext

    app.jinja_env.globals["_"] = gettext
    login_manager.localize_callback = gettext
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)

    from . import models  # noqa: F401  (модельдерді тіркеу)
    from .api import api_bp
    from .routes import admin_bp, auth_bp, main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")
    csrf.exempt(api_bp)

    register_error_handlers(app)
    register_commands(app)
    return app


def register_error_handlers(app):
    def wants_json():
        return request.path.startswith("/api/")

    @app.errorhandler(403)
    def forbidden(e):
        if wants_json():
            return jsonify(error="Рұқсат жоқ"), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        if wants_json():
            return jsonify(error="Табылмады"), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def too_large(e):
        return render_template("errors/413.html"), 413

    @app.errorhandler(500)
    def server_error(e):
        db.session.rollback()
        if wants_json():
            return jsonify(error="Сервер қатесі"), 500
        return render_template("errors/500.html"), 500


def register_commands(app):
    @app.cli.command("init-db")
    @click.option("--drop", is_flag=True, help="Алдымен барлық кестелерді өшіру")
    def init_db(drop):
        """Дерекқор кестелерін құру."""
        if drop:
            db.drop_all()
        db.create_all()
        click.echo("Дерекқор дайын.")

    @app.cli.command("seed")
    def seed():
        """Тест аккаунттар мен үлгі деректерді қосу."""
        from .seed import seed_data

        db.create_all()
        click.echo(seed_data())
