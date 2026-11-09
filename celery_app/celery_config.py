"""Celery instance bound to Flask app context."""

import os

from celery import Celery
from celery.schedules import crontab
from dotenv import load_dotenv

load_dotenv()


def make_celery() -> Celery:
    broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

    celery = Celery("trekmanage", broker=broker, backend=backend, include=["celery_app.tasks"])
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Asia/Kolkata",
        enable_utc=True,
        beat_schedule={
            # Daily reminders at 08:00 IST
            "daily-trek-reminders": {
                "task": "celery_app.tasks.send_daily_reminders",
                "schedule": crontab(hour=8, minute=0),
            },
            # Monthly admin report on 1st at 09:00 IST
            "monthly-admin-report": {
                "task": "celery_app.tasks.generate_monthly_report",
                "schedule": crontab(day_of_month=1, hour=9, minute=0),
            },
        },
    )
    return celery


celery = make_celery()


class ContextTask(celery.Task):
    """Ensure Flask app context for DB access inside tasks."""

    def __call__(self, *args, **kwargs):
        from backend import create_app

        app = create_app()
        with app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask
