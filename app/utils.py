import os
import uuid
from functools import wraps

from flask import abort, current_app
from flask_login import current_user
from werkzeug.utils import secure_filename


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def allowed_file(filename, allowed=None):
    allowed = allowed or current_app.config["ALLOWED_EXTENSIONS"]
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def save_upload(file_storage, allowed=None):
    """Файлды қауіпсіз атаумен сақтап, атауын қайтарады (немесе None)."""
    if not file_storage or not file_storage.filename:
        return None
    if not allowed_file(file_storage.filename, allowed):
        return None
    safe = secure_filename(file_storage.filename) or "file"
    ext = safe.rsplit(".", 1)[-1].lower()
    name = f"{uuid.uuid4().hex[:12]}_{safe[:60]}"
    if not name.lower().endswith("." + ext):
        name += "." + ext
    file_storage.save(os.path.join(current_app.config["UPLOAD_FOLDER"], name))
    return name


def delete_upload(filename):
    if not filename:
        return
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], os.path.basename(filename))
    if os.path.exists(path):
        os.remove(path)
