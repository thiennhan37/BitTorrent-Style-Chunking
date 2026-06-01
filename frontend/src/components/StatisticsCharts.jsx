import { useMemo, useState } from 'react';

const CHART_COLORS = ['#2563eb', '#dc2626', '#059669', '#d97706'];

const TOPOLOGY_LABELS = {
  fullMesh: 'Full mesh',
  randomK: 'Random k-neighbor',
  ring: 'Ring',
  smallWorld: 'Small world',
  star: 'Peer 0 hub',
  custom: 'Custom adjacency',
};

const INITIAL_CHUNK_TYPE_LABELS = {
  balancedRandom: 'Balanced random',
  singleSeeder: 'Peer 0 seeder',
};

function formatTopologyMode(mode) {
  return TOPOLOGY_LABELS[mode] || mode || '—';
}

function formatInitialChunkType(mode) {
  return INITIAL_CHUNK_TYPE_LABELS[mode] || mode || '—';
}

function buildChartConfigTitle(baseTitle, topologyMode, initialChunkType) {
  return `${baseTitle} (Topology: ${formatTopologyMode(topologyMode)} · Initial chunks: ${formatInitialChunkType(initialChunkType)})`;
}

function niceTicks(maxValue, count = 5) {
  const safeMax = Math.max(Number(maxValue) || 0, 1);
  return Array.from({ length: count + 1 }, (_, index) => (safeMax / count) * index);
}

function formatTick(value) {
  if (Math.abs(value) >= 100) return Math.round(value);
  if (Math.abs(value) >= 10) return Number(value.toFixed(1));
  return Number(value.toFixed(2));
}

function chartPoint(point, xDomain, yMax, bounds) {
  const [xMin, xMax] = xDomain;
  const xSpan = Math.max(xMax - xMin, 1);
  const x = bounds.left + ((point.x - xMin) / xSpan) * bounds.width;
  const y = bounds.top + bounds.height - (point.y / Math.max(yMax, 1)) * bounds.height;
  return { x, y };
}

function linePath(points, xDomain, yMax, bounds) {
  return points
    .map((point, index) => {
      const position = chartPoint(point, xDomain, yMax, bounds);
      return `${index === 0 ? 'M' : 'L'} ${position.x.toFixed(2)} ${position.y.toFixed(2)}`;
    })
    .join(' ');
}

function ChartLegend({ items }) {
  return (
    <div className="chart-legend">
      {items.map((item) => (
        <span key={item.label}>
          <i style={{ background: item.color }} />
          {item.label}
        </span>
      ))}
    </div>
  );
}

function LineChart({ title, subtitle, xLabel, yLabel, series, xDomain, xTicks, ySuffix = '' }) {
  const bounds = { left: 58, top: 18, width: 620, height: 230 };
  const allPoints = series.flatMap((item) => item.points);
  const yMax = Math.max(...allPoints.map((point) => point.y), 1) * 1.08;
  const yTicks = niceTicks(yMax);

  return (
    <div className="chart-panel">
      <div className="section-header compact">
        <div>
          <h3>{title}</h3>
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
      </div>
      <ChartLegend items={series} />
      <svg className="stats-chart" viewBox="0 0 720 320" role="img" aria-label={title}>
        {yTicks.map((tick) => {
          const y = bounds.top + bounds.height - (tick / Math.max(yMax, 1)) * bounds.height;
          return (
            <g key={tick}>
              <line className="chart-grid-line" x1={bounds.left} x2={bounds.left + bounds.width} y1={y} y2={y} />
              <text className="chart-tick" x={bounds.left - 12} y={y + 4} textAnchor="end">
                {formatTick(tick)}
                {ySuffix}
              </text>
            </g>
          );
        })}
        {xTicks.map((tick) => {
          const x = chartPoint({ x: tick, y: 0 }, xDomain, yMax, bounds).x;
          return (
            <g key={tick}>
              <line className="chart-grid-line vertical" x1={x} x2={x} y1={bounds.top} y2={bounds.top + bounds.height} />
              <text className="chart-tick" x={x} y={bounds.top + bounds.height + 22} textAnchor="middle">
                {tick}
              </text>
            </g>
          );
        })}
        <line className="chart-axis" x1={bounds.left} x2={bounds.left + bounds.width} y1={bounds.top + bounds.height} y2={bounds.top + bounds.height} />
        <line className="chart-axis" x1={bounds.left} x2={bounds.left} y1={bounds.top} y2={bounds.top + bounds.height} />
        {series.map((item) => (
          <g key={item.label}>
            <path className="chart-line" d={linePath(item.points, xDomain, yMax, bounds)} stroke={item.color} />
            {item.points.map((point) => {
              const position = chartPoint(point, xDomain, yMax, bounds);
              return (
                <circle key={`${item.label}-${point.x}`} cx={position.x} cy={position.y} r="3.5" fill={item.color}>
                  <title>{`${item.label}: x=${point.x}, y=${point.y}${ySuffix}`}</title>
                </circle>
              );
            })}
          </g>
        ))}
        <text className="chart-axis-label" x={bounds.left + bounds.width / 2} y="312" textAnchor="middle">
          {xLabel}
        </text>
        <text className="chart-axis-label" x="18" y={bounds.top + bounds.height / 2} textAnchor="middle" transform={`rotate(-90 18 ${bounds.top + bounds.height / 2})`}>
          {yLabel}
        </text>
      </svg>
    </div>
  );
}

