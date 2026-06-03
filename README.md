# BitTorrent-style Chunking: Large File Distribution

Mô phỏng phân phối file lớn theo cơ chế **BitTorrent** (chia chunk, peer vừa tải vừa chia sẻ) cho môn **Cơ sở dữ liệu phân tán / Hệ phân tán**.

Hệ thống dùng **mô phỏng discrete-event với thời gian ảo (SimPy)**: mỗi peer là một process độc lập, tự chọn chunk theo chiến lược, truyền dữ liệu theo tick và cập nhật trạng thái swarm khi transfer kết thúc — không chờ thời gian thật.

**Báo cáo chi tiết:** xem [REPORT.md](./REPORT.md).

---

## Tóm tắt

| Hạng mục | Mô tả |
|----------|--------|
| File mô phỏng | 10 MB → 40 chunk × 256 KB |
| Swarm | 10 peer |
| Chiến lược | **Random-First** vs **Rarest-First** |
| Backend | Python, Flask, SimPy |
| Frontend | React, Vite |
| Metric chính | `totalTime` — virtual time khi mọi peer **online** hoàn thành file |

---

## Tính năng

- So sánh công bằng hai chiến lược trên **cùng seed** và **cùng initial state**
- Topology mạng: full mesh, random-k, ring, star, small-world, custom adjacency
- Phân phối chunk ban đầu: balanced random hoặc single seeder (peer 0)
- Mô hình mạng: chia bandwidth theo slot, hệ số link deterministic theo cặp peer
- **Churn:** peer online/offline tại thời điểm ảo; gợi ý peer nên tắt để demo contrast giữa hai strategy
- **Thống kê batch:** so sánh nhiều seed, nhiều topology, biểu đồ chunk hiếm theo tiến độ
- Dashboard: metrics, đồ thị láng giềng, mạng truyền chunk, timeline replay, transfer log

---

## Cấu trúc thư mục

```text
BitTorrent_12_5/
├── README.md
├── REPORT.md
├── backend/
│   ├── app.py                 # Flask API
│   ├── run_compare.py         # So sánh CLI
│   ├── requirements.txt
│   ├── simulation/
│   │   ├── config.py          # Tham số mô phỏng
│   │   ├── models.py          # Peer, TransferRecord
│   │   ├── initial_state.py   # Sinh trạng thái ban đầu
│   │   ├── network.py         # Bandwidth / latency
│   │   ├── topology.py        # Đồ thị láng giềng
│   │   ├── strategies.py      # Random-First, Rarest-First
│   │   ├── simulator.py       # SimPy core
│   │   ├── service.py         # Orchestration, stats, churn
│   │   └── simpy_compat.py    # Fallback khi không có SimPy
│   └── tests/
│       └── test_simulator.py
└── frontend/
    ├── package.json
    └── src/
        ├── App.jsx
        ├── api/client.js
        ├── components/
        └── styles.css
```

---

## Yêu cầu

- **Python** 3.10+
- **Node.js** 18+ (cho frontend)

---

## Cài đặt và chạy
## docker 
Để chạy dự án này trên bất kỳ máy tính nào, yêu cầu duy nhất là máy đó đã cài đặt sẵn Docker và Docker Compose. Người dùng thực hiện theo các bước sau:

Bước 1: Tải file docker-compose.yml Người dùng có thể sao chép trực tiếp nội dung file docker-compose.yml ở trên và lưu thành một file có tên là docker-compose.yml trong một thư mục bất kỳ. Hoặc nếu họ clone cả repository về thì có sẵn file này.

Bước 2: Mở Terminal tại thư mục chứa file docker-compose.yml

Bước 3: Khởi chạy dự án Chạy câu lệnh sau để Docker tự động pull các image từ Docker Hub về và khởi động dự án:docker-compose up -d


### Backend

```bash
cd backend
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

**Linux / macOS:**

```bash
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

API mặc định: **http://localhost:5000**

Chạy so sánh nhanh trên terminal:

```bash
python run_compare.py
```

Chạy test:

