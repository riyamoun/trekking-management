"""Programmatic DB seed — admin always; demo fixtures only when SEED_DEMO_DATA=true."""

from __future__ import annotations

from datetime import date, timedelta

from flask import current_app

from backend.extensions import db
from backend.models import Booking, Trek, User
from backend.security import generate_password, write_bootstrap_admin


def _resolve_admin_password() -> str:
    configured = (current_app.config.get("ADMIN_PASSWORD") or "").strip()
    if configured:
        return configured
    return generate_password(18)


def _resolve_demo_password(config_key: str) -> str:
    configured = (current_app.config.get(config_key) or "").strip()
    if configured:
        return configured
    return generate_password(14)


def seed_database() -> None:
    """Create the single admin after DB init. Optional lab fixtures behind a flag."""
    admin_email = current_app.config["ADMIN_EMAIL_SEED"]
    admin = User.query.filter_by(role="admin").first()
    if not admin:
        admin_password = _resolve_admin_password()
        admin = User(
            email=admin_email,
            name=current_app.config["ADMIN_NAME"],
            phone=None,
            role="admin",
            is_active=True,
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        path = write_bootstrap_admin(admin_email, admin_password)
        current_app.logger.info(
            "Seeded admin %s — credentials written to %s (gitignored)",
            admin_email,
            path,
        )

    if not current_app.config.get("SEED_DEMO_DATA"):
        return

    if User.query.filter_by(role="staff").count() > 0:
        return

    staff_password = _resolve_demo_password("DEMO_STAFF_PASSWORD")
    user_password = _resolve_demo_password("DEMO_USER_PASSWORD")

    staff1 = User(
        email="staff1@trekmanage.local",
        name="Priya Sharma",
        phone="9888000001",
        role="staff",
        address="Manali Base Camp",
    )
    staff1.set_password(staff_password)
    staff2 = User(
        email="staff2@trekmanage.local",
        name="Arjun Mehta",
        phone="9888000002",
        role="staff",
        address="Rishikesh Hub",
    )
    staff2.set_password(staff_password)

    user1 = User(
        email="trekker1@example.com",
        name="Ananya Reddy",
        phone="9777000001",
        role="user",
        address="Hyderabad",
        emergency_contact="Emergency contact on file",
    )
    user1.set_password(user_password)
    user2 = User(
        email="trekker2@example.com",
        name="Rohan Kapoor",
        phone="9777000002",
        role="user",
        address="Mumbai",
        emergency_contact="Emergency contact on file",
    )
    user2.set_password(user_password)
    user3 = User(
        email="trekker3@example.com",
        name="Neha Joshi",
        phone="9777000003",
        role="user",
        address="Pune",
    )
    user3.set_password(user_password)

    db.session.add_all([staff1, staff2, user1, user2, user3])
    db.session.commit()

    today = date.today()
    treks = [
        Trek(
            name="Triund Sunrise Trek",
            location="McLeod Ganj, Himachal Pradesh",
            difficulty="Easy",
            duration_days=2,
            total_slots=20,
            available_slots=17,
            description="Gentle ridge walk with panoramic Dhauladhar views and a night camp under the stars.",
            status="Open",
            start_date=today + timedelta(days=10),
            end_date=today + timedelta(days=11),
            price=2499,
            instructions="Carry warm layers, 2L water, and rain jacket. Reporting time 6:00 AM at McLeod Ganj bus stand.",
        ),
        Trek(
            name="Kedarkantha Winter Trail",
            location="Sankri, Uttarakhand",
            difficulty="Moderate",
            duration_days=5,
            total_slots=15,
            available_slots=12,
            description="Classic winter summit trek with snow camps and pine forests.",
            status="Open",
            start_date=today + timedelta(days=21),
            end_date=today + timedelta(days=25),
            price=8999,
            instructions="Mandatory fitness check. Pack microspikes if available. No solo side trails.",
        ),
        Trek(
            name="Hampta Pass Crossing",
            location="Manali, Himachal Pradesh",
            difficulty="Hard",
            duration_days=5,
            total_slots=12,
            available_slots=12,
            description="Dramatic crossing from lush Kullu to arid Spiti landscapes.",
            status="Approved",
            start_date=today + timedelta(days=40),
            end_date=today + timedelta(days=44),
            price=11999,
            instructions="Prior altitude experience preferred. Diamox only under medical advice.",
        ),
        Trek(
            name="Har Ki Dun Valley",
            location="Sankri, Uttarakhand",
            difficulty="Moderate",
            duration_days=7,
            total_slots=18,
            available_slots=18,
            description="Ancient trade route through villages into a glacial amphitheatre.",
            status="Pending",
            start_date=today + timedelta(days=55),
            end_date=today + timedelta(days=61),
            price=10999,
            instructions="Permits arranged by staff. Respect village customs.",
        ),
        Trek(
            name="Chopta–Tungnath Ridge",
            location="Chopta, Uttarakhand",
            difficulty="Easy",
            duration_days=3,
            total_slots=25,
            available_slots=25,
            description="Short temple trek with alpine meadows — ideal for first-timers.",
            status="Closed",
            start_date=today - timedelta(days=20),
            end_date=today - timedelta(days=18),
            price=3999,
            instructions="Temple stairs can be icy — use trekking poles.",
        ),
        Trek(
            name="Valley of Flowers Circuit",
            location="Govindghat, Uttarakhand",
            difficulty="Moderate",
            duration_days=6,
            total_slots=16,
            available_slots=16,
            description="Monsoon bloom trail ending at Hemkund Sahib.",
            status="Completed",
            start_date=today - timedelta(days=60),
            end_date=today - timedelta(days=55),
            price=9999,
            instructions="National park entry included. No plastic bottles beyond base.",
        ),
    ]
    db.session.add_all(treks)
    db.session.commit()

    treks[0].assigned_staff.append(staff1)
    treks[1].assigned_staff.append(staff1)
    treks[1].assigned_staff.append(staff2)
    treks[2].assigned_staff.append(staff2)
    treks[5].assigned_staff.append(staff1)

    bookings = [
        Booking(user_id=user1.id, trek_id=treks[0].id, status="Booked", payment_status="Paid"),
        Booking(user_id=user2.id, trek_id=treks[0].id, status="Booked", payment_status="Paid"),
        Booking(user_id=user3.id, trek_id=treks[0].id, status="Booked", payment_status="Pending"),
        Booking(user_id=user1.id, trek_id=treks[1].id, status="Booked", payment_status="Paid"),
        Booking(user_id=user2.id, trek_id=treks[1].id, status="Booked", payment_status="Paid"),
        Booking(user_id=user3.id, trek_id=treks[1].id, status="Cancelled", payment_status="Refunded"),
        Booking(user_id=user1.id, trek_id=treks[5].id, status="Completed", payment_status="Paid"),
        Booking(user_id=user2.id, trek_id=treks[5].id, status="Completed", payment_status="Paid"),
    ]
    treks[0].available_slots = treks[0].total_slots - 3
    treks[1].available_slots = treks[1].total_slots - 2

    db.session.add_all(bookings)
    db.session.commit()

    creds_path = current_app.instance_path + "/DEMO_CREDENTIALS.txt"
    from pathlib import Path

    Path(current_app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(creds_path).write_text(
        (
            "# Local lab demo accounts — gitignored, never ship\n"
            f"staff_password={staff_password}\n"
            f"user_password={user_password}\n"
            "staff_emails=staff1@trekmanage.local,staff2@trekmanage.local\n"
            "user_emails=trekker1@example.com,trekker2@example.com,trekker3@example.com\n"
        ),
        encoding="utf-8",
    )
    current_app.logger.info("Seeded lab demo fixtures; passwords in %s", creds_path)
