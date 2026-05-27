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

      </div>

      <div className="button-row">
        <button onClick={onCompare} disabled={loading}>{loading ? 'Running...' : 'Compare strategies'}</button>
        <button className="secondary" onClick={onSimulate} disabled={loading}>Run selected strategy</button>
      </div>
    </section>
  );
}