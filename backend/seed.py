"""Programmatic seed: single admin + demo staff/users/treks/bookings for viva demos."""

from datetime import date, timedelta

from flask import current_app

from backend.extensions import db
from backend.models import Booking, Trek, User


def seed_database() -> None:
    admin_email = current_app.config["ADMIN_EMAIL_SEED"]
    admin = User.query.filter_by(email=admin_email).first()
    if not admin:
        admin = User(
            email=admin_email,
            name=current_app.config["ADMIN_NAME"],
            phone="9999999999",
            role="admin",
            is_active=True,
        )
        admin.set_password(current_app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
        current_app.logger.info("Seeded admin user: %s", admin_email)

    if User.query.filter_by(role="staff").count() > 0:
        return  # demo data already present

    staff1 = User(
        email="staff1@trekmanage.local",
        name="Priya Sharma",
        phone="9888000001",
        role="staff",
        address="Manali Base Camp",
    )
    staff1.set_password("Staff@123")
    staff2 = User(
        email="staff2@trekmanage.local",
        name="Arjun Mehta",
        phone="9888000002",
        role="staff",
        address="Rishikesh Hub",
    )
    staff2.set_password("Staff@123")

    user1 = User(
        email="trekker1@example.com",
        name="Ananya Reddy",
        phone="9777000001",
        role="user",
        address="Hyderabad",
        emergency_contact="Mother — 9777000099",
    )
    user1.set_password("User@123")
    user2 = User(
        email="trekker2@example.com",
        name="Rohan Kapoor",
        phone="9777000002",
        role="user",
        address="Mumbai",
        emergency_contact="Father — 9777000088",
    )
    user2.set_password("User@123")
    user3 = User(
        email="trekker3@example.com",
        name="Neha Joshi",
        phone="9777000003",
        role="user",
        address="Pune",
    )
    user3.set_password("User@123")

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

    # Assign staff
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
    # Adjust slots for open treks based on booked counts
    treks[0].available_slots = treks[0].total_slots - 3
    treks[1].available_slots = treks[1].total_slots - 2

    db.session.add_all(bookings)
    db.session.commit()
    current_app.logger.info("Seeded demo staff, users, treks, and bookings")
