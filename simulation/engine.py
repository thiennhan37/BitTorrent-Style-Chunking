# simulation/engine.py
# mô phỏng thời gian, peer, quá trình tải chunk, cập nhật metric và cập nhật state cho frontend.

import simpy

class SimulationEngine:
    def __init__(self, config, peers, graph, scheduler, transfer_manager, metrics, state_manager):
        # Khởi tạo môi trường mô phỏng SimPy
        self.env = simpy.Environment()

        self.config = config
        self.peers = peers
        self.graph = graph

        self.scheduler = scheduler
        self.transfer_manager = transfer_manager
        self.metrics = metrics
        self.state_manager = state_manager

        self.running = False

    def get_neighbors(self, peer):
        neighbor_ids = list(self.graph.neighbors(peer.peer_id))
        return [self.peers[nid] for nid in neighbor_ids]

    def start(self):
        self.running = True

        for peer in self.peers:
            # Tạo process cho từng peer(chạy độc lập)
            self.env.process(self.peer_loop(peer))

        # tạo process cập nhật metrics 
        # Process này định kỳ lấy số liệu và cập nhật state cho frontend.
        self.env.process(self.metrics_loop())

    def peer_loop(self, peer):
        while self.running:

            if self.all_complete():
                self.running = False
                break

            if not peer.online:
                yield self.env.timeout(1)
                continue

            neighbors = self.get_neighbors(peer)

            chunk_id, source = self.scheduler.select_chunk(
                requester=peer,
                neighbors=neighbors,
                all_peers=self.peers
            )

            if chunk_id is None:
                yield self.env.timeout(1)
                continue

            yield self.env.process(
                self.transfer_manager.transfer_chunk(
                    env=self.env,
                    source=source,
                    target=peer,
                    chunk_id=chunk_id
                )
            )

    def metrics_loop(self):
        while self.running:
            self.metrics.sample(self.env.now, self.peers)

            self.state_manager.update(
                time=self.env.now,
                peers=self.peers,
                metrics=self.metrics
            )

            yield self.env.timeout(
                self.config.simulation_step
            )

    def step(self):
        self.env.step()

    def all_complete(self):
        return all(
            p.is_complete(self.config.total_chunks)
            for p in self.peers
        )