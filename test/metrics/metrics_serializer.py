# metrics/report_generator.py

import json
import os


def generate_metrics_payload(results):
    # Convert simulation results into JSON-serializable format
    # for React frontend visualization.

    payload = []

    for result in results:

        strategy_data = {
            "strategy": result["strategy"],
            "completion_time": result["completion_time"],
            "samples": [],
        }

        for sample in result["metrics"].samples:

            strategy_data["samples"].append({
                "time": sample["time"],

                # Average completion %
                "avg_completion":
                    round(sample["avg_completion"] * 100, 2),

                # Replication status
                "replication":
                    sample["replication"],

                # Optional metrics
                "total_transfers":
                    sample.get("total_transfers", 0),

                "total_bytes":
                    sample.get("total_bytes", 0),
            })

        payload.append(strategy_data)

    return payload


def save_metrics_json(results,
                      output_path="results/metrics.json"):

    os.makedirs(os.path.dirname(output_path),
                exist_ok=True)

    payload = generate_metrics_payload(results)

    with open(output_path, "w") as f:
        json.dump(payload, f, indent=4)

    print(f"Metrics exported to {output_path}")