function GroupedBarChart({ title, subtitle, bars }) {
  const bounds = { left: 58, top: 18, width: 620, height: 230 };
  const yMax = Math.max(...bars.flatMap((bar) => [bar.randomFirst.time, bar.rarestFirst.time]), 1) * 1.12;
  const yTicks = niceTicks(yMax);
  const groupWidth = bounds.width / Math.max(bars.length, 1);
  const barWidth = Math.min(34, groupWidth * 0.25);

  return (
    <div className="chart-panel">
      <div className="section-header compact">
        <div>
          <h3>{title}</h3>
          {subtitle && <p className="muted">{subtitle}</p>}
        </div>
      </div>
      <ChartLegend
        items={[
          { label: 'Random-First', color: CHART_COLORS[0] },
          { label: 'Rarest-First', color: CHART_COLORS[1] },
        ]}
      />
      <svg className="stats-chart" viewBox="0 0 720 320" role="img" aria-label={title}>
        {yTicks.map((tick) => {
          const y = bounds.top + bounds.height - (tick / Math.max(yMax, 1)) * bounds.height;
          return (
            <g key={tick}>
              <line className="chart-grid-line" x1={bounds.left} x2={bounds.left + bounds.width} y1={y} y2={y} />
              <text className="chart-tick" x={bounds.left - 12} y={y + 4} textAnchor="end">
                {formatTick(tick)}s
              </text>
            </g>
          );
        })}
        <line className="chart-axis" x1={bounds.left} x2={bounds.left + bounds.width} y1={bounds.top + bounds.height} y2={bounds.top + bounds.height} />
        <line className="chart-axis" x1={bounds.left} x2={bounds.left} y1={bounds.top} y2={bounds.top + bounds.height} />
        {bars.map((bar, index) => {
          const center = bounds.left + groupWidth * index + groupWidth / 2;
          const randomHeight = (bar.randomFirst.time / yMax) * bounds.height;
          const rarestHeight = (bar.rarestFirst.time / yMax) * bounds.height;
          return (
            <g key={bar.topology}>
              <rect
                x={center - barWidth - 3}
                y={bounds.top + bounds.height - randomHeight}
                width={barWidth}
                height={randomHeight}
                fill={CHART_COLORS[0]}
                rx="4"
              >
                <title>{`Random-First ${bar.label}: ${bar.randomFirst.time}s`}</title>
              </rect>
              <rect
                x={center + 3}
                y={bounds.top + bounds.height - rarestHeight}
                width={barWidth}
                height={rarestHeight}
                fill={CHART_COLORS[1]}
                rx="4"
              >
                <title>{`Rarest-First ${bar.label}: ${bar.rarestFirst.time}s`}</title>
              </rect>
              <text className="chart-tick" x={center} y={bounds.top + bounds.height + 22} textAnchor="middle">
                {bar.label}
              </text>
            </g>
          );
        })}
        <text className="chart-axis-label" x={bounds.left + bounds.width / 2} y="312" textAnchor="middle">
          Topology
        </text>
        <text className="chart-axis-label" x="18" y={bounds.top + bounds.height / 2} textAnchor="middle" transform={`rotate(-90 18 ${bounds.top + bounds.height / 2})`}>
          Time (seconds)
        </text>
      </svg>
    </div>
  );
}

