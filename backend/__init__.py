"""Flask application factory for Trekking Management Application."""

from pathlib import Path

from flask import Flask, send_from_directory
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

    # Ensure runtime directories exist
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    Path(app.config["EXPORTS_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["REPORTS_DIR"]).mkdir(parents=True, exist_ok=True)

    CORS(app, supports_credentials=True)
    db.init_app(app)
    jwt.init_app(app)
    redis_client.init_app(app)

    from backend.api import register_blueprints

    register_blueprints(app)

    @app.route("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.errorhandler(404)
    def spa_fallback(e):
        # API 404s stay JSON; unknown UI routes fall back to SPA entry
        from flask import request

        if request.path.startswith("/api/"):
            return {"error": "Not found"}, 404
        if Path(request.path).suffix:
            return {"error": "Not found"}, 404
        return send_from_directory(frontend_dir, "index.html")

    with app.app_context():
        from backend import models  # noqa: F401

        db.create_all()
        from backend.seed import seed_database

        seed_database()

    return app
