import { useMemo } from 'react';

function polarToCartesian(cx, cy, radius, angleDeg) {
  const angle = (Math.PI / 180) * angleDeg;
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  };
}

const EVENT_ORDER = { START: 0, END: 1, CANCEL: 1, CHURN: 2 };

function compareLogs(a, b) {
  const timeDiff = Number(a.time) - Number(b.time);
  if (timeDiff !== 0) return timeDiff;
  const orderDiff = (EVENT_ORDER[a.event] ?? 9) - (EVENT_ORDER[b.event] ?? 9);
  if (orderDiff !== 0) return orderDiff;
  return Number(a.transferId ?? -1) - Number(b.transferId ?? -1);
}

/** Transfers in flight at snapshot time (START seen, no END/CANCEL yet at or before maxTime). */
function activeTransfersAtTime(logs, maxTime) {
  const byId = new Map();
  const sorted = [...logs].sort(compareLogs);
  for (const log of sorted) {
    if (maxTime != null && Number(log.time) > maxTime) break;
    if (log.transferId == null || log.sourcePeer == null || log.destinationPeer == null) continue;
    if (log.event === 'START') {
      byId.set(log.transferId, log);
    } else if (log.event === 'END' || log.event === 'CANCEL') {
      byId.delete(log.transferId);
    }
  }
  return [...byId.values()];
}

export default function PeerNetworkGraph({
  logs = [],
  peerCount = 10,
  maxTime = null,
  peers = [],
  recommendedPeerId = null,
  onPeerClick = null,
}) {
  const size = 460;
  const center = size / 2;
  const radius = 170;
  const positions = Array.from({ length: peerCount }, (_, peerId) => {
    const angle = -90 + (360 * peerId) / peerCount;
    return { peerId, ...polarToCartesian(center, center, radius, angle) };
  });
  const activeTransfers = useMemo(
    () => activeTransfersAtTime(logs, maxTime),
    [logs, maxTime],
  );
  const transfersToRender = activeTransfers
    .map((log) => ({ ...log, source: positions[log.sourcePeer], dest: positions[log.destinationPeer] }))
    .filter((log) => log.source && log.dest);
  const peerState = useMemo(() => new Map(peers.map((peer) => [peer.peerId, peer])), [peers]);

  return (
    <section className="card peer-network-card">
      <h2>Peer network graph</h2>
      <p className="muted">
        {maxTime == null
          ? `Showing ${transfersToRender.length} active transfer(s).`
          : `Showing ${transfersToRender.length} transfer(s) in progress at t = ${maxTime}s.`}
      </p>
      <div className="network-graph-body">
      <svg
        className="network-svg"
        viewBox={`0 0 ${size} ${size}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="peer network graph"
      >
        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L0,6 L8,3 z" />
          </marker>
        </defs>
        {transfersToRender.map((transfer, index) => (
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
      </div>
    </section>
  );
}
