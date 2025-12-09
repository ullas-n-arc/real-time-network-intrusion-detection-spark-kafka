/**
 * NIDS Dashboard - Analytics Page JavaScript
 * Time-series analysis, metrics aggregation, and trend visualization
 */

// ============================================
// Analytics State
// ============================================

const AnalyticsState = {
  alerts: [],
  sessions: [],
  timeRange: '24h', // '1h', '6h', '24h', '7d', '30d', 'custom'
  customDateFrom: null,
  customDateTo: null,
  charts: {},
  autoRefresh: true,
  refreshInterval: null,
};

// ============================================
// Data Loading
// ============================================

async function loadAnalyticsData() {
  try {
    app.showLoading();
    
    const [alerts, sessions] = await Promise.all([
      api.getAlerts({ limit: 5000 }),
      api.getSessions(),
    ]);
    
    AnalyticsState.alerts = alerts;
    AnalyticsState.sessions = sessions;
    
    updateMetrics();
    updateCharts();
    updateTopAttacks();
    updateSessionStatistics();
    
  } catch (error) {
    app.handleError(error, 'Loading analytics data');
  } finally {
    app.hideLoading();
  }
}

// ============================================
// Metrics Calculation
// ============================================

function updateMetrics() {
  const filtered = filterAlertsByTimeRange();
  
  const totalAlerts = filtered.length;
  const highSeverity = filtered.filter(a => a.severity === 'high').length;
  const uniqueAttackTypes = new Set(filtered.map(a => a.attack_type)).size;
  const avgConfidence = filtered.length > 0
    ? filtered.reduce((sum, a) => sum + (a.prediction_score || 0), 0) / filtered.length
    : 0;
  
  updateMetricCard('total-alerts-metric', totalAlerts, 'alerts');
  updateMetricCard('high-severity-metric', highSeverity, 'high severity');
  updateMetricCard('attack-types-metric', uniqueAttackTypes, 'types');
  updateMetricCard('avg-confidence-metric', `${(avgConfidence * 100).toFixed(1)}%`, '');
}

function updateMetricCard(id, value, label) {
  const card = u.$(`#${id}`);
  if (!card) return;
  
  const valueEl = card.querySelector('.metric-value');
  const labelEl = card.querySelector('.metric-label');
  
  if (valueEl) valueEl.textContent = typeof value === 'number' ? u.formatNumber(value) : value;
  if (labelEl && label) labelEl.textContent = label;
}

function filterAlertsByTimeRange() {
  const now = new Date();
  let cutoff;
  
  switch (AnalyticsState.timeRange) {
    case '1h':
      cutoff = new Date(now - 60 * 60 * 1000);
      break;
    case '6h':
      cutoff = new Date(now - 6 * 60 * 60 * 1000);
      break;
    case '24h':
      cutoff = new Date(now - 24 * 60 * 60 * 1000);
      break;
    case '7d':
      cutoff = new Date(now - 7 * 24 * 60 * 60 * 1000);
      break;
    case '30d':
      cutoff = new Date(now - 30 * 24 * 60 * 60 * 1000);
      break;
    case 'custom':
      if (!AnalyticsState.customDateFrom) return AnalyticsState.alerts;
      cutoff = new Date(AnalyticsState.customDateFrom);
      break;
    default:
      cutoff = new Date(now - 24 * 60 * 60 * 1000);
  }
  
  let filtered = AnalyticsState.alerts.filter(alert => {
    const alertDate = new Date(alert.processed_at);
    return alertDate >= cutoff;
  });
  
  if (AnalyticsState.timeRange === 'custom' && AnalyticsState.customDateTo) {
    const endDate = new Date(AnalyticsState.customDateTo);
    filtered = filtered.filter(alert => {
      const alertDate = new Date(alert.processed_at);
      return alertDate <= endDate;
    });
  }
  
  return filtered;
}

// ============================================
// Charts
// ============================================

function updateCharts() {
  updateThreatActivityChart();
  updateAttackDistributionChart();
  updateSeverityTrendChart();
}

