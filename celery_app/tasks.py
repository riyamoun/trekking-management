"""Celery batch jobs: daily reminders, monthly report, CSV export."""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta
from pathlib import Path

from flask import current_app
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func

from backend.extensions import db
from backend.models import Booking, ExportJob, Trek, User
from backend.notifications import send_email, send_webhook
from celery_app.celery_config import celery


@celery.task(name="celery_app.tasks.send_daily_reminders")
def send_daily_reminders() -> dict:
    """Remind users with Booked treks starting within the next 3 days."""
    today = date.today()
    window_end = today + timedelta(days=3)
    bookings = (
        Booking.query.join(Trek)
        .filter(
            Booking.status == "Booked",
            Trek.start_date >= today,
            Trek.start_date <= window_end,
        )
        .all()
    )

    sent = 0
    for booking in bookings:
        user = booking.user
        trek = booking.trek
        if not user or not trek:
            continue
        subject = f"Reminder: {trek.name} starts on {trek.start_date.isoformat()}"
        html = f"""
        <h2>Upcoming Trek Reminder</h2>
        <p>Hi {user.name},</p>
        <p>This is a friendly reminder that <strong>{trek.name}</strong> in
        <strong>{trek.location}</strong> starts on <strong>{trek.start_date}</strong>.</p>
        <p><em>Instructions:</em> {trek.instructions or 'Follow staff guidance at reporting point.'}</p>
        <p>Difficulty: {trek.difficulty} · Duration: {trek.duration_days} day(s)</p>
        <p>— TrekManage</p>
        """
        send_email(user.email, subject, html)
        send_webhook(
            {
                "text": (
                    f"Reminder for {user.name}: {trek.name} starts {trek.start_date.isoformat()}"
                )
            }
        )
        sent += 1

    return {"reminders_sent": sent, "date": today.isoformat()}


def _month_bounds(ref: date | None = None) -> tuple[date, date, str]:
    ref = ref or date.today()
    # Report for previous calendar month when run on 1st; else current month-to-date for manual runs
    if ref.day == 1:
        end = ref - timedelta(days=1)
        start = end.replace(day=1)
    else:
        start = ref.replace(day=1)
        end = ref
    label = start.strftime("%B %Y")
    return start, end, label


@celery.task(name="celery_app.tasks.generate_monthly_report")
def generate_monthly_report() -> dict:
    """Generate HTML + PDF monthly activity report and notify admin."""
    start, end, label = _month_bounds()
    reports_dir = Path(current_app.config["REPORTS_DIR"])
    reports_dir.mkdir(parents=True, exist_ok=True)

    treks_conducted = Trek.query.filter(
        Trek.status.in_(["Completed", "Closed"]),
        Trek.end_date >= start,
        Trek.end_date <= end,
    ).count()

    # Also count any trek that finished in window regardless of status edge cases
    participants = (
        db.session.query(func.count(func.distinct(Booking.user_id)))
        .join(Trek)
        .filter(
            Booking.status.in_(["Booked", "Completed"]),
            Trek.end_date >= start,
            Trek.end_date <= end,
        )
        .scalar()
        or 0
    )

    popular = (
        db.session.query(Trek.name, Trek.location, func.count(Booking.id).label("cnt"))
        .outerjoin(
            Booking,
            (Booking.trek_id == Trek.id) & (Booking.status.in_(["Booked", "Completed"])),
        )
        .filter(Trek.end_date >= start, Trek.end_date <= end)
        .group_by(Trek.id)
        .order_by(func.count(Booking.id).desc())
        .limit(10)
        .all()
    )
    if not popular:
        # Fallback: all-time popular for demo months with sparse data
        popular = (
            db.session.query(Trek.name, Trek.location, func.count(Booking.id).label("cnt"))
            .outerjoin(
                Booking,
                (Booking.trek_id == Trek.id) & (Booking.status.in_(["Booked", "Completed"])),
            )
            .group_by(Trek.id)
            .order_by(func.count(Booking.id).desc())
            .limit(10)
            .all()
        )

    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    html_path = reports_dir / f"monthly_report_{stamp}.html"
    pdf_path = reports_dir / f"monthly_report_{stamp}.pdf"

    popular_rows = "".join(
        f"<tr><td>{i}</td><td>{n}</td><td>{loc}</td><td>{c}</td></tr>"
        for i, (n, loc, c) in enumerate(popular, 1)
    )
    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Monthly Report — {label}</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#f4f7f5;color:#1b2e24;padding:24px}}
