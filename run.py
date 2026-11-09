"""Entry point for the TrekManage Flask API + Vue SPA."""

import os

from backend import create_app

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "3847"))
    app.run(host="0.0.0.0", port=port, debug=True)
