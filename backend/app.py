from __future__ import annotations

from flask import Flask, jsonify, request

try:
    from flask_cors import CORS
except ModuleNotFoundError:  # pragma: no cover
    CORS = None

from simulation.config import SimulationConfig
from simulation.service import build_statistics_charts, compare_strategies, recommend_churn_candidate, run_single_simulation


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

    @app.get("/api/config")
    def get_config():
        return jsonify(SimulationConfig().to_dict())

    @app.post("/api/simulate")
    def simulate():
        payload = request.get_json(silent=True) or {}
        # print("payload", payload)
        try:
            result = run_single_simulation(payload)
            return jsonify(result)
        except Exception as exc:  # keep API friendly for frontend demos
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/simulate/compare")
    def compare():
        payload = request.get_json(silent=True) or {}
        try:
            result = compare_strategies(payload)
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/churn/recommend")
    def recommend_churn():
        payload = request.get_json(silent=True) or {}
        try:
            result = recommend_churn_candidate(payload)
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @app.post("/api/statistics/charts")
    def statistics_charts():
        payload = request.get_json(silent=True) or {}
        try:
            result = build_statistics_charts(payload)
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