.card{{background:#fff;border-radius:12px;padding:24px;max-width:800px;margin:auto;
box-shadow:0 8px 24px rgba(27,46,36,.08)}}
h1{{color:#1f6b4a}} table{{width:100%;border-collapse:collapse;margin-top:16px}}
th,td{{border-bottom:1px solid #d7e3db;padding:8px;text-align:left}}
.stat{{display:inline-block;margin:8px 16px 8px 0;padding:12px 16px;background:#e8f5ef;border-radius:8px}}
</style></head><body><div class="card">
<h1>TrekManage Monthly Activity Report</h1>
<p>Period: <strong>{start.isoformat()}</strong> → <strong>{end.isoformat()}</strong> ({label})</p>
<div class="stat"><strong>{treks_conducted}</strong><br>Treks conducted</div>
<div class="stat"><strong>{participants}</strong><br>Users participated</div>
<h2>Popular Treks</h2>
<table><thead><tr><th>#</th><th>Trek</th><th>Location</th><th>Bookings</th></tr></thead>
<tbody>{popular_rows or '<tr><td colspan="4">No data</td></tr>'}</tbody></table>
<p style="margin-top:24px;color:#5a6b62">Generated {datetime.utcnow().isoformat()}Z</p>
</div></body></html>"""
    html_path.write_text(html, encoding="utf-8")

    # PDF via reportlab
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(pdf_path), pagesize=A4)
    story = [
        Paragraph("TrekManage Monthly Activity Report", styles["Title"]),
        Paragraph(f"Period: {start.isoformat()} → {end.isoformat()} ({label})", styles["Normal"]),
        Spacer(1, 12),
        Paragraph(f"Treks conducted: <b>{treks_conducted}</b>", styles["Normal"]),
        Paragraph(f"Users participated: <b>{participants}</b>", styles["Normal"]),
        Spacer(1, 12),
        Paragraph("Popular Treks", styles["Heading2"]),
    ]
    table_data = [["#", "Trek", "Location", "Bookings"]]
    for i, (n, loc, c) in enumerate(popular, 1):
        table_data.append([str(i), n, loc, str(c)])
    if len(table_data) == 1:
        table_data.append(["—", "No data", "—", "0"])
    table = Table(table_data, colWidths=[40, 180, 180, 70])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f6b4a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c5d9cd")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef6f1")]),
                ("PADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)
    doc.build(story)

    admin_email = current_app.config.get("ADMIN_EMAIL") or current_app.config.get(
        "ADMIN_EMAIL_SEED"
    )
    send_email(
        admin_email,
        f"Monthly Trekking Report — {label}",
        html,
        text_body=f"Monthly report for {label}. HTML: {html_path.name}, PDF: {pdf_path.name}",
    )
    send_webhook({"text": f"Monthly report ready for {label}: {pdf_path.name}"})

    return {
        "html": str(html_path),
        "pdf": str(pdf_path),
        "treks_conducted": treks_conducted,
        "participants": participants,
        "period": label,
    }


@celery.task(name="celery_app.tasks.export_user_bookings_csv")
def export_user_bookings_csv(job_id: int) -> dict:
    """User-triggered async CSV export with completion alert."""
    job = ExportJob.query.get(job_id)
    if not job:
        return {"error": "job not found"}

    job.status = "Running"
    job.message = "Generating CSV"
    db.session.commit()

    try:
        user = User.query.get(job.user_id)
        exports_dir = Path(current_app.config["EXPORTS_DIR"])
        exports_dir.mkdir(parents=True, exist_ok=True)
        filename = f"bookings_user{job.user_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        path = exports_dir / filename

        bookings = (
            Booking.query.filter_by(user_id=job.user_id)
            .order_by(Booking.booking_date.desc())
            .all()
        )
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(
                [
                    "User ID",
                    "User Name",
                    "Trek Name",
                    "Location",
                    "Booking Status",
                    "Booking Date",
                    "Trek Start",
                    "Trek End",
                    "Difficulty",
                    "Duration Days",
                ]
            )
            for b in bookings:
                trek = b.trek
                writer.writerow(
                    [
                        b.user_id,
                        user.name if user else "",
                        trek.name if trek else "",
                        trek.location if trek else "",
                        b.status,
                        b.booking_date.isoformat() if b.booking_date else "",
                        trek.start_date.isoformat() if trek and trek.start_date else "",
                        trek.end_date.isoformat() if trek and trek.end_date else "",
                        trek.difficulty if trek else "",
                        trek.duration_days if trek else "",
                    ]
                )

        job.status = "Completed"
        job.file_path = str(path)
        job.message = "Export ready — download from your dashboard"
        job.completed_at = datetime.utcnow()
        db.session.commit()

        if user:
            send_email(
                user.email,
                "Your booking history export is ready",
                f"""
                <h2>Export Complete</h2>
                <p>Hi {user.name},</p>
                <p>Your trekking booking history CSV is ready.</p>
                <p>File: <strong>{filename}</strong></p>
                <p>Download it from the TrekManage dashboard → Exports.</p>
                """,
            )
            send_webhook({"text": f"CSV export ready for {user.email}: {filename}"})

        return {"job_id": job_id, "file": str(path), "rows": len(bookings)}
    except Exception as exc:
        job.status = "Failed"
        job.message = str(exc)
        job.completed_at = datetime.utcnow()
        db.session.commit()
        return {"error": str(exc), "job_id": job_id}
