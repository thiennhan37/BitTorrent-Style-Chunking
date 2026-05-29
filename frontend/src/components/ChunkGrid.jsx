export default function ChunkGrid({ ownedChunks = [], totalChunks = 40 }) {
  const owned = new Set(ownedChunks);
  return (
    <div className="chunk-grid" aria-label="chunk grid">
      {Array.from({ length: totalChunks }, (_, chunkId) => (
        <span
          key={chunkId}
          className={`chunk-cell ${owned.has(chunkId) ? 'owned' : ''}`}
          title={`Chunk ${chunkId}${owned.has(chunkId) ? ' owned' : ' missing'}`}
        >
          {chunkId}
        </span>
      ))}
    </div>
  );
}
