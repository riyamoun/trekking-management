"""SQLAlchemy models — database is created programmatically via db.create_all()."""

from datetime import date, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from backend.extensions import db


class User(db.Model):
    """Unified user model for Admin, Trek Staff, and Trekker roles."""

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False, default="user")  # admin|staff|user
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_blacklisted = db.Column(db.Boolean, default=False, nullable=False)
    address = db.Column(db.String(255))
    emergency_contact = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    bookings = db.relationship("Booking", back_populates="user", lazy="dynamic")
    assigned_treks = db.relationship(
        "Trek",
        secondary="trek_staff_assignments",
        back_populates="assigned_staff",
        lazy="dynamic",
    )
    export_jobs = db.relationship("ExportJob", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_sensitive: bool = False) -> dict:
        data = {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "phone": self.phone,
            "role": self.role,
            "is_active": self.is_active,
            "is_blacklisted": self.is_blacklisted,
            "address": self.address,
            "emergency_contact": self.emergency_contact,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_sensitive:
            data["assigned_trek_ids"] = [t.id for t in self.assigned_treks]
        return data


trek_staff_assignments = db.Table(
    "trek_staff_assignments",
    db.Column("trek_id", db.Integer, db.ForeignKey("treks.id"), primary_key=True),
    db.Column("staff_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("assigned_at", db.DateTime, default=datetime.utcnow),
)


class Trek(db.Model):
    __tablename__ = "treks"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    location = db.Column(db.String(160), nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)  # Easy|Moderate|Hard
    duration_days = db.Column(db.Integer, nullable=False)
    total_slots = db.Column(db.Integer, nullable=False)
    available_slots = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(
        db.String(20), nullable=False, default="Pending"
    )  # Pending|Approved|Open|Closed|Completed
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    price = db.Column(db.Float, default=0.0)
    instructions = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    assigned_staff = db.relationship(
        "User",
        secondary=trek_staff_assignments,
        back_populates="assigned_treks",
        lazy="joined",
    )
    bookings = db.relationship("Booking", back_populates="trek", lazy="dynamic")

    def booked_count(self) -> int:
        return self.bookings.filter_by(status="Booked").count()

    def to_dict(self, include_staff: bool = True) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "location": self.location,
            "difficulty": self.difficulty,
            "duration_days": self.duration_days,
            "total_slots": self.total_slots,
            "available_slots": self.available_slots,
            "description": self.description,
            "status": self.status,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "price": self.price,
            "instructions": self.instructions,
            "booked_count": self.booked_count(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_staff:
            data["assigned_staff"] = [
                {"id": s.id, "name": s.name, "email": s.email}
                for s in self.assigned_staff
                if s.role == "staff"
            ]
            data["assigned_staff_ids"] = [
                s.id for s in self.assigned_staff if s.role == "staff"
            ]
        return data


class Booking(db.Model):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    trek_id = db.Column(db.Integer, db.ForeignKey("treks.id"), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="Booked"
    )  # Booked|Cancelled|Completed
    payment_status = db.Column(db.String(20), default="Pending")  # Pending|Paid|Refunded
    notes = db.Column(db.String(255))

    user = db.relationship("User", back_populates="bookings")
    trek = db.relationship("Trek", back_populates="bookings")

    __table_args__ = (
        db.Index("ix_bookings_user_trek", "user_id", "trek_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "trek_id": self.trek_id,
            "booking_date": self.booking_date.isoformat() if self.booking_date else None,
            "status": self.status,
            "payment_status": self.payment_status,
            "notes": self.notes,
            "user": {
                "id": self.user.id,
                "name": self.user.name,
                "email": self.user.email,
                "phone": self.user.phone,
            }
            if self.user
            else None,
            "trek": {
                "id": self.trek.id,
                "name": self.trek.name,
                "location": self.trek.location,
                "difficulty": self.trek.difficulty,
                "duration_days": self.trek.duration_days,
                "status": self.trek.status,
                "start_date": self.trek.start_date.isoformat()
                if self.trek.start_date
                else None,
                "end_date": self.trek.end_date.isoformat() if self.trek.end_date else None,
            }
            if self.trek
            else None,
        }


class ExportJob(db.Model):
    """Tracks user-triggered CSV export Celery jobs."""

    __tablename__ = "export_jobs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="Pending"
    )  # Pending|Running|Completed|Failed
    file_path = db.Column(db.String(255))
    message = db.Column(db.String(255))
    celery_task_id = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)

    user = db.relationship("User", back_populates="export_jobs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "status": self.status,
            "file_path": self.file_path,
            "download_url": f"/api/user/exports/{self.id}/download"
            if self.status == "Completed" and self.file_path
            else None,
            "message": self.message,
            "celery_task_id": self.celery_task_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class NotificationLog(db.Model):
    """Persists mock/real notification deliveries for demo visibility."""

    __tablename__ = "notification_logs"

    id = db.Column(db.Integer, primary_key=True)
    channel = db.Column(db.String(20), nullable=False)  # email|webhook|sms|mock
    recipient = db.Column(db.String(160), nullable=False)
    subject = db.Column(db.String(255))
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "channel": self.channel,
            "recipient": self.recipient,
            "subject": self.subject,
            "body": self.body,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
