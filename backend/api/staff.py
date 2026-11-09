"""Trek Staff APIs — only assigned staff may manage a trek."""

from flask import Blueprint, jsonify, request

from backend.auth_utils import current_user, role_required
from backend.cache_utils import invalidate_trek_caches
from backend.extensions import db
from backend.models import Booking, Trek

staff_bp = Blueprint("staff", __name__)

STAFF_ALLOWED_STATUSES = {"Open", "Closed", "Completed"}


def _assigned_trek_or_403(trek_id: int, staff: object):
    trek = Trek.query.get_or_404(trek_id)
    if staff.id not in [s.id for s in trek.assigned_staff]:
        return None, (jsonify({"error": "You are not assigned to this trek"}), 403)
    return trek, None


@staff_bp.get("/dashboard")
@role_required("staff")
def dashboard():
    staff = current_user()
    treks = staff.assigned_treks.order_by(Trek.start_date.asc()).all()
    payload = []
    for trek in treks:
        registered = trek.bookings.filter(Booking.status.in_(["Booked", "Completed"])).count()
        data = trek.to_dict()
        data["registered_users"] = registered
        payload.append(data)
    return jsonify(
        {
            "assigned_treks": payload,
            "summary": {
                "assigned_count": len(payload),
                "open_count": sum(1 for t in payload if t["status"] == "Open"),
                "total_participants": sum(t["registered_users"] for t in payload),
            },
        }
    )


@staff_bp.get("/treks/<int:trek_id>")
@role_required("staff")
def trek_detail(trek_id: int):
    staff = current_user()
    trek, err = _assigned_trek_or_403(trek_id, staff)
    if err:
        return err
    return jsonify({"trek": trek.to_dict()})


@staff_bp.patch("/treks/<int:trek_id>")
@role_required("staff")
def update_trek(trek_id: int):
    staff = current_user()
    trek, err = _assigned_trek_or_403(trek_id, staff)
    if err:
        return err

    data = request.get_json(silent=True) or {}
    if "available_slots" in data:
        try:
            slots = int(data["available_slots"])
        except (TypeError, ValueError):
            return jsonify({"error": "available_slots must be an integer"}), 400
        if slots < 0 or slots > trek.total_slots:
            return jsonify({"error": f"Slots must be between 0 and {trek.total_slots}"}), 400
        # Do not allow slots below current booked count
        booked = trek.bookings.filter_by(status="Booked").count()
        remaining_capacity = trek.total_slots - booked
        if slots > remaining_capacity:
            # available_slots is remaining free seats
            pass
        trek.available_slots = slots

    if "total_slots" in data:
        try:
            total = int(data["total_slots"])
        except (TypeError, ValueError):
            return jsonify({"error": "total_slots must be an integer"}), 400
        booked = trek.bookings.filter_by(status="Booked").count()
        if total < booked:
            return jsonify({"error": f"total_slots cannot be less than booked ({booked})"}), 400
        trek.total_slots = total
        trek.available_slots = min(trek.available_slots, total - booked)

    if "status" in data:
        status = data["status"]
        if status not in STAFF_ALLOWED_STATUSES:
            return jsonify(
                {"error": "Staff may set status to Open, Closed, or Completed"}
            ), 400
        trek.status = status
        if status == "Completed":
            # Mark active bookings completed
            for booking in trek.bookings.filter_by(status="Booked"):
                booking.status = "Completed"

    if "instructions" in data:
        trek.instructions = data["instructions"]

    db.session.commit()
    invalidate_trek_caches(trek.id)
    return jsonify({"message": "Trek updated", "trek": trek.to_dict()})


@staff_bp.get("/treks/<int:trek_id>/participants")
@role_required("staff")
def participants(trek_id: int):
    staff = current_user()
    trek, err = _assigned_trek_or_403(trek_id, staff)
    if err:
        return err
    bookings = (
        trek.bookings.filter(Booking.status.in_(["Booked", "Completed", "Cancelled"]))
        .order_by(Booking.booking_date.desc())
        .all()
    )
    return jsonify({"trek": trek.to_dict(), "participants": [b.to_dict() for b in bookings]})


@staff_bp.post("/treks/<int:trek_id>/mark-started")
@role_required("staff")
def mark_started(trek_id: int):
    """Mark trek as underway by closing new bookings (Closed)."""
    staff = current_user()
    trek, err = _assigned_trek_or_403(trek_id, staff)
    if err:
        return err
    if trek.status not in {"Open", "Approved"}:
        return jsonify({"error": "Only Open/Approved treks can be marked started"}), 400
    trek.status = "Closed"
    db.session.commit()
    invalidate_trek_caches(trek.id)
    return jsonify({"message": "Trek marked as started (Closed for new bookings)", "trek": trek.to_dict()})


@staff_bp.post("/treks/<int:trek_id>/mark-completed")
@role_required("staff")
def mark_completed(trek_id: int):
    staff = current_user()
    trek, err = _assigned_trek_or_403(trek_id, staff)
    if err:
        return err
    trek.status = "Completed"
    for booking in trek.bookings.filter_by(status="Booked"):
        booking.status = "Completed"
    db.session.commit()
    invalidate_trek_caches(trek.id)
    return jsonify({"message": "Trek marked completed", "trek": trek.to_dict()})
