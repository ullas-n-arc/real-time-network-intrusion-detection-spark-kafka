/**
 * NIDS Dashboard - Dashboard Page JavaScript
 * Handles dashboard-specific functionality
 */

// ============================================
// Dashboard State
// ============================================

const DashboardState = {
  currentSession: null,
  autoRefresh: true,
  refreshInterval: 10000,
  refreshTimer: null,
  charts: {},
  data: {
    stats: null,
    alerts: [],
    timeline: [],
  },
};

// ============================================
// Session Management
// ============================================

async function loadSessions() {
  try {
    const sessions = await api.getSessions();
    const select = u.$('#session-select');
    
    if (!select) return;
    
    // Clear existing options except "All Sessions"
    select.innerHTML = '<option value="">All Sessions</option>';
    
    // Add session options
    sessions.forEach(session => {
      const option = document.createElement('option');
      option.value = session.session_id;
      
      const status = session.status === 'active' ? '🟢' : '⚪';
      const startTime = session.started_at ? u.formatDate(session.started_at, false) : 'Unknown';
      option.textContent = `${status} ${session.session_id} (${startTime})`;
      
      select.appendChild(option);
    });
    
    // Load and select current session
    const current = await api.getCurrentSession();
    if (current.session_id) {
      select.value = current.session_id;
      DashboardState.currentSession = current.session_id;
    }
    
    // Update delete button state
    updateDeleteButtonState();
    
  } catch (error) {
    app.handleError(error, 'Loading sessions');
  }
}

function updateDeleteButtonState() {
  const select = u.$('#session-select');
  const deleteBtn = u.$('#delete-session-btn');
  
  if (select && deleteBtn) {
    deleteBtn.disabled = !select.value;
  }
}

async function changeSession() {
  const select = u.$('#session-select');
  if (!select) return;
  
  const sessionId = select.value || null;
  
  try {
    await api.setSession(sessionId);
    DashboardState.currentSession = sessionId;
    
    updateDeleteButtonState();
    await loadDashboardData();
    
    app.showToast(
      sessionId ? `Switched to session ${sessionId}` : 'Viewing all sessions',
      'success',
      3000
    );
  } catch (error) {
    app.handleError(error, 'Changing session');
  }
}

async function deleteCurrentSession() {
  const select = u.$('#session-select');
  if (!select || !select.value) {
    app.showToast('Please select a session to delete', 'warning');
    return;
  }
  
  const sessionId = select.value;
  
  // Show confirmation modal
  const modal = u.$('#confirm-delete-modal');
  const desc = u.$('#delete-modal-desc');
  const confirmBtn = u.$('#confirm-delete-btn');
  
  if (!modal || !desc || !confirmBtn) return;
  
  desc.textContent = `Are you sure you want to delete session "${sessionId}" and all its alerts? This action cannot be undone.`;
  
  confirmBtn.onclick = async () => {
    try {
      app.showLoading();
      const result = await api.deleteSession(sessionId);
      
      app.showToast(
        `Deleted session ${sessionId}: ${result.alerts_deleted} alerts removed`,
        'success'
      );
      
      // Reset to "All Sessions"
      select.value = '';
      DashboardState.currentSession = null;
      
      await loadSessions();
      await loadDashboardData();
      
      app.closeModal(modal);
      
    } catch (error) {
      app.handleError(error, 'Deleting session');
    } finally {
      app.hideLoading();
    }
  };
  
  app.openModal('confirm-delete-modal');
}

async function deleteAllSessions() {
  if (!confirm('Are you sure you want to delete ALL sessions and ALL alerts? This cannot be undone!')) {
    return;
  }
  
  if (!confirm('This will permanently delete all data. Are you absolutely sure?')) {
    return;
  }
  
  try {
    app.showLoading();
    const result = await api.deleteAllSessions();
    
    app.showToast(
      `Deleted all data: ${result.alerts_deleted} alerts, ${result.sessions_deleted} sessions removed`,
      'success'
    );
    
    DashboardState.currentSession = null;
    await loadSessions();
    await loadDashboardData();
    
  } catch (error) {
    app.handleError(error, 'Deleting all sessions');
  } finally {
    app.hideLoading();
  }
}

// ============================================
// Data Loading
// ============================================