function updateThreatActivityChart() {
  const canvas = u.$('#threat-activity-chart');
  if (!canvas) return;
  
  if (AnalyticsState.charts.threatActivity) {
    AnalyticsState.charts.threatActivity.destroy();
  }
  
  const filtered = filterAlertsByTimeRange();
  const grouped = groupAlertsByTime(filtered);
  
  const ctx = canvas.getContext('2d');
  AnalyticsState.charts.threatActivity = new Chart(ctx, {
    type: 'line',
    data: {
      labels: grouped.labels,
      datasets: [{
        label: 'Threats Detected',
        data: grouped.data,
        borderColor: 'rgb(239, 68, 68)',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
        tension: 0.4,
        fill: true,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          padding: 12,
          titleColor: '#fff',
          bodyColor: '#fff',
          callbacks: {
            label: (context) => `Threats: ${context.parsed.y}`,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          ticks: {
            precision: 0,
          },
        },
      },
    },
  });
}

function updateAttackDistributionChart() {
  const canvas = u.$('#attack-distribution-chart');
  if (!canvas) return;
  
  if (AnalyticsState.charts.attackDistribution) {
    AnalyticsState.charts.attackDistribution.destroy();
  }
  
  const filtered = filterAlertsByTimeRange();
  const distribution = {};
  
  filtered.forEach(alert => {
    const type = alert.attack_type || 'Unknown';
    distribution[type] = (distribution[type] || 0) + 1;
  });
  
  const sorted = Object.entries(distribution)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8);
  
  const ctx = canvas.getContext('2d');
  AnalyticsState.charts.attackDistribution = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: sorted.map(([type]) => type),
      datasets: [{
        data: sorted.map(([_, count]) => count),
        backgroundColor: [
          'rgb(239, 68, 68)',
          'rgb(249, 115, 22)',
          'rgb(245, 158, 11)',
          'rgb(34, 197, 94)',
          'rgb(59, 130, 246)',
          'rgb(139, 92, 246)',
          'rgb(236, 72, 153)',
          'rgb(156, 163, 175)',
        ],
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: {
            padding: 12,
            usePointStyle: true,
          },
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          padding: 12,
          callbacks: {
            label: (context) => {
              const label = context.label || '';
              const value = context.parsed || 0;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percent = ((value / total) * 100).toFixed(1);
              return `${label}: ${value} (${percent}%)`;
            },
          },
        },
      },
    },
  });
}

function updateSeverityTrendChart() {
  const canvas = u.$('#severity-trend-chart');
  if (!canvas) return;
  
  if (AnalyticsState.charts.severityTrend) {
    AnalyticsState.charts.severityTrend.destroy();
  }
  
  const filtered = filterAlertsByTimeRange();
  const grouped = groupAlertsBySeverityAndTime(filtered);
  
  const ctx = canvas.getContext('2d');
  AnalyticsState.charts.severityTrend = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: grouped.labels,
      datasets: [
        {
          label: 'High',
          data: grouped.high,
          backgroundColor: 'rgba(239, 68, 68, 0.8)',
        },
        {
          label: 'Medium',
          data: grouped.medium,
          backgroundColor: 'rgba(249, 115, 22, 0.8)',
        },
        {
          label: 'Low',
          data: grouped.low,
          backgroundColor: 'rgba(245, 158, 11, 0.8)',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          padding: 12,
        },
      },
      scales: {
        x: {
          stacked: true,
        },
        y: {
          stacked: true,
          beginAtZero: true,
          ticks: {
            precision: 0,
          },
        },
      },
    },
  });
}

function groupAlertsByTime(alerts) {
  const buckets = getTimeBuckets();
  const data = new Array(buckets.length).fill(0);
  
  alerts.forEach(alert => {
    const time = new Date(alert.processed_at).getTime();
    const bucketIndex = buckets.findIndex((bucket, i) => {
      const nextBucket = buckets[i + 1];
      return time >= bucket.time && (!nextBucket || time < nextBucket.time);
    });
    
    if (bucketIndex >= 0) {
      data[bucketIndex]++;
    }
  });
  
  return {
    labels: buckets.map(b => b.label),
    data,
  };
}

function groupAlertsBySeverityAndTime(alerts) {
  const buckets = getTimeBuckets();
  const high = new Array(buckets.length).fill(0);
  const medium = new Array(buckets.length).fill(0);
  const low = new Array(buckets.length).fill(0);
  
  alerts.forEach(alert => {
    const time = new Date(alert.processed_at).getTime();
    const bucketIndex = buckets.findIndex((bucket, i) => {
      const nextBucket = buckets[i + 1];
      return time >= bucket.time && (!nextBucket || time < nextBucket.time);
    });
    
    if (bucketIndex >= 0) {
      if (alert.severity === 'high') high[bucketIndex]++;
      else if (alert.severity === 'medium') medium[bucketIndex]++;
      else low[bucketIndex]++;
    }
  });
  
  return {
    labels: buckets.map(b => b.label),
    high,
    medium,
    low,
  };
}

