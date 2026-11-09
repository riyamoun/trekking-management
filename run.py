"""Entry point for the TrekManage Flask API + Vue SPA."""

import os

from backend import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "3847"))
    # Debug is off unless explicitly enabled — never default to True in production
    debug = os.getenv("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug)
