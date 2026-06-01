import { useMemo } from 'react';

function polarToCartesian(cx, cy, radius, angleDeg) {
  const angle = (Math.PI / 180) * angleDeg;
  return {
    x: cx + radius * Math.cos(angle),
    y: cy + radius * Math.sin(angle),
  };
}

export default function NeighborGraph({ graph = null, peerCount = 10, peers = [] }) {
  const size = 460;
  const center = size / 2;
  const radius = 168;
  const positions = Array.from({ length: peerCount }, (_, peerId) => {
    const angle = -90 + (360 * peerId) / peerCount;
    return { peerId, ...polarToCartesian(center, center, radius, angle) };
  });
  const positionByPeer = useMemo(() => new Map(positions.map((node) => [node.peerId, node])), [positions]);
  const peerState = useMemo(() => new Map(peers.map((peer) => [peer.peerId, peer])), [peers]);
  const edges = graph?.edges || [];
  const modeLabel = graph?.mode || 'fullMesh';

  return (
    <section className="card neighbor-card">
      <div className="section-header">
        <div>
          <h2>Neighbor topology</h2>
          <p className="muted">
            {modeLabel} - {edges.length} links
          </p>
        </div>
      </div>
      <svg className="neighbor-svg" viewBox={`0 0 ${size} ${size}`} role="img" aria-label="neighbor topology graph">
        {edges.map((edge) => {
          const source = positionByPeer.get(edge.source);
          const target = positionByPeer.get(edge.target);
          if (!source || !target) return null;
          return (
            <line
              key={`${edge.source}-${edge.target}`}
              className="neighbor-edge"
              x1={source.x}
              y1={source.y}
              x2={target.x}
              y2={target.y}
            />
          );
        })}
        {positions.map((node) => {
          const state = peerState.get(node.peerId);
          const online = state?.online ?? true;
          return (
            <g key={node.peerId} className={`node ${online ? '' : 'offline'}`}>
              <circle cx={node.x} cy={node.y} r="22" />
              <text x={node.x} y={node.y + 5} fontSize="13">P{node.peerId}</text>
            </g>
          );
        })}
      </svg>
    </section>
  );
}
