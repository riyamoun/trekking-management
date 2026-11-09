"""Trekker APIs — browse, book, history, profile, CSV export."""

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request, send_file

from backend.auth_utils import current_user, role_required
from backend.cache_utils import invalidate_trek_caches
from backend.extensions import db
from backend.models import Booking, ExportJob, Trek
from backend.notifications import notify_booking

user_bp = Blueprint("user", __name__)


@user_bp.get("/dashboard")
@role_required("user")
def dashboard():
    user = current_user()
    open_treks = (
        Trek.query.filter(Trek.status.in_(["Open", "Approved"]))
        .order_by(Trek.start_date.asc())
        .limit(12)
        .all()
    )
    bookings = (
        Booking.query.filter_by(user_id=user.id)
        .order_by(Booking.booking_date.desc())
        .all()
    )
    return jsonify(
        {
            "available_treks": [t.to_dict() for t in open_treks if t.status == "Open"],
            "approved_treks": [t.to_dict() for t in open_treks if t.status == "Approved"],
            "bookings": [b.to_dict() for b in bookings],
            "summary": {
                "booked": sum(1 for b in bookings if b.status == "Booked"),
                "completed": sum(1 for b in bookings if b.status == "Completed"),
                "cancelled": sum(1 for b in bookings if b.status == "Cancelled"),
            },
        }
    )


@user_bp.get("/profile")
@role_required("user")
def get_profile():
    return jsonify({"user": current_user().to_dict()})


@user_bp.put("/profile")
@role_required("user")
def update_profile():
    user = current_user()
    data = request.get_json(silent=True) or {}
    errors = {}
    if "name" in data:
        name = (data["name"] or "").strip()
        if len(name) < 2:
            errors["name"] = "Name min 2 characters"
        else:
            user.name = name
    if "phone" in data:
        user.phone = (data["phone"] or "").strip() or None
    if "address" in data:
        user.address = (data["address"] or "").strip() or None
    if "emergency_contact" in data:
        user.emergency_contact = (data["emergency_contact"] or "").strip() or None
    if "password" in data and data["password"]:
        if len(data["password"]) < 6:
            errors["password"] = "Password min 6 characters"
        else:
            user.set_password(data["password"])
    if errors:
        return jsonify({"error": "Validation failed", "fields": errors}), 400
    db.session.commit()
    return jsonify({"message": "Profile updated", "user": user.to_dict()})


@user_bp.post("/bookings")
@role_required("user")
def book_trek():
    user = current_user()
    data = request.get_json(silent=True) or {}
    trek_id = data.get("trek_id")
    if not trek_id:
        return jsonify({"error": "trek_id is required"}), 400

    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({"error": "Trek not found"}), 404
    if trek.status != "Open":
        return jsonify({"error": "Booking allowed only when trek status is Open"}), 400
    if trek.available_slots <= 0:
        return jsonify({"error": "No slots available — overbooking prevented"}), 400

    existing = Booking.query.filter_by(
        user_id=user.id, trek_id=trek.id, status="Booked"
    ).first()
    if existing:
        return jsonify({"error": "Duplicate booking for the same trek is not allowed"}), 409

    # Also block if they already completed? Allow re-book only if previous cancelled
    booking = Booking(
        user_id=user.id,
        trek_id=trek.id,
        status="Booked",
        payment_status=data.get("payment_status") or "Pending",
        notes=(data.get("notes") or "").strip() or None,
    )
    trek.available_slots -= 1
    db.session.add(booking)
    db.session.commit()
    invalidate_trek_caches(trek.id)

    try:
        notify_booking(user.email, user.name, trek.name, "confirmed")
    except Exception:
        pass

    return jsonify({"message": "Booked successfully", "booking": booking.to_dict()}), 201


@user_bp.post("/bookings/<int:booking_id>/cancel")
@role_required("user")
def cancel_booking(booking_id: int):
    user = current_user()
    booking = Booking.query.filter_by(id=booking_id, user_id=user.id).first_or_404()
    if booking.status != "Booked":
        return jsonify({"error": "Only Booked bookings can be cancelled"}), 400

    booking.status = "Cancelled"
    booking.payment_status = "Refunded"
    trek = booking.trek
    if trek and trek.status == "Open":
        trek.available_slots = min(trek.total_slots, trek.available_slots + 1)
    db.session.commit()
    if trek:
        invalidate_trek_caches(trek.id)

    try:
        notify_booking(user.email, user.name, trek.name if trek else "trek", "cancelled")
    except Exception:
        pass

    return jsonify({"message": "Booking cancelled", "booking": booking.to_dict()})


@user_bp.get("/bookings")
@role_required("user")
def booking_history():
    user = current_user()
    bookings = (
        Booking.query.filter_by(user_id=user.id)
        .order_by(Booking.booking_date.desc())
        .all()
    )
    return jsonify({"bookings": [b.to_dict() for b in bookings]})


@user_bp.post("/exports/bookings")
@role_required("user")
def export_bookings():
    """Trigger Celery async CSV export of booking history."""
    user = current_user()
    job = ExportJob(user_id=user.id, status="Pending", message="Queued")
    db.session.add(job)
    db.session.commit()

    from celery_app.tasks import export_user_bookings_csv

    task = export_user_bookings_csv.delay(job.id)
    job.celery_task_id = task.id
    db.session.commit()
    return jsonify({"message": "Export job started", "job": job.to_dict()}), 202


@user_bp.get("/exports")
@role_required("user")
def list_exports():
    user = current_user()
    jobs = (
        ExportJob.query.filter_by(user_id=user.id)
        .order_by(ExportJob.created_at.desc())
        .limit(20)
        .all()
    )
    return jsonify({"jobs": [j.to_dict() for j in jobs]})


@user_bp.get("/exports/<int:job_id>")
@role_required("user")
def export_status(job_id: int):
    user = current_user()
    job = ExportJob.query.filter_by(id=job_id, user_id=user.id).first_or_404()
    return jsonify({"job": job.to_dict()})


@user_bp.get("/exports/<int:job_id>/download")
@role_required("user")
def download_export(job_id: int):
    user = current_user()
    job = ExportJob.query.filter_by(id=job_id, user_id=user.id).first_or_404()
    if job.status != "Completed" or not job.file_path:
        return jsonify({"error": "Export not ready"}), 400
    path = Path(job.file_path)
    if not path.exists():
        # Resolve relative to exports dir
        path = Path(current_app.config["EXPORTS_DIR"]) / path.name
    if not path.exists():
        return jsonify({"error": "File missing"}), 404
    return send_file(path, as_attachment=True, download_name=path.name)