export default function StatisticsCharts({ form, result, loading, onBuild }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const [controls, setControls] = useState({
    seedStart: Number(form.seed || 1),
    seedEnd: Number(form.seed || 1) + 9,
    seedStep: 1,
  });

  function updateControl(field, value) {
    setControls((prev) => ({ ...prev, [field]: Number(value) }));
  }

  const seedRows = result?.charts?.seedComparison || [];
  const topologyRows = result?.charts?.topologyComparison || [];
  const rareRows = result?.charts?.rareChunkProgress || [];
  const seedTicks = seedRows.map((row) => row.seed);
  const seedDomain = seedTicks.length ? [Math.min(...seedTicks), Math.max(...seedTicks)] : [0, 1];

  const seedSeries = [
    {
      label: 'Random-First',
      color: CHART_COLORS[0],
      points: seedRows.map((row) => ({ x: row.seed, y: row.randomFirst.time })),
    },
    {
      label: 'Rarest-First',
      color: CHART_COLORS[1],
      points: seedRows.map((row) => ({ x: row.seed, y: row.rarestFirst.time })),
    },
  ];

  const rareSeries = rareRows.map((row, index) => ({
    label: row.label,
    color: CHART_COLORS[index % CHART_COLORS.length],
    points: row.points.map((point) => ({ x: point.completion, y: point.rareChunks })),
  }));

  const chartConfig = useMemo(() => {
    const source = result?.config ?? form;
    return {
      topologyMode: source.topologyMode ?? source.topology_mode ?? form.topologyMode,
      initialChunkType: source.initialDistributionMode ?? source.initial_distribution_mode ?? form.initialDistributionMode,
    };
  }, [result, form]);

  const chart3InitialChunkTypes = useMemo(() => {
    const modes = [...new Set(rareRows.map((row) => row.distributionMode).filter(Boolean))];
    if (!modes.length) return formatInitialChunkType(chartConfig.initialChunkType);
    return modes.map((mode) => formatInitialChunkType(mode)).join(' & ');
  }, [rareRows, chartConfig.initialChunkType]);

  const chart1Title = buildChartConfigTitle(
    'Chart 1: Seed range',
    chartConfig.topologyMode,
    chartConfig.initialChunkType,
  );
  const chart3Title = `Chart 3: Rare chunks by completion level (Topology: ${formatTopologyMode(chartConfig.topologyMode)} · Initial chunks: ${chart3InitialChunkTypes})`;

  return (
    <section className={`card statistics-panel${isExpanded ? '' : ' statistics-panel--collapsed'}`}>
      <div className="section-header">
        <div className="statistics-panel-title">
          <button
            type="button"
            className="statistics-panel-toggle"
            onClick={() => setIsExpanded((prev) => !prev)}
            aria-expanded={isExpanded}
            aria-label={isExpanded ? 'Hide chart statistics' : 'Show chart statistics'}
          >
            <span aria-hidden="true">{isExpanded ? '▲' : '▼'}</span>
          </button>
          <div>
            <h2>Chart Statistics</h2>
            <p className="muted">
              Run a batch with the current config to compare strategies, topologies, and rare chunk counts.
            </p>
          </div>
        </div>
        {isExpanded && (
          <div className="stats-controls">
            <label>
              Seed start
              <input type="number" value={controls.seedStart} onChange={(event) => updateControl('seedStart', event.target.value)} />
            </label>
            <label>
              Seed end
              <input type="number" value={controls.seedEnd} onChange={(event) => updateControl('seedEnd', event.target.value)} />
            </label>
            <label>
              Step
              <input type="number" min="1" value={controls.seedStep} onChange={(event) => updateControl('seedStep', event.target.value)} />
            </label>
            <button onClick={() => onBuild(controls)} disabled={loading}>
              {loading ? 'Building...' : 'Build charts'}
            </button>
          </div>
        )}
      </div>

      {isExpanded && !result && (
        <p className="muted">Click &quot;Build charts&quot; to generate 3 charts from the selected configuration.</p>
      )}

      {isExpanded && result && (
        <div className="charts-grid">
          <LineChart
            title={chart1Title}
            subtitle="X is seed; Y is completion time for Random-First and Rarest-First."
            xLabel="Seed"
            yLabel="Time (seconds)"
            ySuffix="s"
            series={seedSeries}
            xDomain={seedDomain}
            xTicks={seedTicks}
          />
          <GroupedBarChart
            title="Chart 2: Topology"
            subtitle="Each topology has two time bars: Random-First and Rarest-First."
            bars={topologyRows}
          />
          <LineChart
            title={chart3Title}
            subtitle={`X steps by ${result.completionStep}%; Y is the number of chunks owned by <= ${result.rareThreshold} peers.`}
            xLabel="System completion (%)"
            yLabel="Rare chunks"
            series={rareSeries}
            xDomain={[0, 100]}
            xTicks={Array.from({ length: 11 }, (_, index) => index * 10)}
          />
        </div>
      )}
    </section>
  );
}
