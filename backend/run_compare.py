from __future__ import annotations

import json

from simulation.service import compare_strategies


if __name__ == "__main__":
    result = compare_strategies(
        {
            "seed": 1,
            "download_bandwidth": 128,
            "upload_bandwidth": 128,
            "latencyMs": 50,
            "initialChunkProbability": 0.3,
        }
    )
    summary = {
        "randomFirst": {
            "totalTime": result["randomFirst"]["totalTime"],
            "totalTransfers": result["randomFirst"]["totalTransfers"],
            "completed": result["randomFirst"]["completed"],
        },
        "rarestFirst": {
            "totalTime": result["rarestFirst"]["totalTime"],
            "totalTransfers": result["rarestFirst"]["totalTransfers"],
            "completed": result["rarestFirst"]["completed"],
        },
        "winner": result["winner"],
        "difference": result["difference"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
