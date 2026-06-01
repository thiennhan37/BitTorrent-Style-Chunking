export default function ConfigPanel({
  config,
  form,
  setForm,
  strategy,
  setStrategy,
  onCompare,
  onSimulate,
  loading,
}) {
  function updateField(field, value) {
    const numericFields = new Set([
      'seed',
      'download_bandwidth',
      'upload_bandwidth',
      'latencyMs',
      'initialChunkProbability',
      'neighborsPerPeer',
      'topologyRewireProbability',
      'max_download_slots',
      'max_upload_slots',
    ]);
    setForm((prev) => ({ ...prev, [field]: numericFields.has(field) ? Number(value) : value }));
  }

  return (
    <section className="card config-panel">
      <div>
        <h2>Simulation Config</h2>
        <p className="muted">
          Default: {config?.file_size_mb || 10}MB file, {config?.chunk_size_kb || 256}KB/chunk,
          {' '}{config?.totalChunks || 40} chunks, {config?.peer_count || 10} peers.
        </p>
      </div>

      {/* Bọc toàn bộ các nhóm form vào form-container */}
      <div className="form-container">
        
        {/* Nhóm 1: Network Settings */}
        <div className="form-group-section">
          <h3 style={{ fontSize: '1rem', marginBottom: '12px', marginTop: '0' }}>Network Settings</h3>
          <div className="form-grid">
            <div className="form-field">
              <label htmlFor="seed">Seed</label>
              <input id="seed" type="number" value={form.seed} onChange={(e) => updateField('seed', e.target.value)} />
            </div>
            <div className="form-field">
              <label htmlFor="download_bandwidth">Download bandwidth (KB/s)</label>
              <input
                id="download_bandwidth"
                type="number"
                min="1"
                value={form.download_bandwidth}
                onChange={(e) => updateField('download_bandwidth', e.target.value)}
              />
            </div>
            <div className="form-field">
              <label htmlFor="upload_bandwidth">Upload bandwidth (KB/s)</label>
              <input
                id="upload_bandwidth"
                type="number"
                min="1"
                value={form.upload_bandwidth}
                onChange={(e) => updateField('upload_bandwidth', e.target.value)}
              />
            </div>
            <div className="form-field">
              <label htmlFor="latencyMs">Latency (ms)</label>
              <input
                id="latencyMs"
                type="number"
                min="0"
                value={form.latencyMs}
                onChange={(e) => updateField('latencyMs', e.target.value)}
              />
            </div>
          </div>
        </div>

        {/* Nhóm 2: Simulation & Strategy Settings */}
        <div className="form-group-section">
          <h3 style={{ fontSize: '1rem', marginBottom: '12px', marginTop: '8px' }}>Simulation & Strategy Settings</h3>
          <div className="form-grid">
            <div className="form-field">
              <label htmlFor="initialChunkProbability">Initial probability</label>
              <input
                id="initialChunkProbability"
                type="number"
                min="0.05"
                max="0.95"
                step="0.01"
                value={form.initialChunkProbability}
                onChange={(e) => updateField('initialChunkProbability', e.target.value)}
              />
            </div>
            <div className="form-field">
              <label htmlFor="initialDistributionMode">Initial chunks</label>
              <select
                id="initialDistributionMode"
                value={form.initialDistributionMode}
                onChange={(e) => updateField('initialDistributionMode', e.target.value)}
              >
                <option value="balancedRandom">Balanced random</option>
                <option value="singleSeeder">Peer 0 seeder</option>
              </select>
            </div>
            <div className="form-field">
              <label htmlFor="max_download_slots">Max download slots</label>
              <input
                id="max_download_slots"
                type="number"
                min="1"
                value={form.max_download_slots}
                onChange={(e) => updateField('max_download_slots', e.target.value)}
              />
            </div>
            <div className="form-field">
              <label htmlFor="max_upload_slots">Max upload slots</label>
              <input
                id="max_upload_slots"
                type="number"
                min="1"
                value={form.max_upload_slots}
                onChange={(e) => updateField('max_upload_slots', e.target.value)}
              />
            </div>
            <div className="form-field">
              <label htmlFor="strategy">Single strategy</label>
              <select id="strategy" value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                <option value="randomFirst">Random-First</option>
                <option value="rarestFirst">Rarest-First</option>
              </select>
            </div>
          </div>
        </div>

        <div className="form-group-section">
          <h3 style={{ fontSize: '1rem', marginBottom: '12px', marginTop: '8px' }}>Neighbor Topology</h3>
          <div className="form-grid">
            <div className="form-field">
              <label htmlFor="topologyMode">Topology mode</label>
              <select id="topologyMode" value={form.topologyMode} onChange={(e) => updateField('topologyMode', e.target.value)}>
                <option value="fullMesh">Full mesh</option>
                <option value="randomK">Random k-neighbor</option>
                <option value="ring">Ring</option>
                <option value="smallWorld">Small world</option>
                <option value="star">Peer 0 hub</option>
                <option value="custom">Custom adjacency</option>
              </select>
            </div>
            <div className="form-field">
              <label htmlFor="neighborsPerPeer">Neighbors per peer</label>
              <input
                id="neighborsPerPeer"
                type="number"
                min={form.topologyMode === 'smallWorld' ? '2' : '1'}
                step={form.topologyMode === 'smallWorld' ? '2' : '1'}
                value={form.neighborsPerPeer}
                onChange={(e) => updateField('neighborsPerPeer', e.target.value)}
                disabled={!['randomK', 'smallWorld'].includes(form.topologyMode)}
              />
            </div>
            <div className="form-field">
              <label htmlFor="topologyRewireProbability">Rewire probability</label>
              <input
                id="topologyRewireProbability"
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={form.topologyRewireProbability}
                onChange={(e) => updateField('topologyRewireProbability', e.target.value)}
                disabled={form.topologyMode !== 'smallWorld'}
              />
            </div>
            <div className="form-field form-field-wide">
              <label htmlFor="topologyAdjacency">Custom adjacency</label>
              <textarea
                id="topologyAdjacency"
                rows="4"
                value={form.topologyAdjacency}
                onChange={(e) => updateField('topologyAdjacency', e.target.value)}
                placeholder={'0: 1, 2\n1: 0, 3'}
                disabled={form.topologyMode !== 'custom'}
              />
            </div>
          </div>
        </div>

      </div>

      <div className="button-row">
        <button onClick={onCompare} disabled={loading}>{loading ? 'Running...' : 'Compare strategies'}</button>
        <button className="secondary" onClick={onSimulate} disabled={loading}>Run selected strategy</button>
      </div>
    </section>
  );
}
