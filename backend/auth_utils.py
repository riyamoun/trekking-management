"""JWT auth helpers and role decorators."""

from functools import wraps

from flask import jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, verify_jwt_in_request

from backend.models import User


def current_user() -> User | None:
    verify_jwt_in_request()
    user_id = get_jwt_identity()
    return User.query.get(int(user_id))


def role_required(*roles: str):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            role = claims.get("role")
            if role not in roles:
                return jsonify({"error": "Forbidden for this role"}), 403
            user = User.query.get(int(get_jwt_identity()))
            if not user or not user.is_active or user.is_blacklisted:
                return jsonify({"error": "Account inactive or blacklisted"}), 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        verify_jwt_in_request()
        user = User.query.get(int(get_jwt_identity()))
        if not user or not user.is_active or user.is_blacklisted:
            return jsonify({"error": "Account inactive or blacklisted"}), 403
        return fn(*args, **kwargs)

    return wrapper
