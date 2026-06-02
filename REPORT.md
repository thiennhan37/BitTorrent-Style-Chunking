# Báo cáo đồ án

## BitTorrent-style Chunking: Large File Distribution

**Môn:** Cơ sở dữ liệu phân tán / Hệ phân tán  
**Loại hình:** Mô phỏng phân tán — so sánh chiến lược chọn chunk trong swarm peer-to-peer

---

## Mục lục

1. [Giới thiệu](#1-giới-thiệu)
2. [Bối cảnh và mục tiêu](#2-bối-cảnh-và-mục-tiêu)
3. [Kiến trúc hệ thống](#3-kiến-trúc-hệ-thống)
4. [Mô hình dữ liệu](#4-mô-hình-dữ-liệu)
5. [Mô hình mạng và topology](#5-mô-hình-mạng-và-topology)
6. [Mô phỏng event-based](#6-mô-phỏng-event-based)
7. [Chiến lược chọn chunk](#7-chiến-lược-chọn-chunk)
8. [So sánh thí nghiệm](#8-so-sánh-thí-nghiệm)
9. [Giao diện và API](#9-giao-diện-và-api)
10. [Kết quả kỳ vọng và kết luận](#10-kết-quả-kỳ-vọng-và-kết-luận)
11. [Hạn chế và hướng phát triển](#11-hạn-chế-và-hướng-phát-triển)

---

## 1. Giới thiệu

### 1.1 Vấn đề

Phân phối file lớn từ một server trung tâm tới nhiều client gặp áp lực về băng thông và điểm lỗi đơn. **BitTorrent** giải quyết bằng cách chia file thành các **piece/chunk** nhỏ; mỗi **peer** vừa tải phần còn thiếu, vừa upload phần đã có cho peer khác, tạo thành một **swarm** phân tán.

Đồ án không triển khai client BitTorrent thật mà **mô phỏng** hành vi swarm với thời gian ảo, tập trung vào câu hỏi: *chiến lược chọn chunk nào giúp hoàn thành phân phối nhanh và ổn định hơn?*

### 1.2 Hai chiến lược nghiên cứu

| Chiến lược | Ý tưởng |
|------------|---------|
| **Random-First** | Chọn ngẫu nhiên một chunk còn thiếu mà có thể tải được ngay |
| **Rarest-First** | Ưu tiên chunk **hiếm nhất** trong swarm (ít bản sao nhất) |

Metric đánh giá: **`totalTime`** — thời gian ảo khi tất cả peer **đang online** đạt 100% file.

---

## 2. Bối cảnh và mục tiêu

### 2.1 Thông số mô phỏng

| Thông số | Giá trị | Ghi chú |
|----------|--------:|---------|
| Kích thước file | 10 MB | File master cố định |
| Kích thước chunk | 256 KB | |
| Tổng số chunk | 40 | ⌈10×1024 / 256⌉ |
| Số peer | 10 | |
| Download slot / peer | 2 | Số transfer tải song song |
| Upload slot / peer | 3 | Số transfer gửi song song |
| Bandwidth mặc định | 128 KB/s | Download và upload |
| Độ trễ cơ sở | 50 ms | Có biến thiên theo cặp peer |
| Xác suất sở hữu chunk ban đầu | 0.3 | Chế độ `balancedRandom` |

### 2.2 Initial state

Trạng thái ban đầu được sinh **deterministic** theo `seed`:

1. Mỗi peer có xác suất `initial_chunk_probability` sở hữu từng chunk.
2. Mọi chunk phải có **ít nhất một** owner (swarm luôn khả thi).

**Chế độ phân phối:**

- `balancedRandom` — phân tán ngẫu nhiên đều trên swarm.
- `singleSeeder` — peer 0 giữ toàn bộ 40 chunk (kịch bản seeder đơn).

### 2.3 Mục tiêu đồ án

1. Xây dựng **simulator event-based** (SimPy) mô tả trao đổi chunk giữa peer.
2. Cài đặt và so sánh **Random-First** vs **Rarest-First** trên cùng điều kiện.
3. Cung cấp **dashboard** trực quan hóa tiến trình, log, topology, churn.
4. Phân tích ảnh hưởng **topology** và **peer rời mạng (churn)** tới kết quả.

---

## 3. Kiến trúc hệ thống

### 3.1 Sơ đồ tổng quan

```text
┌─────────────────────┐     HTTP/JSON      ┌─────────────────────┐
│  React Dashboard    │ ◄──────────────► │  Flask REST API       │
│  (Vite, port 5173)  │                  │  (port 5000)          │
└─────────────────────┘                  └──────────┬────────────┘
                                                    │
                                                    ▼
                                         ┌─────────────────────┐
                                         │  Simulation Core    │
                                         │  SimPy + Python     │
                                         │  BitTorrentSimulator│
                                         └─────────────────────┘
```

### 3.2 Backend — module và trách nhiệm

| Module | Trách nhiệm |
|--------|-------------|
| `config.py` | `SimulationConfig`: tham số file, peer, mạng, topology, slot |
| `models.py` | `Peer`, `TransferRecord`: trạng thái và ràng buộc transfer |
| `initial_state.py` | Sinh / clone ownership chunk ban đầu |
| `topology.py` | Đồ thị láng giềng (full mesh, ring, star, …) |
| `network.py` | Bandwidth chia sẻ, latency, hệ số link |
| `strategies.py` | `RandomFirstStrategy`, `RarestFirstStrategy` |
| `simulator.py` | `BitTorrentSimulator`: process peer, churn, log, timeline |
| `service.py` | `run_single_simulation`, `compare_strategies`, stats, churn recommend |
| `app.py` | Flask routes |

### 3.3 Frontend — component

| Component | Chức năng |
|-----------|-----------|
| `ConfigPanel` | Cấu hình thí nghiệm; Simulate / Compare |
| `StrategyComparison` | Chuyển xem kết quả Random vs Rarest; hiển thị winner |
| `MetricsPanel` | `totalTime`, số transfer, completion |
| `StatisticsCharts` | Batch seed, topology, đường chunk hiếm |
| `ChurnPanel` | Gợi ý và áp dụng kịch bản peer offline |
| `NeighborGraph` | Đồ thị topology (láng giềng) |
| `PeerNetworkGraph` | Hướng truyền chunk; click peer để churn |
| `PeerProgressTable` | % hoàn thành từng peer |
| `TimelineReplay` | Tua `progressTimeline` |
| `TransferLog` | Bảng log START / END / CANCEL / CHURN |

---

## 4. Mô hình dữ liệu

### 4.1 Peer

Mỗi peer `P_i` (i = 0 … 9) lưu:

| Thuộc tính | Ý nghĩa |
|------------|---------|
| `ownedChunks` | Tập chunk đã có |
| `activeDownloads` | `chunk_id → source_peer_id` đang tải |
| `activeUploads` | `destination_peer_id → chunk_id` đang gửi |
| `neighbors` | Tập peer được phép truyền nhận |
| `online` | Trạng thái churn |
| `download_bandwidth_kbps`, `upload_bandwidth_kbps` | Capacity |
| `max_download_slots`, `max_upload_slots` | Giới hạn song song |

**Điều kiện bắt đầu download** chunk `c` từ peer `S`:

1. `P` online, chưa có `c`, còn download slot.
2. `c` chưa nằm trong `activeDownloads` của `P`.
3. Tồn tại `S` online, `S ≠ P`, `S ∈ neighbors(P)`, `S` có `c`, `S` còn upload slot, `S` chưa upload cho `P`.

**Kết thúc transfer thành công:** `c` được thêm vào `ownedChunks` của `P`; slot được giải phóng.

### 4.2 Transfer log

Mỗi transfer có `transferId` và các sự kiện:

| Event | Mô tả |
|-------|--------|
| `START` | Bắt đầu truyền; khóa slot |
| `END` | Hoàn tất; destination nhận chunk |
| `CANCEL` | Hủy (ví dụ peer offline) |
| `CHURN` | Peer online / offline |

Trường log: `time`, `sourcePeer`, `destinationPeer`, `chunkId`, `duration`, `bandwidthKbps`, `latencyMs`.

### 4.3 Progress timeline

Sau mỗi thay đổi quan trọng (transfer xong, churn, …), simulator ghi **snapshot**:

- Thời điểm `time`
- `averageCompletion`, `completedPeers`, `onlinePeers`
- Trạng thái từng peer (`ownedChunks`, `completion`, …)

Frontend dùng timeline để **replay** trạng thái swarm.

---

## 5. Mô hình mạng và topology

### 5.1 Topology

Peer chỉ trao đổi với **láng giềng** trong đồ thị vô hướng:

| `topology_mode` | Mô tả |
|-----------------|--------|
| `fullMesh` | Mọi cặp peer kết nối |
| `randomK` | Mỗi peer có k láng giềng ngẫu nhiên (theo seed) |
| `ring` | Vòng |
| `star` | Hub (peer 0) nối tất cả |
| `smallWorld` | Watts–Strogatz (rewire) |
| `custom` | Adjacency list / edge list từ UI |

### 5.2 Bandwidth và latency

Khác với mô hình “một công thức cố định cho cả phiên”, simulator dùng **tick-based transfer**:

- Mỗi tick `transfer_tick_duration` (0.1 s), tính lại `effective_bandwidth`.
- **Upload** của source chia đều cho số upload đang active.
- **Download** của destination chia đều cho số download đang active.
- `effective_bandwidth = min(shared_upload, shared_download) × link_factor`
- `link_factor` ∈ [0.65, 1.0] và latency factor ∈ [1.0, 1.75] — **deterministic** theo `(seed, source_id, dest_id)` để so sánh hai strategy **công bằng**.

Ước lượng (test / báo cáo):

```text
duration ≈ (latency_ms / 1000) + chunk_size_kb / effective_bandwidth
```

Đơn vị bandwidth: **KB/s**.

### 5.3 Chọn source peer

Sau khi chọn chunk, cả hai strategy chọn source theo thứ tự ưu tiên:

1. Thời gian truyền ước lượng ngắn nhất.
2. Ít upload đang active hơn.
3. Tie-break ngẫu nhiên (cùng RNG của strategy).

---

## 6. Mô phỏng event-based

### 6.1 Tại sao không dùng round đồng bộ?

Trong thực tế, peer hành động **bất đồng bộ**: vừa tải vừa gửi, nhiều transfer chồng lấn. **Discrete-event simulation (DES)** với **SimPy** mô tả đúng hơn: mỗi peer là một **coroutine/process**, thời gian chỉ nhảy tới event tiếp theo (virtual time).

### 6.2 Luồng một peer

```text
while chưa đủ 40 chunk và peer online:
    chờ swarm_event (có cơ hội transfer mới)
    chunk ← strategy.select_chunk(peer, swarm)
    source ← strategy.select_source(peer, swarm, chunk)
    if chunk và source:
        reserve download/upload slot
        log START
        loop từng tick:
            tính bytes truyền theo effective_bandwidth hiện tại
            yield timeout(tick)
        nhận chunk, log END
        wake swarm (đánh thức peer khác)
    else:
        yield timeout(polling_interval) hoặc chờ swarm_event
```

### 6.3 Swarm event

`swarm_event` là cơ chế **đánh thức** toàn bộ peer khi:

- Transfer kết thúc → chunk mới xuất hiện / slot giải phóng.
- Churn thay đổi trạng thái online.

Tránh busy-polling liên tục trên toàn mạng.

### 6.4 Churn

Người dùng (hoặc API) định nghĩa danh sách sự kiện `{ time, peerId, online }`:

- Tại thời điểm ảo tương ứng, peer chuyển online/offline.
- Transfer liên quan peer offline bị **CANCEL**; slot được giải phóng.
- Điều kiện hoàn thành chỉ xét peer **đang online**.

API `recommend_churn` thử lần lượt tắt từng peer tại thời điểm snapshot để tìm kịch bản: Random-First **không** hoàn thành nhưng Rarest-First **vẫn** hoàn thành — phục vụ demo trong báo cáo.

---

## 7. Chiến lược chọn chunk

### 7.1 Random-First

**Thuật toán:**

1. `missing ←` các chunk peer chưa có.
2. `candidates ← { c ∈ missing | ∃ source upload được c ngay }`.
3. Nếu `candidates` rỗng → không chọn.
4. Chọn `rng.choice(candidates)`.

**Đặc điểm:** Đơn giản, không cần thống kê toàn swarm. Có thể bỏ qua chunk hiếm → nhiều peer cùng “đuổi” chunk phổ biến, chunk hiếm lan chậm → **nghẽn cuối**.

### 7.2 Rarest-First (phiên bản trong đồ án)

**Thuật toán:**

Với mỗi `c ∈ missing` có thể tải:

- `copies` = số peer có thể làm source cho `c`.
- `in_flight` = số peer **đang download** `c`.
- `projected_copies = copies + in_flight`.

Chọn `c` có `projected_copies` **nhỏ nhất**; hòa thì chọn ngẫu nhiên.

**Lý do cộng `in_flight`:** Tránh nhiều peer cùng chen vào một chunk hiếm đã có người tải, trong khi chunk hiếm khác vẫn chỉ nằm ở một peer.

**Đặc điểm:** Ưu tiên nhân bản chunk hiếm sớm → giảm nguy cơ bottleneck khi gần 100% completion.

### 7.3 So sánh trực quan

```text
Swarm ban đầu (ví dụ):
  Chunk A: 8 peer có    Chunk B: 2 peer có    Chunk C: 1 peer có

Random-First có thể chọn A nhiều lần (xác suất cao trong candidates).

Rarest-First ưu tiên C, sau đó B → phân tán bản sao đều hơn trước khi kết thúc.
```

---

## 8. So sánh thí nghiệm

### 8.1 Nguyên tắc công bằng

Hai lượt chạy **Random-First** và **Rarest-First** dùng chung:

- `seed`, `initialState` (clone), topology, bandwidth, latency, slots, `churnEvents`.

Khác biệt duy nhất: class strategy trong `strategies.py`.

### 8.2 Winner

`compare_strategies` xác định `winner`:

1. Nếu chỉ một strategy `completed` → strategy đó thắng.
2. Nếu cả hai hoàn thành → `totalTime` nhỏ hơn thắng.
3. Hòa thời gian → `tie`.

### 8.3 Thí nghiệm mở rộng (Statistics)

Endpoint `/api/statistics/charts` chạy batch:

| Biểu đồ | Nội dung |
|---------|----------|
| `seedComparison` | `totalTime` theo từng seed (1…N) |
| `topologyComparison` | So sánh full mesh, random-k, ring, star, small-world |
| `rareChunkProgress` | Số chunk “hiếm” (≤ `rareThreshold` bản sao) theo % completion hệ thống |

Giới hạn: tối đa **50** seed mỗi request.

---

## 9. Giao diện và API

### 9.1 Luồng sử dụng điển hình

1. Cấu hình tham số trên dashboard.
2. **Compare strategies** → nhận `randomFirst`, `rarestFirst`, `winner`.
3. Xem **NeighborGraph** (topology) và **PeerNetworkGraph** (transfer).
4. **Timeline replay** tại các mốc thời gian.
5. (Tuỳ chọn) **Recommend churn** tại mốc timeline → áp dụng → so sánh lại.
6. **Build statistics** với dải seed để vẽ biểu đồ tổng hợp.

### 9.2 API tóm tắt

| Method | Path | Mô tả |
|--------|------|--------|
| GET | `/api/health` | Health check |
| GET | `/api/config` | Cấu hình mặc định |
| POST | `/api/simulate` | Một strategy |
| POST | `/api/simulate/compare` | Hai strategy |
| POST | `/api/churn/recommend` | Gợi ý peer tắt |
| POST | `/api/statistics/charts` | Batch charts |

Chi tiết request/response: [README.md](./README.md).

---

## 10. Kết quả kỳ vọng và kết luận

### 10.1 Kết quả kỳ vọng

- Với phân phối chunk ban đầu **không đều** (`balancedRandom`, xác suất thấp), **Rarest-First** thường có `totalTime` nhỏ hơn hoặc ít nhạy với seed hơn **Random-First**.
- Với `singleSeeder`, chênh lệch có thể nhỏ hơn vì bottleneck ban đầu rõ ràng ở peer 0.
- Topology thưa (ring, random-k) làm tăng `totalTime`; churn có thể khiến Random-First **không hoàn thành** trong khi Rarest-First vẫn xong — minh họa vai trò chunk hiếm và nhân bản sớm.

### 10.2 Kết luận

Đồ án đã xây dựng được:

1. **Simulation core** event-based (SimPy) mô tả swarm BitTorrent-style với slot, topology, churn.
2. Hai chiến lược **Random-First** và **Rarest-First** (có cải tiến projected copies).
3. **REST API** và **React dashboard** hỗ trợ so sánh, replay, thống kê và demo churn.

Kết luận học thuật: trong mô hình phân phối chunk phân tán, **ưu tiên chunk hiếm** (Rarest-First) là heuristic quan trọng giúp tránh deadlock phân phối ở giai đoạn cuối, so với chọn chunk ngẫu nhiên đơn thuần.

---

## 11. Hạn chế và hướng phát triển

### 11.1 Hạn chế

Đây là **mô phỏng giáo dục**, không phải client BitTorrent production:

- Không có tracker/DHT, handshake, mã hóa piece, SHA1 verify.
- Không có tit-for-tat choking / optimistic unchoking chuẩn protocol.
- Bandwidth đồng nhất theo peer (chưa heterogeneity đầy đủ).
- Không tách/ghép file nhị phân thật trên đĩa.
- Peer “biết” availability toàn swarm khi chọn Rarest-First (mô hình lý tưởng hóa).

### 11.2 Hướng phát triển

1. Bandwidth và latency **khác nhau từng peer**.
2. Mô hình **choking** gần BitTorrent thật hơn.
3. Tracker đơn giản hoặc gossip availability (giảm giả định global view).
4. Tích hợp **file splitter/assembler** cho file thật.
5. Lưu batch experiment vào **database** (PostgreSQL/SQLite) để phân tích dài hạn.
6. Export PDF/CSV kết quả từ dashboard.

---

## Phụ lục A — Công nghệ

| Tầng | Công nghệ | Phiên bản (requirements) |
|------|-----------|---------------------------|
| Backend runtime | Python 3.10+ | — |
| Web framework | Flask | 3.1.0 |
| CORS | Flask-Cors | 5.0.0 |
| Simulation | SimPy | 4.1.1 |
| Test | pytest | 9.0.2 |
| Frontend | React, Vite | latest (package.json) |

## Phụ lục B — Cấu trúc response mô phỏng

```json
{
  "strategy": "rarestFirst",
  "strategyName": "Rarest-First",
  "totalTime": 38.4,
  "completed": true,
  "totalTransfers": 312,
  "logs": [],
  "transfers": [],
  "progressTimeline": [],
  "finalPeers": [],
  "chunkAvailability": { "0": 10, "1": 9 },
  "neighborGraph": { "0": [1, 2] },
  "config": {}
}
```

---

*Tài liệu đồng bộ với mã nguồn tại nhánh hiện tại. Hướng dẫn cài đặt nhanh: [README.md](./README.md).*
