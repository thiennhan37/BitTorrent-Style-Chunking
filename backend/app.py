from __future__ import annotations

from flask import Flask, jsonify, request

try:
    from flask_cors import CORS
except ModuleNotFoundError:  # pragma: no cover
    CORS = None

# from simulation.config import SimulationConfig
# from simulation.service import compare_strategies, recommend_churn_candidate, run_single_simulation


def create_app() -> Flask:
    app = Flask(__name__)
    if CORS is not None:
        CORS(app)
    else:
        @app.after_request
        def add_cors_headers(response):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            return response

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})


    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