```bash
python -m pytest -q
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

UI mặc định: **http://localhost:5173**

Nếu backend ở host/port khác, tạo `frontend/.env`:

```env
VITE_API_BASE=http://localhost:5000
```

---

## Sử dụng dashboard

1. Mở **http://localhost:5173** (backend phải đang chạy).
2. Chỉnh **seed**, bandwidth, latency, topology, slots, xác suất chunk ban đầu.
3. **Compare strategies** — chạy Random-First và Rarest-First trên cùng điều kiện.
4. **Simulate** — chạy một chiến lược (chọn trong panel).
5. Dùng **timeline** để replay trạng thái swarm; xem **transfer log** và **network graph**.
6. (Sau Compare) **Statistics** — batch nhiều seed/topology; **Churn** — gợi ý / bật tắt peer tại thời điểm trên timeline.

---

## API

### `GET /api/health`

Kiểm tra server.

### `GET /api/config`

Trả về cấu hình mặc định (`SimulationConfig`).

### `POST /api/simulate`

Chạy một chiến lược.

**Body mẫu:**

```json
{
  "strategy": "rarestFirst",
  "seed": 9,
  "download_bandwidth": 128,
  "upload_bandwidth": 128,
  "latencyMs": 50,
  "initialChunkProbability": 0.3,
  "initialDistributionMode": "balancedRandom",
  "topologyMode": "fullMesh",
  "neighborsPerPeer": 4,
  "max_download_slots": 2,
  "max_upload_slots": 3
}
```

**Response chính:** `totalTime`, `completed`, `logs`, `transfers`, `progressTimeline`, `finalPeers`, `chunkAvailability`, `neighborGraph`, `config`.

### `POST /api/simulate/compare`

Chạy Random-First và Rarest-First trên **cùng** `initialState` (sinh từ seed nếu không gửi).

**Body mẫu:** giống `/api/simulate` (không cần `strategy`).

**Response rút gọn:**

```json
{
  "randomFirst": { "totalTime": 42.5, "completed": true },
  "rarestFirst": { "totalTime": 38.1, "completed": true },
  "winner": "rarestFirst",
  "difference": 4.4,
  "initialState": [[0, 1, 5], "..."],
  "neighborGraph": { "0": [1, 2], "...": [] }
}
```

### `POST /api/churn/recommend`

Gợi ý peer nên **offline** tại thời điểm `time` để minh họa Random không hoàn thành trong khi Rarest vẫn xong (nếu có).

```json
{
  "seed": 9,
  "time": 12.5,
  "initialState": [],
  "churnEvents": []
}
```

### `POST /api/statistics/charts`

Chạy batch so sánh (tối đa 50 seed/lần).

```json
{
  "seedStart": 1,
  "seedEnd": 10,
  "seedStep": 1,
  "rareThreshold": 3,
  "completionStep": 5
}
```

Trả về `charts.seedComparison`, `charts.topologyComparison`, `charts.rareChunkProgress`.

---

## Tham số mô phỏng mặc định

| Tham số | Mặc định |
|---------|----------|
| `file_size_mb` | 10 |
| `chunk_size_kb` | 256 → **40 chunk** |
| `peer_count` | 10 |
| `seed` | 1 |
| `initial_chunk_probability` | 0.3 |
| `initial_distribution_mode` | `balancedRandom` |
| `topology_mode` | `fullMesh` |
| `neighbors_per_peer` | 4 |
| `bandwidth_kbps` (download) | 128 KB/s |
| `upload_bandwidth_kbps` | 128 KB/s |
| `latency_ms` | 50 |
| `max_download_slots` | 2 |
| `max_upload_slots` | 3 |
| `transfer_tick_duration` | 0.1 s |

**Điều kiện dừng:** mọi peer **đang online** sở hữu đủ 40 chunk.

---

## Chiến lược (tóm tắt)

| | Random-First | Rarest-First |
|---|--------------|--------------|
| Chọn chunk | Ngẫu nhiên trong các chunk có thể tải | Chunk có ít bản sao nhất (kể cả transfer đang chạy) |
| Chọn source | Ưu tiên thời gian ước lượng ngắn nhất | Giống Random-First |

Chi tiết thuật toán và mô hình mạng: [REPORT.md](./REPORT.md).

---

## Mô hình thời gian truyền

Transfer không dùng một công thức cố định cho toàn bộ phiên; mỗi **tick** (0.1 s) tính lại:

```text
effective_bandwidth = min(shared_upload, shared_download) × link_factor
shared_upload   = upload_bandwidth / số upload đang active
shared_download = download_bandwidth / số download đang active
```

Ước lượng tổng thời gian (test / tương thích):

```text
duration ≈ latency_s + chunk_size_kb / effective_bandwidth
```

Đơn vị bandwidth: **KB/s**. Latency và hệ số link giữa từng cặp peer là **deterministic** theo `seed` + id peer.

---

## Ghi chú kỹ thuật

- **`simpy_compat.py`:** fallback nhỏ khi không cài SimPy; môi trường dev nên cài `requirements.txt` để dùng SimPy thật.
- Peer chỉ tải từ **láng giềng** trong topology (trừ full mesh = mọi peer là láng giềng).
- So sánh hai strategy: cùng seed, initial state, topology, churn — khác biệt chỉ ở thuật toán chọn chunk.

---

## Tài liệu liên quan

| File | Nội dung |
|------|----------|
| [REPORT.md](./REPORT.md) | Báo cáo đồ án: kiến trúc, mô hình, thuật toán, kết luận |
| `backend/tests/test_simulator.py` | Test hành vi simulator |

---

## License

Đồ án học thuật — sử dụng theo quy định của lớp 
