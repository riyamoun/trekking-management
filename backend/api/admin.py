"""Admin APIs — treks CRUD, staff, assignments, search, blacklist, reports."""

from datetime import datetime

from flask import Blueprint, jsonify, request
from sqlalchemy import func, or_

from backend.auth_utils import role_required
from backend.cache_utils import invalidate_trek_caches
from backend.extensions import db
from backend.models import Booking, NotificationLog, Trek, User
from backend.validators import is_valid_email

admin_bp = Blueprint("admin", __name__)

VALID_DIFFICULTIES = {"Easy", "Moderate", "Hard"}
VALID_TREK_STATUSES = {"Pending", "Approved", "Open", "Closed", "Completed"}


def _parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


@admin_bp.get("/dashboard")
@role_required("admin")
def dashboard():
    stats = {
        "total_treks": Trek.query.count(),
        "total_users": User.query.filter_by(role="user").count(),
        "total_staff": User.query.filter_by(role="staff").count(),
        "total_bookings": Booking.query.count(),
        "bookings_by_status": {
            row[0]: row[1]
            for row in db.session.query(Booking.status, func.count(Booking.id))
            .group_by(Booking.status)
            .all()
        },
        "treks_by_status": {
            row[0]: row[1]
            for row in db.session.query(Trek.status, func.count(Trek.id))
            .group_by(Trek.status)
            .all()
        },
        "popular_treks": [
            {
                "trek_id": r.id,
                "name": r.name,
                "location": r.location,
                "bookings": r.cnt,
            }
            for r in (
                db.session.query(
                    Trek.id, Trek.name, Trek.location, func.count(Booking.id).label("cnt")
                )
                .outerjoin(Booking, Booking.trek_id == Trek.id)
                .group_by(Trek.id)
                .order_by(func.count(Booking.id).desc())
                .limit(5)
                .all()
            )
        ],
        "recent_bookings": [b.to_dict() for b in Booking.query.order_by(Booking.booking_date.desc()).limit(8)],
    }
    return jsonify(stats)


@admin_bp.get("/search")
@role_required("admin")
def search():
    q = (request.args.get("q") or "").strip()
    kind = (request.args.get("type") or "all").strip().lower()
    if not q:
        return jsonify({"error": "Query q is required"}), 400
    like = f"%{q}%"
    result = {"users": [], "staff": [], "treks": []}

    if kind in ("all", "users", "user"):
        result["users"] = [
            u.to_dict()
            for u in User.query.filter(
                User.role == "user",
                or_(User.name.ilike(like), User.email.ilike(like), User.phone.ilike(like)),
            ).limit(30)
        ]
    if kind in ("all", "staff"):
        result["staff"] = [
            u.to_dict(include_sensitive=True)
            for u in User.query.filter(
                User.role == "staff",
                or_(User.name.ilike(like), User.email.ilike(like), User.phone.ilike(like)),
            ).limit(30)
        ]
    if kind in ("all", "treks", "trek"):
        result["treks"] = [
            t.to_dict()
            for t in Trek.query.filter(
                or_(
                    Trek.name.ilike(like),
                    Trek.location.ilike(like),
                    Trek.difficulty.ilike(like),
                    Trek.status.ilike(like),
                )
            ).limit(30)
        ]
    return jsonify(result)


# ---------- Treks CRUD ----------
@admin_bp.get("/treks")
@role_required("admin")
def list_treks():
    treks = Trek.query.order_by(Trek.created_at.desc()).all()
    return jsonify({"treks": [t.to_dict() for t in treks]})


