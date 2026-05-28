export default function StrategyComparison({ result, selectedView, setSelectedView }) {
  const random = result.randomFirst;
  const rarest = result.rarestFirst;
  return (
    <section className="card">
      <div className="section-header">
        <div>
          <h2>Random-First vs Rarest-First</h2>
          <p className="muted">Both strategies use the same seed, initial state, bandwidth, slots and latency.</p>
        </div>
        <span className="winner">Winner: {result.winner}</span>
      </div>
      <div className="compare-grid">
        <button
          className={`compare-card ${selectedView === 'randomFirst' ? 'active' : ''}`}
          onClick={() => setSelectedView('randomFirst')}
        >
          <span>Random-First</span>
          <strong>{random.totalTime}s</strong>
          <small>{random.totalTransfers} transfers</small>
        </button>
        <button
          className={`compare-card ${selectedView === 'rarestFirst' ? 'active' : ''}`}
          onClick={() => setSelectedView('rarestFirst')}
        >
          <span>Rarest-First</span>
          <strong>{rarest.totalTime}s</strong>
          <small>{rarest.totalTransfers} transfers</small>
        </button>
      </div>
    </section>
  );
}