async function loadDashboardData() {
  try {
    // Get selected time range for timeline
    const timelineSelect = u.$('#timeline-range');
    const hours = timelineSelect ? parseInt(timelineSelect.value) : 24;
    
    // Load stats, alerts, and timeline in parallel
    const [stats, alerts, timeline] = await Promise.all([
      api.getAlertStats(24),
      api.getAlerts({ limit: 20 }),
      api.getAlertTimeline(hours, hours <= 6 ? 15 : 60),
    ]);
    
    DashboardState.data.stats = stats;
    DashboardState.data.alerts = alerts;
    DashboardState.data.timeline = timeline;
    
    // Update UI
    updateStatsCards(stats);
    updateAlertsTable(alerts);
    updateAttackTypesChart(stats);
    updateTimelineChart(timeline);
    updateSeverityChart(stats);
    
    app.announce('Dashboard data updated');
    
  } catch (error) {
    app.handleError(error, 'Loading dashboard data');
  }
}

// ============================================
// Stats Cards
// ============================================

function updateStatsCards(stats) {
  const elements = {
    total: u.$('#total-alerts'),
    high: u.$('#high-severity'),
    medium: u.$('#medium-severity'),
    low: u.$('#low-severity'),
  };
  
  if (elements.total) elements.total.textContent = u.formatNumber(stats.total_alerts || 0);
  if (elements.high) elements.high.textContent = u.formatNumber(stats.high_severity || 0);
  if (elements.medium) elements.medium.textContent = u.formatNumber(stats.medium_severity || 0);
  if (elements.low) elements.low.textContent = u.formatNumber(stats.low_severity || 0);
}

// ============================================
// Alerts Table
// ============================================

function updateAlertsTable(alerts) {
  const tbody = u.$('#alerts-body');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  if (alerts.length === 0) {
    const row = u.createElement('tr', {}, [
      u.createElement('td', { colspan: '5', className: 'table-empty' }, [
        u.createElement('div', { className: 'empty-state' }, [
          u.createElement('span', { className: 'empty-icon', 'aria-hidden': 'true' }, '📭'),
          u.createElement('p', {}, 'No alerts found'),
        ]),
      ]),
    ]);
    tbody.appendChild(row);
    return;
  }
  
  alerts.forEach(alert => {
    const row = u.createElement('tr', {}, [
      u.createElement('td', {}, u.formatDate(alert.processed_at)),
      u.createElement('td', { className: 'attack-type' }, alert.attack_type || 'Unknown'),
      u.createElement('td', {}, [
        u.createElement('span', {
          className: `severity-badge severity-${alert.severity}`,
        }, alert.severity),
      ]),
      u.createElement('td', {}, u.truncateString(alert.session_id || '-', 12)),
      u.createElement('td', {}, [
        u.createElement('button', {
          className: 'btn btn-sm btn-ghost',
          'aria-label': 'View alert details',
          onClick: () => showAlertDetails(alert),
        }, 'View'),
      ]),
    ]);
    
    tbody.appendChild(row);
  });
}

// ============================================
// Charts
// ============================================

function updateAttackTypesChart(stats) {
  const canvas = u.$('#attack-types-chart');
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  const attackTypes = stats.by_attack_type || {};
  
  // Destroy existing chart
  if (DashboardState.charts.attackTypes) {
    DashboardState.charts.attackTypes.destroy();
  }
  
  // No data
  if (Object.keys(attackTypes).length === 0) {
    const legend = u.$('#attack-types-legend');
    if (legend) {
      legend.innerHTML = '<p style="text-align: center; color: var(--color-text-muted);">No data available</p>';
    }
    return;
  }
  
  const labels = Object.keys(attackTypes);
  const data = Object.values(attackTypes);
  const colors = generateColors(labels.length);
  
  DashboardState.charts.attackTypes = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderColor: 'var(--color-bg-secondary)',
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.parsed;
              const total = context.dataset.data.reduce((a, b) => a + b, 0);
              const percentage = ((value / total) * 100).toFixed(1);
              return `${label}: ${value} (${percentage}%)`;
            },
          },
        },
      },
    },
  });
  
  // Update custom legend
  updateChartLegend('attack-types-legend', labels, colors, data);
}