@admin_bp.post("/treks")
@role_required("admin")
def create_trek():
    data = request.get_json(silent=True) or {}
    errors = {}
    name = (data.get("name") or "").strip()
    location = (data.get("location") or "").strip()
    difficulty = (data.get("difficulty") or "").strip()
    status = (data.get("status") or "Pending").strip()

    if not name:
        errors["name"] = "Name is required"
    if not location:
        errors["location"] = "Location is required"
    if difficulty not in VALID_DIFFICULTIES:
        errors["difficulty"] = "Difficulty must be Easy, Moderate, or Hard"
    if status not in VALID_TREK_STATUSES:
        errors["status"] = "Invalid status"
    try:
        duration = int(data.get("duration_days"))
        if duration < 1:
            raise ValueError()
    except (TypeError, ValueError):
        errors["duration_days"] = "Duration must be a positive integer"
        duration = 1
    try:
        total_slots = int(data.get("total_slots"))
        if total_slots < 1:
            raise ValueError()
    except (TypeError, ValueError):
        errors["total_slots"] = "Total slots must be a positive integer"
        total_slots = 1
    try:
        start_date = _parse_date(data.get("start_date", ""))
        end_date = _parse_date(data.get("end_date", ""))
        if end_date < start_date:
            errors["end_date"] = "End date must be on or after start date"
    except (TypeError, ValueError):
        errors["start_date"] = "start_date and end_date required (YYYY-MM-DD)"
        start_date = end_date = None

    if errors:
        return jsonify({"error": "Validation failed", "fields": errors}), 400

    available = int(data.get("available_slots", total_slots))
    available = min(max(available, 0), total_slots)

    trek = Trek(
        name=name,
        location=location,
        difficulty=difficulty,
        duration_days=duration,
        total_slots=total_slots,
        available_slots=available,
        description=(data.get("description") or "").strip() or None,
        status=status,
        start_date=start_date,
        end_date=end_date,
        price=float(data.get("price") or 0),
        instructions=(data.get("instructions") or "").strip() or None,
        image_url=(data.get("image_url") or "").strip() or None,
        gallery_urls=(data.get("gallery_urls") or "").strip() or None,
    )
    db.session.add(trek)
    db.session.commit()
    invalidate_trek_caches(trek.id)
    return jsonify({"message": "Trek created", "trek": trek.to_dict()}), 201


@admin_bp.put("/treks/<int:trek_id>")
@role_required("admin")
def update_trek(trek_id: int):
    trek = Trek.query.get_or_404(trek_id)
    data = request.get_json(silent=True) or {}

    if "name" in data:
        trek.name = (data["name"] or "").strip() or trek.name
    if "location" in data:
        trek.location = (data["location"] or "").strip() or trek.location
    if "difficulty" in data:
        if data["difficulty"] not in VALID_DIFFICULTIES:
            return jsonify({"error": "Invalid difficulty"}), 400
        trek.difficulty = data["difficulty"]
    if "duration_days" in data:
        trek.duration_days = int(data["duration_days"])
    if "total_slots" in data:
        trek.total_slots = int(data["total_slots"])
    if "available_slots" in data:
        trek.available_slots = max(0, min(int(data["available_slots"]), trek.total_slots))
    if "description" in data:
        trek.description = data["description"]
    if "status" in data:
        if data["status"] not in VALID_TREK_STATUSES:
            return jsonify({"error": "Invalid status"}), 400
        trek.status = data["status"]
    if "start_date" in data and data["start_date"]:
        trek.start_date = _parse_date(data["start_date"])
    if "end_date" in data and data["end_date"]:
        trek.end_date = _parse_date(data["end_date"])
    if "price" in data:
        trek.price = float(data["price"] or 0)
    if "instructions" in data:
        trek.instructions = data["instructions"]
    if "image_url" in data:
        trek.image_url = (data.get("image_url") or "").strip() or None
    if "gallery_urls" in data:
        trek.gallery_urls = (data.get("gallery_urls") or "").strip() or None

    db.session.commit()
    invalidate_trek_caches(trek.id)
    return jsonify({"message": "Trek updated", "trek": trek.to_dict()})


@admin_bp.delete("/treks/<int:trek_id>")
@role_required("admin")
def delete_trek(trek_id: int):
    trek = Trek.query.get_or_404(trek_id)
    active = trek.bookings.filter(Booking.status == "Booked").count()
    if active:
        return jsonify({"error": "Cannot delete trek with active bookings. Close it instead."}), 400
    db.session.delete(trek)
    db.session.commit()
    invalidate_trek_caches(trek_id)
    return jsonify({"message": "Trek removed"})


# ---------- Staff management ----------
@admin_bp.get("/staff")
@role_required("admin")
def list_staff():
    staff = User.query.filter_by(role="staff").order_by(User.name).all()
    return jsonify({"staff": [s.to_dict(include_sensitive=True) for s in staff]})