function getTimeBuckets() {
  const now = new Date();
  const buckets = [];
  
  switch (AnalyticsState.timeRange) {
    case '1h':
      for (let i = 12; i >= 0; i--) {
        const time = new Date(now - i * 5 * 60 * 1000);
        buckets.push({
          time: time.getTime(),
          label: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        });
      }
      break;
    case '6h':
      for (let i = 12; i >= 0; i--) {
        const time = new Date(now - i * 30 * 60 * 1000);
        buckets.push({
          time: time.getTime(),
          label: time.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        });
      }
      break;
    case '24h':
      for (let i = 24; i >= 0; i--) {
        const time = new Date(now - i * 60 * 60 * 1000);
        buckets.push({
          time: time.getTime(),
          label: time.toLocaleTimeString([], { hour: '2-digit' }),
        });
      }
      break;
    case '7d':
      for (let i = 7; i >= 0; i--) {
        const time = new Date(now - i * 24 * 60 * 60 * 1000);
        buckets.push({
          time: time.getTime(),
          label: time.toLocaleDateString([], { month: 'short', day: 'numeric' }),
        });
      }
      break;
    case '30d':
      for (let i = 30; i >= 0; i -= 2) {
        const time = new Date(now - i * 24 * 60 * 60 * 1000);
        buckets.push({
          time: time.getTime(),
          label: time.toLocaleDateString([], { month: 'short', day: 'numeric' }),
        });
      }
      break;
    default:
      for (let i = 24; i >= 0; i--) {
        const time = new Date(now - i * 60 * 60 * 1000);
        buckets.push({
          time: time.getTime(),
          label: time.toLocaleTimeString([], { hour: '2-digit' }),
        });
      }
  }
  
  return buckets;
}

// ============================================
// Top Attacks Table
// ============================================

function updateTopAttacks() {
  const tbody = u.$('#top-attacks-body');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  const filtered = filterAlertsByTimeRange();
  const attacks = {};
  
  filtered.forEach(alert => {
    const type = alert.attack_type || 'Unknown';
    if (!attacks[type]) {
      attacks[type] = {
        type,
        count: 0,
        high: 0,
        medium: 0,
        low: 0,
      };
    }
    
    attacks[type].count++;
    if (alert.severity === 'high') attacks[type].high++;
    else if (alert.severity === 'medium') attacks[type].medium++;
    else attacks[type].low++;
  });
  
  const sorted = Object.values(attacks)
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);
  
  if (sorted.length === 0) {
    const row = u.createElement('tr', {}, [
      u.createElement('td', { colspan: '5', className: 'table-empty' }, 'No data available'),
    ]);
    tbody.appendChild(row);
    return;
  }
  
  sorted.forEach((attack, index) => {
    const row = u.createElement('tr', {}, [
      u.createElement('td', {}, (index + 1).toString()),
      u.createElement('td', {}, attack.type),
      u.createElement('td', {}, u.formatNumber(attack.count)),
      u.createElement('td', {}, [
        attack.high > 0 ? u.createElement('span', { className: 'severity-badge severity-high' }, attack.high.toString()) : null,
        attack.medium > 0 ? u.createElement('span', { className: 'severity-badge severity-medium' }, attack.medium.toString()) : null,
        attack.low > 0 ? u.createElement('span', { className: 'severity-badge severity-low' }, attack.low.toString()) : null,
      ].filter(Boolean)),
      u.createElement('td', {}, [
        u.createElement('div', { className: 'progress-bar' }, [
          u.createElement('div', {
            className: 'progress-fill',
            style: `width: ${(attack.count / sorted[0].count) * 100}%`,
          }),
        ]),
      ]),
    ]);
    
    tbody.appendChild(row);
  });
}

// ============================================
// Session Statistics
// ============================================

function updateSessionStatistics() {
  const tbody = u.$('#session-stats-body');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  const filtered = filterAlertsByTimeRange();
  const sessionStats = {};
  
  filtered.forEach(alert => {
    const sessionId = alert.session_id || 'Unknown';
    if (!sessionStats[sessionId]) {
      sessionStats[sessionId] = {
        sessionId,
        count: 0,
        high: 0,
        medium: 0,
        low: 0,
        firstSeen: alert.processed_at,
        lastSeen: alert.processed_at,
      };
    }
    
    sessionStats[sessionId].count++;
    if (alert.severity === 'high') sessionStats[sessionId].high++;
    else if (alert.severity === 'medium') sessionStats[sessionId].medium++;
    else sessionStats[sessionId].low++;
    
    if (new Date(alert.processed_at) < new Date(sessionStats[sessionId].firstSeen)) {
      sessionStats[sessionId].firstSeen = alert.processed_at;
    }
    if (new Date(alert.processed_at) > new Date(sessionStats[sessionId].lastSeen)) {
      sessionStats[sessionId].lastSeen = alert.processed_at;
    }
  });
  
  const sorted = Object.values(sessionStats)
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);
  
  if (sorted.length === 0) {
    const row = u.createElement('tr', {}, [
      u.createElement('td', { colspan: '4', className: 'table-empty' }, 'No data available'),
    ]);
    tbody.appendChild(row);
    return;
  }
  
  sorted.forEach(session => {
    const row = u.createElement('tr', {}, [
      u.createElement('td', { className: 'session-id' }, u.truncateString(session.sessionId, 12)),
      u.createElement('td', {}, u.formatNumber(session.count)),
      u.createElement('td', {}, [
        session.high > 0 ? u.createElement('span', { className: 'severity-badge severity-high' }, session.high.toString()) : null,
        session.medium > 0 ? u.createElement('span', { className: 'severity-badge severity-medium' }, session.medium.toString()) : null,
        session.low > 0 ? u.createElement('span', { className: 'severity-badge severity-low' }, session.low.toString()) : null,
      ].filter(Boolean)),
      u.createElement('td', {}, u.formatRelativeTime(session.lastSeen)),
    ]);
    
    tbody.appendChild(row);
  });
}