function updateTimelineChart(timeline) {
  const canvas = u.$('#timeline-chart');
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  
  // Destroy existing chart
  if (DashboardState.charts.timeline) {
    DashboardState.charts.timeline.destroy();
  }
  
  // No data
  if (!timeline || timeline.length === 0) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#64748b';
    ctx.font = '14px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText('No timeline data available', canvas.width / 2, canvas.height / 2);
    return;
  }
  
  // Sort by timestamp
  const sortedTimeline = [...timeline].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  
  // Extract labels and data
  const labels = sortedTimeline.map(item => {
    const date = new Date(item.timestamp);
    // Convert to IST (UTC+5:30)
    const istDate = new Date(date.getTime() + (5.5 * 60 * 60 * 1000));
    const hours = sortedTimeline.length > 48;
    if (hours) {
      return istDate.toLocaleDateString('en-IN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    }
    return istDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  });
  const data = sortedTimeline.map(item => item.count || 0);
  
  // Create chart
  DashboardState.charts.timeline = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [{
        label: 'Alerts',
        data: data,
        borderColor: '#00d9ff',
        backgroundColor: 'rgba(0, 217, 255, 0.1)',
        borderWidth: 2,
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointBackgroundColor: '#00d9ff',
        pointBorderColor: '#fff',
        pointBorderWidth: 1,
        pointHoverRadius: 5,
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
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(26, 32, 53, 0.95)',
          titleColor: '#00d9ff',
          bodyColor: '#e2e8f0',
          borderColor: '#334155',
          borderWidth: 1,
          padding: 12,
          displayColors: false,
          callbacks: {
            title: function(context) {
              return 'Time: ' + context[0].label;
            },
            label: function(context) {
              return 'Alerts: ' + context.parsed.y;
            },
          },
        },
      },
      scales: {
        x: {
          grid: {
            color: 'rgba(255, 255, 255, 0.05)',
            drawBorder: false,
          },
          ticks: {
            color: '#94a3b8',
            maxRotation: 45,
            minRotation: 0,
          },
        },
        y: {
          beginAtZero: true,
          grid: {
            color: 'rgba(255, 255, 255, 0.05)',
            drawBorder: false,
          },
          ticks: {
            color: '#94a3b8',
            precision: 0,
          },
        },
      },
      interaction: {
        mode: 'nearest',
        axis: 'x',
        intersect: false,
      },
    },
  });
}

function updateSeverityChart(stats) {
  const canvas = u.$('#severity-chart');
  if (!canvas) return;
  
  const ctx = canvas.getContext('2d');
  
  // Destroy existing chart
  if (DashboardState.charts.severity) {
    DashboardState.charts.severity.destroy();
  }
  
  const high = stats.high_severity || 0;
  const medium = stats.medium_severity || 0;
  const low = stats.low_severity || 0;
  const total = high + medium + low;
  
  // No data
  if (total === 0) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#64748b';
    ctx.font = '14px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText('No severity data available', canvas.width / 2, canvas.height / 2);
    return;
  }
  
  const data = [high, medium, low];
  const labels = ['High', 'Medium', 'Low'];
  const colors = ['#ef4444', '#f59e0b', '#10b981'];
  
  // Create chart
  DashboardState.charts.severity = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderColor: '#1a2035',
        borderWidth: 2,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      plugins: {
        legend: {
          position: 'bottom',
          labels: {
            color: '#e2e8f0',
            padding: 15,
            font: {
              size: 12,
              weight: '500',
            },
            generateLabels: function(chart) {
              const data = chart.data;
              if (data.labels.length && data.datasets.length) {
                return data.labels.map((label, i) => {
                  const value = data.datasets[0].data[i];
                  const percentage = ((value / total) * 100).toFixed(1);
                  return {
                    text: `${label}: ${value} (${percentage}%)`,
                    fillStyle: data.datasets[0].backgroundColor[i],
                    hidden: false,
                    index: i,
                  };
                });
              }
              return [];
            },
          },
        },
        tooltip: {
          backgroundColor: 'rgba(26, 32, 53, 0.95)',
          titleColor: '#00d9ff',
          bodyColor: '#e2e8f0',
          borderColor: '#334155',
          borderWidth: 1,
          padding: 12,
          displayColors: true,
          callbacks: {
            label: function(context) {
              const label = context.label || '';
              const value = context.parsed || 0;
              const percentage = ((value / total) * 100).toFixed(1);
              return `${label}: ${value} alerts (${percentage}%)`;
            },
          },
        },
      },
      cutout: '60%',
    },
  });
}

function updateChartLegend(containerId, labels, colors, data) {
  const container = u.$(`#${containerId}`);
  if (!container) return;
  
  container.innerHTML = '';
  
  labels.forEach((label, index) => {
    const item = u.createElement('div', { className: 'chart-legend-item' }, [
      u.createElement('span', {
        className: 'chart-legend-color',
        style: `background: ${colors[index]};`,
      }),
      u.createElement('span', { className: 'chart-legend-label' }, `${label}: ${data[index]}`),
    ]);
    container.appendChild(item);
  });
}

