import { useEffect, useMemo, useState } from 'react';
import ChunkGrid from './ChunkGrid.jsx';

export default function TimelineReplay({ timeline = [], totalChunks = 40, index, onIndexChange }) {
  const [internalIndex, setInternalIndex] = useState(0);
  const controlled = Number.isFinite(index);
  const activeIndex = controlled ? index : internalIndex;
  const safeIndex = Math.min(activeIndex, Math.max(timeline.length - 1, 0));
  const snapshot = timeline[safeIndex];

  useEffect(() => {
    if (!controlled) {
      setInternalIndex((prev) => Math.min(prev, Math.max(timeline.length - 1, 0)));
    }
  }, [timeline.length, controlled]);

  const summary = useMemo(() => {
    if (!snapshot) return null;
    const onlinePeers = snapshot.onlinePeers ?? snapshot.peers.length;
    return `${snapshot.completedPeers}/${onlinePeers} online peers complete - average ${snapshot.averageCompletion}%`;
  }, [snapshot]);

  if (!snapshot) return null;

  return (
    <section className="card">
      <div className="section-header">
        <div>
          <h2>Timeline replay</h2>
          <p className="muted">Move the slider to inspect peer states after transfer events.</p>
        </div>
        <span className="muted">t = {snapshot.time}s</span>
      </div>
      <input
        className="timeline-slider"
        type="range"
        min="0"
        max={Math.max(timeline.length - 1, 0)}
        value={safeIndex}
        onChange={(event) => {
          const nextIndex = Number(event.target.value);
          if (controlled) {
            onIndexChange?.(nextIndex);
          } else {
            setInternalIndex(nextIndex);
          }
        }}
      />
      <p className="muted">{summary}</p>
      <div className="timeline-peers">
        {snapshot.peers.map((peer) => (
          <div key={peer.peerId} className={`timeline-peer ${peer.online === false ? 'offline' : ''}`}>
            <strong>P{peer.peerId}</strong>
            <span>{peer.online === false ? 'offline' : `${peer.completion}%`}</span>
            <ChunkGrid ownedChunks={peer.ownedChunks} totalChunks={totalChunks} />
          </div>
        ))}
      </div>
    </section>
  );
}
