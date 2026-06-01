const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000';

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || `Request failed: ${response.status}`);
  }
  return data;
}

export function getConfig() {
  return request('/api/config');
}

export function simulate(payload) {
  return request('/api/simulate', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function compareStrategies(payload) {
  return request('/api/simulate/compare', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function recommendChurn(payload) {
  return request('/api/churn/recommend', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export function buildStatisticsCharts(payload) {
  return request('/api/statistics/charts', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
