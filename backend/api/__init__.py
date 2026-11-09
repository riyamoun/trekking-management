"""Register API blueprints."""

from backend.api.admin import admin_bp
from backend.api.auth import auth_bp
from backend.api.staff import staff_bp
from backend.api.treks import treks_bp
from backend.api.user import user_bp


def register_blueprints(app) -> None:
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(staff_bp, url_prefix="/api/staff")
    app.register_blueprint(user_bp, url_prefix="/api/user")
    app.register_blueprint(treks_bp, url_prefix="/api/treks")