function generateColors(count) {
  const baseColors = [
    '#00d9ff', '#3b82f6', '#8b5cf6', '#ef4444', '#f59e0b',
    '#10b981', '#06b6d4', '#ec4899', '#14b8a6', '#f97316',
  ];
  
  const colors = [];
  for (let i = 0; i < count; i++) {
    colors.push(baseColors[i % baseColors.length]);
  }
  
  return colors;
}

// ============================================
// Alert Details Modal
// ============================================

function showAlertDetails(alert) {
  const modal = u.$('#alert-detail-modal');
  const body = u.$('#alert-modal-body');
  
  if (!modal || !body) return;
  
  body.innerHTML = '';
  
  const details = [
    { label: 'Alert ID', value: alert._id || '-' },
    { label: 'Timestamp', value: u.formatDate(alert.processed_at) },
    { label: 'Attack Type', value: alert.attack_type || 'Unknown' },
    { label: 'Severity', value: alert.severity || '-' },
    { label: 'Session ID', value: alert.session_id || '-' },
    { label: 'Prediction', value: alert.prediction !== undefined ? alert.prediction : '-' },
    { label: 'Confidence', value: alert.prediction_score ? u.formatConfidence(alert.prediction_score) : '-' },
  ];
  
  details.forEach(({ label, value }) => {
    const row = u.createElement('div', { className: 'detail-row' }, [
      u.createElement('strong', {}, label + ':'),
      u.createElement('span', {}, ' ' + value),
    ]);
    body.appendChild(row);
  });
  
  app.openModal('alert-detail-modal');
}

// ============================================
// Auto-refresh
// ============================================

function startAutoRefresh() {
  if (DashboardState.refreshTimer) {
    clearInterval(DashboardState.refreshTimer);
  }
  
  if (DashboardState.autoRefresh) {
    DashboardState.refreshTimer = setInterval(loadDashboardData, DashboardState.refreshInterval);
  }
}

function stopAutoRefresh() {
  if (DashboardState.refreshTimer) {
    clearInterval(DashboardState.refreshTimer);
    DashboardState.refreshTimer = null;
  }
}

// ============================================
// Event Listeners
// ============================================

function initEventListeners() {
  // Session selector
  const sessionSelect = u.$('#session-select');
  if (sessionSelect) {
    sessionSelect.addEventListener('change', changeSession);
  }
  
  // Timeline range selector
  const timelineRange = u.$('#timeline-range');
  if (timelineRange) {
    timelineRange.addEventListener('change', loadDashboardData);
  }
  
  // Delete session button
  const deleteSessionBtn = u.$('#delete-session-btn');
  if (deleteSessionBtn) {
    deleteSessionBtn.addEventListener('click', deleteCurrentSession);
  }
  
  // Refresh button
  const refreshBtn = u.$('#refresh-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', loadDashboardData);
  }
  
  // Auto-refresh toggle
  const autoRefreshToggle = u.$('#auto-refresh-toggle');
  if (autoRefreshToggle) {
    autoRefreshToggle.checked = DashboardState.autoRefresh;
    autoRefreshToggle.addEventListener('change', (e) => {
      DashboardState.autoRefresh = e.target.checked;
      if (e.target.checked) {
        startAutoRefresh();
        app.showToast('Auto-refresh enabled', 'success', 2000);
      } else {
        stopAutoRefresh();
        app.showToast('Auto-refresh disabled', 'info', 2000);
      }
    });
  }
}

// ============================================
// Initialization
// ============================================

async function initDashboard() {
  console.log('📊 Initializing dashboard...');
  
  try {
    initEventListeners();
    
    // Load data
    console.log('📥 Loading sessions and data...');
    await Promise.all([
      loadSessions().catch(err => {
        console.error('Failed to load sessions:', err);
        app.showToast('Failed to load sessions: ' + err.message, 'error');
      }),
      loadDashboardData().catch(err => {
        console.error('Failed to load dashboard data:', err);
        app.showToast('Failed to load dashboard data: ' + err.message, 'error');
      }),
    ]);
    
    // Start auto-refresh
    startAutoRefresh();
    
    console.log('✅ Dashboard initialized');
  } catch (error) {
    console.error('❌ Dashboard initialization failed:', error);
    app.showToast('Dashboard initialization failed: ' + error.message, 'error');
  }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDashboard);
} else {
  initDashboard();
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  stopAutoRefresh();
});
