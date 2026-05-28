import { useMemo, useState } from 'react';

function polarToCartesian(cx, cy, radius, angleDeg) {
  const angle = (Math.PI / 180) * angleDeg;
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  };
}

export default function PeerNetworkGraph({
  logs = [],
  peerCount = 10,
  maxTime = null,
  peers = [],
  recommendedPeerId = null,
  onPeerClick = null,
}) {
  const [showAllTransfers, setShowAllTransfers] = useState(false);
  const size = 460;
  const center = size / 2;
  const radius = 170;
  const positions = Array.from({ length: peerCount }, (_, peerId) => {
    const angle = -90 + (360 * peerId) / peerCount;
    return { peerId, ...polarToCartesian(center, center, radius, angle) };
  });
  const completedTransfers = useMemo(
    () => logs.filter((log) => log.event === 'END' && (maxTime == null || Number(log.time) <= maxTime)),
    [logs, maxTime],
  );
  const transfersToRender = showAllTransfers ? completedTransfers : completedTransfers.slice(-12);
  const recentTransfers = transfersToRender
    .map((log) => ({ ...log, source: positions[log.sourcePeer], dest: positions[log.destinationPeer] }))
    .filter((log) => log.source && log.dest);
  const peerState = useMemo(() => new Map(peers.map((peer) => [peer.peerId, peer])), [peers]);

  return (
    <section className="card">
      <h2>Peer network graph</h2>
      <p className="muted">
        Showing {recentTransfers.length}/{completedTransfers.length} completed transfers as arrows.
      </p>
      <label className="graph-toggle">
        <input
          type="checkbox"
          checked={showAllTransfers}
          onChange={(event) => setShowAllTransfers(event.target.checked)}
        />
        Show all completed transfers
      </label>
      <svg className="network-svg" viewBox={`0 0 ${size} ${size}`} role="img" aria-label="peer network graph">
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L8,3 z" />
          </marker>
        </defs>
        {recentTransfers.map((transfer, index) => (
          <g key={`${transfer.transferId}-${index}`} className="edge">
            <line
              x1={transfer.source.x}
              y1={transfer.source.y}
              x2={transfer.dest.x}
              y2={transfer.dest.y}
              markerEnd="url(#arrow)"
            />
            <text
              x={(transfer.source.x + transfer.dest.x) / 2}
              y={(transfer.source.y + transfer.dest.y) / 2}
            >
              c{transfer.chunkId}
            </text>
          </g>
        ))}
        {positions.map((node) => {
          const state = peerState.get(node.peerId);
          const online = state?.online ?? true;
          const recommended = recommendedPeerId === node.peerId;
          return (
            <g
              key={node.peerId}
              className={`node ${online ? '' : 'offline'} ${recommended ? 'recommended' : ''}`}
              role={onPeerClick ? 'button' : undefined}
              tabIndex={onPeerClick ? 0 : undefined}
              onClick={() => onPeerClick?.(node.peerId)}
              onKeyDown={(event) => {
                if ((event.key === 'Enter' || event.key === ' ') && onPeerClick) {
                  event.preventDefault();
                  onPeerClick(node.peerId);
                }
              }}
            >
              <circle cx={node.x} cy={node.y} r="22" />
              <text x={node.x} y={node.y + 5}>P{node.peerId}</text>
            </g>
          );
        })}
      </svg>
    </section>
  );
}
