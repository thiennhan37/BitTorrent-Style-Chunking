function Stat({ label, value }) {
  return (
    <div className="stat">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export default function MetricsPanel({ result, compareResult }) {
  const onlinePeers = result.finalPeers?.filter((peer) => peer.online !== false) || [];
  const completedPeers = onlinePeers.filter((peer) => peer.completion === 100).length;
  return (
    <section className="card">
      <h2>Metrics: {result.strategyName}</h2>
      <div className="stats-grid">
        <Stat label="Status" value={result.completed ? 'Completed' : 'Incomplete'} />
        <Stat label="Total virtual time" value={`${result.totalTime}s`} />
        <Stat label="Transfers" value={result.totalTransfers} />
        <Stat label="Completed online peers" value={`${completedPeers}/${onlinePeers.length || 0}`} />
        {compareResult && <Stat label="Winner" value={compareResult.winner} />}
        {compareResult && <Stat label="Difference" value={`${compareResult.difference}s`} />}
      </div>
    </section>
  );
}