// ============================================
// Time Range Control
// ============================================

function changeTimeRange(range) {
  AnalyticsState.timeRange = range;
  
  const buttons = u.$$('.time-range-btn');
  buttons.forEach(btn => {
    if (btn.getAttribute('data-range') === range) {
      btn.classList.add('active');
      btn.setAttribute('aria-pressed', 'true');
    } else {
      btn.classList.remove('active');
      btn.setAttribute('aria-pressed', 'false');
    }
  });
  
  if (range === 'custom') {
    u.show(u.$('#custom-date-range'));
  } else {
    u.hide(u.$('#custom-date-range'));
    updateMetrics();
    updateCharts();
    updateTopAttacks();
    updateSessionStatistics();
  }
}

function applyCustomRange() {
  const fromInput = u.$('#custom-date-from');
  const toInput = u.$('#custom-date-to');
  
  if (!fromInput || !toInput) return;
  
  AnalyticsState.customDateFrom = fromInput.value;
  AnalyticsState.customDateTo = toInput.value;
  
  if (!AnalyticsState.customDateFrom) {
    app.showToast('Please select a start date', 'error');
    return;
  }
  
  updateMetrics();
  updateCharts();
  updateTopAttacks();
  updateSessionStatistics();
}

// ============================================
// Auto Refresh
// ============================================

function toggleAutoRefresh() {
  const checkbox = u.$('#auto-refresh-toggle');
  if (!checkbox) return;
  
  AnalyticsState.autoRefresh = checkbox.checked;
  
  if (AnalyticsState.autoRefresh) {
    startAutoRefresh();
    app.showToast('Auto-refresh enabled', 'success');
  } else {
    stopAutoRefresh();
    app.showToast('Auto-refresh disabled', 'info');
  }
}

function startAutoRefresh() {
  stopAutoRefresh();
  
  AnalyticsState.refreshInterval = setInterval(() => {
    console.log('🔄 Auto-refreshing analytics data...');
    loadAnalyticsData();
  }, 30000); // 30 seconds
}

function stopAutoRefresh() {
  if (AnalyticsState.refreshInterval) {
    clearInterval(AnalyticsState.refreshInterval);
    AnalyticsState.refreshInterval = null;
  }
}

// ============================================
// Event Listeners
// ============================================

function initEventListeners() {
  const timeRangeBtns = u.$$('.time-range-btn');
  timeRangeBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const range = btn.getAttribute('data-range');
      changeTimeRange(range);
    });
  });
  
  const applyCustomBtn = u.$('#apply-custom-range');
  if (applyCustomBtn) {
    applyCustomBtn.addEventListener('click', applyCustomRange);
  }
  
  const autoRefreshToggle = u.$('#auto-refresh-toggle');
  if (autoRefreshToggle) {
    autoRefreshToggle.addEventListener('change', toggleAutoRefresh);
  }
  
  const refreshBtn = u.$('#refresh-analytics-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => {
      loadAnalyticsData();
      app.showToast('Analytics refreshed', 'success');
    });
  }
}

// ============================================
// Initialization
// ============================================

async function initAnalyticsPage() {
  console.log('📊 Initializing analytics page...');
  
  initEventListeners();
  await loadAnalyticsData();
  
  if (AnalyticsState.autoRefresh) {
    startAutoRefresh();
  }
  
  console.log('✅ Analytics page initialized');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAnalyticsPage);
} else {
  initAnalyticsPage();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  stopAutoRefresh();
  Object.values(AnalyticsState.charts).forEach(chart => {
    if (chart) chart.destroy();
  });
});
