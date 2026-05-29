export default function TransferLog({ logs = [] }) {
  const visibleLogs = logs.slice(-250).reverse();
  return (
    <section className="card">
      <div className="section-header">
        <h2>Transfer log</h2>
        <span className="muted">Showing latest {visibleLogs.length} events</span>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Event</th>
              <th>Source</th>
              <th>Destination</th>
              <th>Chunk</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            {visibleLogs.map((log, index) => (
              <tr key={`${log.transferId}-${log.event}-${index}`}>
                <td>{log.time}</td>
                <td><span className={`event-pill ${log.event.toLowerCase()}`}>{log.event}</span></td>
                <td>{log.sourcePeer == null ? '-' : `Peer ${log.sourcePeer}`}</td>
                <td>{log.destinationPeer == null ? '-' : `Peer ${log.destinationPeer}`}</td>
                <td>{log.chunkId == null ? '-' : log.chunkId}</td>
                <td>{log.duration}s</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
