from services import BitTorrentService, generate_initial_chunks


def test_generate_initial_chunks_covers_every_chunk():
    peer_chunks = generate_initial_chunks(
        peer_count=3,
        total_chunks=10,
        probability=0.0,
        seed=1,
    )

    covered_chunks = set().union(*peer_chunks)
    assert covered_chunks == set(range(10))


def test_service_can_download_one_chunk():
    service = BitTorrentService(file_size_kb=2048, chunk_size_kb=1024)
    service.add_seeder(peer_id=0)
    service.add_leecher(peer_id=1)

    session = service.download_one_chunk(downloader_id=1)

    assert session is not None
    assert len(service.get_peer(1).chunk_ids) == 1
    assert not service.active_sessions


def test_swarm_completes_with_seeder():
    service = BitTorrentService.create_swarm(
        file_size_kb=4096,
        chunk_size_kb=1024,
        peer_count=4,
        initial_chunk_probability=0.1,
        seed=42,
        include_seeder=True,
    )

    result = service.simulate_until_complete(max_rounds=30)

    assert result["status"] == "completed"
    assert service.is_complete()
