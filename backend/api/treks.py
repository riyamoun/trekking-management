"""Public/shared trek listing with Redis caching for open treks."""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

from backend.cache_utils import (
    OPEN_TREKS_KEY,
    TREK_DETAIL_PREFIX,
    get_cached_json,
    set_cached_json,
)
from backend.extensions import db
from backend.models import Trek, User

treks_bp = Blueprint("treks", __name__)

PUBLIC_STATUSES = {"Open", "Approved"}


def _apply_filters(query):
    difficulty = (request.args.get("difficulty") or "").strip()
    location = (request.args.get("location") or "").strip()
    duration = request.args.get("duration")
    status = (request.args.get("status") or "").strip()
    q = (request.args.get("q") or "").strip()

    if difficulty:
        query = query.filter(Trek.difficulty.ilike(difficulty))
    if location:
        query = query.filter(Trek.location.ilike(f"%{location}%"))
    if duration:
        try:
            query = query.filter(Trek.duration_days == int(duration))
        except ValueError:
            pass
    if status:
        query = query.filter(Trek.status.ilike(status))
    if q:
        like = f"%{q}%"
        from sqlalchemy import or_

        query = query.filter(
            or_(Trek.name.ilike(like), Trek.location.ilike(like), Trek.description.ilike(like))
        )
    return query


def _optional_user() -> User | None:
    try:
        verify_jwt_in_request(optional=True)
        identity = get_jwt_identity()
        if identity is None:
            return None
        return db.session.get(User, int(identity))
    except Exception:
        return None


def _can_view_trek(trek: Trek, user: User | None) -> bool:
    if trek.status in PUBLIC_STATUSES:
        return True
    if not user or not user.is_active or user.is_blacklisted:
        return False
    if user.role == "admin":
        return True
    if user.role == "staff" and user.id in [s.id for s in trek.assigned_staff]:
        return True
    if user.role == "user":
        # Trekkers may see non-public treks only if they have a booking history on it
        from backend.models import Booking

        return (
            Booking.query.filter_by(user_id=user.id, trek_id=trek.id).first() is not None
        )
    return False


@treks_bp.get("")
def list_treks():
    """List treks. Open/Approved are public; other views require admin."""
    view = (request.args.get("view") or "public").strip()
    has_filters = any(
        request.args.get(k)
        for k in ("difficulty", "location", "duration", "status", "q")
    )

    if view != "public":
        user = _optional_user()
        if not user or user.role != "admin":
            return jsonify({"error": "Admin authentication required for this view"}), 401

    if view == "public" and not has_filters:
        cached = get_cached_json(OPEN_TREKS_KEY)
        if cached is not None:
            return jsonify({"treks": cached, "cached": True})

    query = Trek.query
    if view == "public":
        query = query.filter(Trek.status.in_(list(PUBLIC_STATUSES)))
    query = _apply_filters(query)
    treks = [t.to_dict() for t in query.order_by(Trek.start_date.asc()).all()]

    if view == "public" and not has_filters:
        set_cached_json(OPEN_TREKS_KEY, treks)

    return jsonify({"treks": treks, "cached": False})


@treks_bp.get("/<int:trek_id>")
def trek_detail(trek_id: int):
    trek = db.session.get(Trek, trek_id)
    if not trek:
        return jsonify({"error": "Not found"}), 404

    user = _optional_user()
    if not _can_view_trek(trek, user):
        return jsonify({"error": "Not found"}), 404

    # Cache only public trek details
    if trek.status in PUBLIC_STATUSES:
        cache_key = f"{TREK_DETAIL_PREFIX}{trek_id}"
        cached = get_cached_json(cache_key)
        if cached is not None:
            return jsonify({"trek": cached, "cached": True})
        data = trek.to_dict()
        set_cached_json(cache_key, data)
        return jsonify({"trek": data, "cached": False})

    return jsonify({"trek": trek.to_dict(), "cached": False})
