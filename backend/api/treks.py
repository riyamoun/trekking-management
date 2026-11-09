"""Public/shared trek listing with Redis caching for open treks."""

from flask import Blueprint, jsonify, request

from backend.auth_utils import login_required
from backend.cache_utils import (
    OPEN_TREKS_KEY,
    TREK_DETAIL_PREFIX,
    get_cached_json,
    set_cached_json,
)
from backend.models import Trek

treks_bp = Blueprint("treks", __name__)


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
        query = query.filter(
            db_or(Trek.name.ilike(like), Trek.location.ilike(like), Trek.description.ilike(like))
        )
    return query


def db_or(*clauses):
    from sqlalchemy import or_

    return or_(*clauses)


@treks_bp.get("")
def list_treks():
    """List treks. Open treks are Redis-cached when no filters are applied."""
    # Default public view: Open (+ Approved for browsing interest)
    view = (request.args.get("view") or "public").strip()
    has_filters = any(
        request.args.get(k)
        for k in ("difficulty", "location", "duration", "status", "q")
    )

    if view == "public" and not has_filters:
        cached = get_cached_json(OPEN_TREKS_KEY)
        if cached is not None:
            return jsonify({"treks": cached, "cached": True})

    query = Trek.query
    if view == "public":
        query = query.filter(Trek.status.in_(["Open", "Approved"]))
    query = _apply_filters(query)
    treks = [t.to_dict() for t in query.order_by(Trek.start_date.asc()).all()]

    if view == "public" and not has_filters:
        set_cached_json(OPEN_TREKS_KEY, treks)

    return jsonify({"treks": treks, "cached": False})


@treks_bp.get("/<int:trek_id>")
def trek_detail(trek_id: int):
    cache_key = f"{TREK_DETAIL_PREFIX}{trek_id}"
    cached = get_cached_json(cache_key)
    if cached is not None:
        return jsonify({"trek": cached, "cached": True})

    trek = Trek.query.get_or_404(trek_id)
    data = trek.to_dict()
    set_cached_json(cache_key, data)
    return jsonify({"trek": data, "cached": False})
