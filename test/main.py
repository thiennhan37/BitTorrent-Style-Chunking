# main.py

from services import BitTorrentService


if __name__ == "__main__":
    service = BitTorrentService.create_swarm(
        file_size_kb=10_240,
        chunk_size_kb=1_024,
        peer_count=5,
        initial_chunk_probability=0.2,
        seed=42,
        include_seeder=True,
    )

    result = service.simulate_until_complete(max_rounds=50)

    print("Simulation status:", result["status"])
    print("Round count:", result["round_count"])
    print("Summary:", result["summary"])

    print("\nPeers:")
    for peer in service.get_status()["peers"]:
        print(
            f"Peer {peer['id']}: "
            f"chunks={peer['chunk_ids']} "
            f"completion={peer['completion_percentage']}%"
        )
