"""Flask application factory for Trekking Management Application."""

from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from backend.config import Config
from backend.extensions import db, jwt, redis_client


def create_app(config_class: type = Config) -> Flask:
    root = Path(__file__).resolve().parent.parent
    frontend_dir = root / "frontend"

    app = Flask(
        __name__,
        static_folder=str(frontend_dir),
        static_url_path="",
        instance_relative_config=True,
    )
    app.config.from_object(config_class)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["EXPORTS_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["REPORTS_DIR"]).mkdir(parents=True, exist_ok=True)

    # Same-origin SPA by default; optional explicit CORS allowlist (no wildcard)
    origins = app.config.get("CORS_ORIGINS") or []
    if origins:
        CORS(
            app,
            resources={r"/api/*": {"origins": origins}},
            supports_credentials=True,
        )

    db.init_app(app)
    jwt.init_app(app)
    redis_client.init_app(app)

    from backend.api import register_blueprints

    register_blueprints(app)

    @app.get("/api/meta")
    def meta():
        """Public deployment metadata — never includes credentials."""
        return jsonify(
            {
                "app": "TrekManage",
                "version": "2.1.0",
                "lab_mode": bool(app.config.get("SEED_DEMO_DATA")),
                "show_lab_hints": bool(app.config.get("SHOW_LAB_HINTS")),
                "auth": "JWT",
                "cache": "Redis",
                "jobs": "Celery",
            }
        )

    @app.get("/api/health")
    def health():
        redis_ok = False
        try:
            redis_ok = bool(redis_client.client.ping())
        except Exception:
            redis_ok = False
        return jsonify({"status": "ok", "redis": redis_ok})

    @app.route("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.errorhandler(404)
    def spa_fallback(e):
        from flask import request

        if request.path.startswith("/api/"):
            return {"error": "Not found"}, 404
        if Path(request.path).suffix:
            return {"error": "Not found"}, 404
        return send_from_directory(frontend_dir, "index.html")

    with app.app_context():
        from backend import models  # noqa: F401
        from backend.schema_utils import ensure_sqlite_columns
        from backend.seed import seed_database

        db.create_all()
        ensure_sqlite_columns()
        seed_database()

    return app
