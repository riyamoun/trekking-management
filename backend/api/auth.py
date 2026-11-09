"""Authentication endpoints — JWT based."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

from backend.auth_utils import current_user, login_required
from backend.extensions import db
from backend.models import User
from backend.validators import is_valid_email

auth_bp = Blueprint("auth", __name__)


def _validate_password(password: str) -> str | None:
    if not password or len(password) < 6:
        return "Password must be at least 6 characters"
    return None


@auth_bp.post("/register")
def register():
    """Self-registration for Trekkers only."""
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""
    phone = (data.get("phone") or "").strip()

    errors = {}
    if not name or len(name) < 2:
        errors["name"] = "Name is required (min 2 characters)"
    if not is_valid_email(email):
        errors["email"] = "Valid email is required"
    pwd_err = _validate_password(password)
    if pwd_err:
        errors["password"] = pwd_err
    if errors:
        return jsonify({"error": "Validation failed", "fields": errors}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    user = User(
        email=email,
        name=name,
        phone=phone or None,
        role="user",
        address=(data.get("address") or "").strip() or None,
        emergency_contact=(data.get("emergency_contact") or "").strip() or None,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    token = create_access_token(
        identity=str(user.id), additional_claims={"role": user.role, "email": user.email}
    )
    return jsonify({"message": "Registered", "access_token": token, "user": user.to_dict()}), 201


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401
    if user.is_blacklisted:
        return jsonify({"error": "Account is blacklisted. Contact admin."}), 403
    if not user.is_active:
        return jsonify({"error": "Account is deactivated. Contact admin."}), 403

    token = create_access_token(
        identity=str(user.id), additional_claims={"role": user.role, "email": user.email}
    )
    return jsonify({"access_token": token, "user": user.to_dict()})


@auth_bp.get("/me")
@login_required
def me():
    user = current_user()
    return jsonify({"user": user.to_dict(include_sensitive=True)})