@admin_bp.post("/staff")
@role_required("admin")
def create_staff():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    name = (data.get("name") or "").strip()
    password = data.get("password") or ""
    errors = {}
    if not name:
        errors["name"] = "Name is required"
    if not is_valid_email(email):
        errors["email"] = "Valid email required"
    from backend.security import password_policy_error

    pwd_err = password_policy_error(password, min_length=10)
    if pwd_err:
        errors["password"] = pwd_err
    if errors:
        return jsonify({"error": "Validation failed", "fields": errors}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists"}), 409

    staff = User(
        email=email,
        name=name,
        phone=(data.get("phone") or "").strip() or None,
        role="staff",
        address=(data.get("address") or "").strip() or None,
    )
    staff.set_password(password)
    db.session.add(staff)
    db.session.commit()
    return jsonify({"message": "Staff created", "staff": staff.to_dict(include_sensitive=True)}), 201


@admin_bp.put("/staff/<int:staff_id>")
@role_required("admin")
def update_staff(staff_id: int):
    staff = User.query.filter_by(id=staff_id, role="staff").first_or_404()
    data = request.get_json(silent=True) or {}
    if "name" in data and data["name"]:
        staff.name = data["name"].strip()
    if "phone" in data:
        staff.phone = data["phone"]
    if "address" in data:
        staff.address = data["address"]
    if "password" in data and data["password"]:
        from backend.security import password_policy_error

        pwd_err = password_policy_error(data["password"], min_length=10)
        if pwd_err:
            return jsonify({"error": pwd_err}), 400
        staff.set_password(data["password"])
    db.session.commit()
    return jsonify({"message": "Staff updated", "staff": staff.to_dict(include_sensitive=True)})


@admin_bp.post("/treks/<int:trek_id>/assign-staff")
@role_required("admin")
def assign_staff(trek_id: int):
    trek = Trek.query.get_or_404(trek_id)
    data = request.get_json(silent=True) or {}
    staff_ids = data.get("staff_ids")
    if staff_ids is None and "staff_id" in data:
        staff_ids = [data["staff_id"]]
    if not isinstance(staff_ids, list):
        return jsonify({"error": "staff_ids must be a list"}), 400

    staff_members = User.query.filter(User.id.in_(staff_ids), User.role == "staff").all()
    if len(staff_members) != len(set(staff_ids)):
        return jsonify({"error": "One or more staff IDs invalid"}), 400

    replace = bool(data.get("replace", True))
    if replace:
        trek.assigned_staff = staff_members
    else:
        existing = {s.id for s in trek.assigned_staff}
        for s in staff_members:
            if s.id not in existing:
                trek.assigned_staff.append(s)
    db.session.commit()
    invalidate_trek_caches(trek.id)
    return jsonify({"message": "Staff assigned", "trek": trek.to_dict()})


# ---------- Users / blacklist ----------
@admin_bp.get("/users")
@role_required("admin")
def list_users():
    users = User.query.filter_by(role="user").order_by(User.created_at.desc()).all()
    return jsonify({"users": [u.to_dict() for u in users]})


@admin_bp.patch("/people/<int:user_id>/status")
@role_required("admin")
def set_person_status(user_id: int):
    person = User.query.get_or_404(user_id)
    if person.role == "admin":
        return jsonify({"error": "Cannot modify admin account"}), 400
    data = request.get_json(silent=True) or {}
    if "is_active" in data:
        person.is_active = bool(data["is_active"])
    if "is_blacklisted" in data:
        person.is_blacklisted = bool(data["is_blacklisted"])
        if person.is_blacklisted:
            person.is_active = False
    db.session.commit()
    return jsonify({"message": "Status updated", "user": person.to_dict()})


@admin_bp.get("/bookings")
@role_required("admin")
def all_bookings():
    bookings = Booking.query.order_by(Booking.booking_date.desc()).all()
    return jsonify({"bookings": [b.to_dict() for b in bookings]})


@admin_bp.get("/reports/summary")
@role_required("admin")
def reports_summary():
    """On-demand stats used by ChartJS analytics page."""
    popular = (
        db.session.query(
            Trek.name, func.count(Booking.id).label("cnt")
        )
        .outerjoin(Booking, (Booking.trek_id == Trek.id) & (Booking.status != "Cancelled"))
        .group_by(Trek.id)
        .order_by(func.count(Booking.id).desc())
        .all()
    )
    participation = (
        db.session.query(User.name, func.count(Booking.id).label("cnt"))
        .join(Booking, Booking.user_id == User.id)
        .filter(User.role == "user", Booking.status != "Cancelled")
        .group_by(User.id)
        .order_by(func.count(Booking.id).desc())
        .limit(10)
        .all()
    )
    return jsonify(
        {
            "popular_treks": [{"name": n, "count": c} for n, c in popular],
            "top_participants": [{"name": n, "count": c} for n, c in participation],
            "treks_conducted": Trek.query.filter(Trek.status.in_(["Completed", "Closed"])).count(),
            "active_open_treks": Trek.query.filter_by(status="Open").count(),
        }
    )


@admin_bp.post("/reports/monthly/run")
@role_required("admin")
def trigger_monthly_report():
    """Manually trigger monthly report Celery job (useful for viva demo)."""
    from celery_app.tasks import generate_monthly_report

    task = generate_monthly_report.delay()
    return jsonify({"message": "Monthly report job queued", "task_id": task.id})


@admin_bp.get("/notifications")
@role_required("admin")
def notifications():
    logs = NotificationLog.query.order_by(NotificationLog.created_at.desc()).limit(50).all()
    return jsonify({"notifications": [n.to_dict() for n in logs]})
