export default function ChurnPanel({
  snapshotTime,
  recommendation,
  churnEvents,
  loading,
  onRecommend,
  onApply,
  onReset,
}) {
  const recommendedPeer = recommendation?.peerId;
  const rareChunks = recommendation?.rareChunks || [];

  return (
    <section className="card churn-panel">
      <div className="section-header">
        <div>
          <h2>Peer churn what-if</h2>
          <p className="muted">Current timeline point: t = {snapshotTime == null ? '0' : snapshotTime}s</p>
        </div>
        {!!churnEvents?.length && (
          <div className="churn-badge-list">
            {churnEvents.map((event) => (
              <span key={`churn-${event.peerId}`} className={`churn-badge ${event.online ? 'online' : 'offline'}`}>
                Peer {event.peerId} {event.online ? 'online' : 'offline'} at {event.time}s
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="button-row">
        <button onClick={onRecommend} disabled={loading || snapshotTime == null}>
          {loading ? 'Searching...' : 'Find best peer to drop'}
        </button>
        {recommendation && (
          <button className="secondary" onClick={() => onApply(recommendedPeer)} disabled={loading}>
            Apply Peer {recommendedPeer} offline
          </button>
        )}
        {!!churnEvents?.length && (
          <button className="ghost" onClick={onReset} disabled={loading}>
            Back to baseline
          </button>
        )}
      </div>

      {recommendation && (
        <div className={`churn-recommendation ${recommendation.desired ? 'strong' : ''}`}>
          <strong>{recommendation.message}</strong>
          <div className="churn-facts">
            <span>Random: {recommendation.randomCompleted ? `${recommendation.randomTotalTime}s` : 'incomplete'}</span>
            <span>Rarest: {recommendation.rarestCompleted ? `${recommendation.rarestTotalTime}s` : 'incomplete'}</span>
            <span>Rare chunks: {rareChunks.length ? rareChunks.slice(0, 8).join(', ') : 'none'}</span>
            <span>Tip: click peers on graph to toggle offline → online → baseline</span>
          </div>
        </div>
      )}
    </section>
  );
}
