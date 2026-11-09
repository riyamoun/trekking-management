"""JWT auth helpers — roles always reconciled against the live database user."""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from backend.extensions import db
from backend.models import User


def current_user() -> User | None:
    verify_jwt_in_request()
    user_id = get_jwt_identity()
    return db.session.get(User, int(user_id))


def _load_active_user() -> tuple[User | None, tuple | None]:
    verify_jwt_in_request()
    user = db.session.get(User, int(get_jwt_identity()))
    if not user:
        return None, (jsonify({"error": "Unauthorized"}), 401)
    if user.is_blacklisted:
        return None, (jsonify({"error": "Account is blacklisted. Contact admin."}), 403)
    if not user.is_active:
        return None, (jsonify({"error": "Account is deactivated. Contact admin."}), 403)
    return user, None


def role_required(*roles: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user, err = _load_active_user()
            if err:
                return err
            # Authorize from DB role, not JWT claim (prevents stale/forged role elevation)
            if user.role not in roles:
                return jsonify({"error": "Forbidden for this role"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user, err = _load_active_user()
        if err:
            return err
        return fn(*args, **kwargs)

    return wrapper
