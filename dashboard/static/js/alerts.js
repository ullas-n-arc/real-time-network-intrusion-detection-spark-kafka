/**
 * NIDS Dashboard - Alerts Page JavaScript
 * Advanced alert filtering, sorting, and management
 */

// ============================================
// Alerts State
// ============================================

const AlertsState = {
  alerts: [],
  filteredAlerts: [],
  sessions: [],
  attackTypes: [],
  currentPage: 1,
  pageSize: 25,
  totalPages: 1,
  sortBy: 'timestamp',
  sortOrder: 'desc',
  filters: {
    search: '',
    severity: '',
    attackType: '',
    session: '',
    dateFrom: '',
    dateTo: '',
  },
  selectedAlerts: new Set(),
  viewMode: 'table', // 'table' or 'cards'
};

// ============================================
// Data Loading
// ============================================

async function loadAlertsData() {
  try {
    app.showLoading();
    
    // Load data in parallel
    const [sessions, attackTypes] = await Promise.all([
      api.getSessions(),
      api.getAttackTypes(),
    ]);
    
    AlertsState.sessions = sessions;
    AlertsState.attackTypes = Object.values(attackTypes);
    
    // Populate filter dropdowns
    populateFilterDropdowns();
    
    // Load alerts
    await loadAlerts();
    
  } catch (error) {
    app.handleError(error, 'Loading alerts data');
  } finally {
    app.hideLoading();
  }
}

async function loadAlerts() {
  try {
    const params = {
      limit: 1000, // Load more for client-side filtering
    };
    
    // Apply server-side filters if available
    if (AlertsState.filters.severity) {
      params.severity = AlertsState.filters.severity;
    }
    if (AlertsState.filters.attackType) {
      params.attack_type = AlertsState.filters.attackType;
    }
    
    const alerts = await api.getAlerts(params);
    AlertsState.alerts = alerts;
    
    // Apply client-side filters
    applyFilters();
    
    updateResultsCount();
    renderAlerts();
    
  } catch (error) {
    app.handleError(error, 'Loading alerts');
  }
}

// ============================================
// Filtering
// ============================================

function populateFilterDropdowns() {
  // Populate attack types
  const attackTypeSelect = u.$('#attack-type-filter');
  if (attackTypeSelect) {
    attackTypeSelect.innerHTML = '<option value="">All Types</option>';
    AlertsState.attackTypes.forEach(type => {
      const option = document.createElement('option');
      option.value = type;
      option.textContent = type;
      attackTypeSelect.appendChild(option);
    });
  }
  
  // Populate sessions
  const sessionSelect = u.$('#session-filter');
  if (sessionSelect) {
    sessionSelect.innerHTML = '<option value="">All Sessions</option>';
    AlertsState.sessions.forEach(session => {
      const option = document.createElement('option');
      option.value = session.session_id;
      const status = session.status === 'active' ? '🟢' : '⚪';
      option.textContent = `${status} ${session.session_id}`;
      sessionSelect.appendChild(option);
    });
  }
}

function applyFilters() {
  let filtered = [...AlertsState.alerts];
  
  // Search filter
  if (AlertsState.filters.search) {
    const search = AlertsState.filters.search.toLowerCase();
    filtered = filtered.filter(alert => 
      (alert.attack_type || '').toLowerCase().includes(search) ||
      (alert.session_id || '').toLowerCase().includes(search) ||
      (alert.severity || '').toLowerCase().includes(search)
    );
  }
  
  // Severity filter
  if (AlertsState.filters.severity) {
    filtered = filtered.filter(alert => 
      alert.severity === AlertsState.filters.severity
    );
  }
  
  // Attack type filter
  if (AlertsState.filters.attackType) {
    filtered = filtered.filter(alert => 
      alert.attack_type === AlertsState.filters.attackType
    );
  }
  
  // Session filter
  if (AlertsState.filters.session) {
    filtered = filtered.filter(alert => 
      alert.session_id === AlertsState.filters.session
    );
  }
  
  // Date range filter
  if (AlertsState.filters.dateFrom) {
    const fromDate = new Date(AlertsState.filters.dateFrom);
    filtered = filtered.filter(alert => {
      const alertDate = new Date(alert.processed_at);
      return alertDate >= fromDate;
    });
  }
  
  if (AlertsState.filters.dateTo) {
    const toDate = new Date(AlertsState.filters.dateTo);
    filtered = filtered.filter(alert => {
      const alertDate = new Date(alert.processed_at);
      return alertDate <= toDate;
    });
  }
  
  // Apply sorting
  filtered = u.sortBy(filtered, AlertsState.sortBy, AlertsState.sortOrder);
  
  AlertsState.filteredAlerts = filtered;
  AlertsState.totalPages = Math.ceil(filtered.length / AlertsState.pageSize);
  AlertsState.currentPage = 1; // Reset to first page
}

function resetFilters() {
  AlertsState.filters = {
    search: '',
    severity: '',
    attackType: '',
    session: '',
    dateFrom: '',
    dateTo: '',
  };
  
  // Reset form inputs
  const form = u.$('#alerts-filter-form');
  if (form) form.reset();
  
  const searchInput = u.$('#search-input');
  if (searchInput) searchInput.value = '';
  
  // Hide active filters
  const activeFilters = u.$('#active-filters');
  if (activeFilters) u.hide(activeFilters);
  
  applyFilters();
  renderAlerts();
  updateResultsCount();
}

function updateActiveFilters() {
  const activeFilters = u.$('#active-filters');
  const filterTags = u.$('#filter-tags');
  
  if (!activeFilters || !filterTags) return;
  
  const tags = [];
  
  if (AlertsState.filters.search) {
    tags.push({ label: 'Search', value: AlertsState.filters.search, key: 'search' });
  }
  if (AlertsState.filters.severity) {
    tags.push({ label: 'Severity', value: AlertsState.filters.severity, key: 'severity' });
  }
  if (AlertsState.filters.attackType) {
    tags.push({ label: 'Attack Type', value: AlertsState.filters.attackType, key: 'attackType' });
  }
  if (AlertsState.filters.session) {
    tags.push({ label: 'Session', value: u.truncateString(AlertsState.filters.session, 10), key: 'session' });
  }
  if (AlertsState.filters.dateFrom) {
    tags.push({ label: 'From', value: u.formatDate(AlertsState.filters.dateFrom, false), key: 'dateFrom' });
  }
  if (AlertsState.filters.dateTo) {
    tags.push({ label: 'To', value: u.formatDate(AlertsState.filters.dateTo, false), key: 'dateTo' });
  }
  
  if (tags.length === 0) {
    u.hide(activeFilters);
    return;
  }
  
  u.show(activeFilters);
  filterTags.innerHTML = '';
  
  tags.forEach(tag => {
    const tagEl = u.createElement('div', { className: 'filter-tag' }, [
      u.createElement('span', {}, `${tag.label}: ${tag.value}`),
      u.createElement('button', {
        className: 'filter-tag-remove',
        'aria-label': `Remove ${tag.label} filter`,
        onClick: () => removeFilter(tag.key),
      }, '×'),
    ]);
    filterTags.appendChild(tagEl);
  });
}

function removeFilter(key) {
  AlertsState.filters[key] = '';
  
  // Update form input
  const inputMap = {
    search: '#search-input',
    severity: '#severity-filter',
    attackType: '#attack-type-filter',
    session: '#session-filter',
    dateFrom: '#date-from',
    dateTo: '#date-to',
  };
  
  const input = u.$(inputMap[key]);
  if (input) input.value = '';
  
  applyFilters();
  renderAlerts();
  updateActiveFilters();
  updateResultsCount();
}

// ============================================
// Rendering
// ============================================

function renderAlerts() {
  if (AlertsState.viewMode === 'table') {
    renderTableView();
  } else {
    renderCardsView();
  }
  
  renderPagination();
}

function renderTableView() {
  const tbody = u.$('#alerts-body');
  if (!tbody) return;
  
  tbody.innerHTML = '';
  
  const start = (AlertsState.currentPage - 1) * AlertsState.pageSize;
  const end = start + AlertsState.pageSize;
  const pageAlerts = AlertsState.filteredAlerts.slice(start, end);
  
  if (pageAlerts.length === 0) {
    const row = u.createElement('tr', {}, [
      u.createElement('td', { colspan: '7', className: 'table-empty' }, [
        u.createElement('div', { className: 'empty-state' }, [
          u.createElement('span', { className: 'empty-icon', 'aria-hidden': 'true' }, '📭'),
          u.createElement('p', {}, 'No alerts found'),
        ]),
      ]),
    ]);
    tbody.appendChild(row);
    return;
  }
  
  pageAlerts.forEach(alert => {
    const row = u.createElement('tr', {}, [
      u.createElement('td', { className: 'table-checkbox-col' }, [
        u.createElement('label', { className: 'checkbox-wrapper' }, [
          u.createElement('input', {
            type: 'checkbox',
            'aria-label': `Select alert ${alert._id}`,
            checked: AlertsState.selectedAlerts.has(alert._id),
            onChange: (e) => toggleAlertSelection(alert._id, e.target.checked),
          }),
          u.createElement('span', { className: 'checkbox-custom' }),
        ]),
      ]),
      u.createElement('td', {}, u.formatDate(alert.processed_at)),
      u.createElement('td', { className: 'attack-type' }, alert.attack_type || 'Unknown'),
      u.createElement('td', {}, [
        u.createElement('span', {
          className: `severity-badge severity-${alert.severity}`,
        }, alert.severity || '-'),
      ]),
      u.createElement('td', {}, u.truncateString(alert.session_id || '-', 12)),
      u.createElement('td', {}, [
        u.createElement('button', {
          className: 'btn btn-sm btn-ghost',
          'aria-label': 'View alert details',
          onClick: () => showAlertDetails(alert),
        }, '👁️'),
      ]),
    ]);
    
    tbody.appendChild(row);
  });
}

function renderCardsView() {
  const container = u.$('#alerts-cards-container');
  if (!container) return;
  
  container.innerHTML = '';
  
  const start = (AlertsState.currentPage - 1) * AlertsState.pageSize;
  const end = start + AlertsState.pageSize;
  const pageAlerts = AlertsState.filteredAlerts.slice(start, end);
  
  if (pageAlerts.length === 0) {
    container.innerHTML = '<div class="empty-state"><span class="empty-icon">📭</span><p>No alerts found</p></div>';
    return;
  }
  
  pageAlerts.forEach(alert => {
    const card = u.createElement('article', { className: 'alert-card' }, [
      u.createElement('header', { className: 'alert-card-header' }, [
        u.createElement('span', {
          className: `severity-badge severity-${alert.severity}`,
        }, alert.severity || '-'),
        u.createElement('span', { className: 'alert-card-time' }, u.formatRelativeTime(alert.processed_at)),
      ]),
      u.createElement('div', { className: 'alert-card-body' }, [
        u.createElement('h3', { className: 'alert-card-type' }, alert.attack_type || 'Unknown'),
        u.createElement('p', { className: 'alert-card-session' }, `Session: ${u.truncateString(alert.session_id || '-', 15)}`),
      ]),
      u.createElement('footer', { className: 'alert-card-footer' }, [
        u.createElement('button', {
          className: 'btn btn-sm btn-primary',
          onClick: () => showAlertDetails(alert),
        }, 'View Details'),
      ]),
    ]);
    
    container.appendChild(card);
  });
}

function renderPagination() {
  const summary = u.$('#pagination-summary');
  const pages = u.$('#pagination-pages');
  const firstBtn = u.$('#first-page');
  const prevBtn = u.$('#prev-page');
  const nextBtn = u.$('#next-page');
  const lastBtn = u.$('#last-page');
  
  const start = (AlertsState.currentPage - 1) * AlertsState.pageSize + 1;
  const end = Math.min(start + AlertsState.pageSize - 1, AlertsState.filteredAlerts.length);
  const total = AlertsState.filteredAlerts.length;
  
  if (summary) {
    summary.textContent = `Showing ${start}-${end} of ${total} alerts`;
  }
  
  // Update buttons
  if (firstBtn) firstBtn.disabled = AlertsState.currentPage === 1;
  if (prevBtn) prevBtn.disabled = AlertsState.currentPage === 1;
  if (nextBtn) nextBtn.disabled = AlertsState.currentPage === AlertsState.totalPages;
  if (lastBtn) lastBtn.disabled = AlertsState.currentPage === AlertsState.totalPages;
  
  // Render page numbers
  if (pages) {
    pages.innerHTML = '';
    const maxPages = 7;
    let startPage = Math.max(1, AlertsState.currentPage - Math.floor(maxPages / 2));
    let endPage = Math.min(AlertsState.totalPages, startPage + maxPages - 1);
    
    if (endPage - startPage < maxPages - 1) {
      startPage = Math.max(1, endPage - maxPages + 1);
    }
    
    for (let i = startPage; i <= endPage; i++) {
      const btn = u.createElement('button', {
        className: `pagination-page-btn ${i === AlertsState.currentPage ? 'active' : ''}`,
        onClick: () => goToPage(i),
        'aria-label': `Page ${i}`,
        'aria-current': i === AlertsState.currentPage ? 'page' : null,
      }, i.toString());
      
      pages.appendChild(btn);
    }
  }
}

// ============================================
// Pagination & Other Functions
// ============================================

function goToPage(page) {
  AlertsState.currentPage = Math.max(1, Math.min(page, AlertsState.totalPages));
  renderAlerts();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function changePageSize() {
  const select = u.$('#page-size');
  if (select) {
    AlertsState.pageSize = parseInt(select.value);
    AlertsState.totalPages = Math.ceil(AlertsState.filteredAlerts.length / AlertsState.pageSize);
    AlertsState.currentPage = 1;
    renderAlerts();
    app.setSetting('pageSize', AlertsState.pageSize);
  }
}

function setupSorting() {
  const sortButtons = u.$$('.table-sort');
  
  sortButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const sortBy = btn.getAttribute('data-sort');
      
      if (AlertsState.sortBy === sortBy) {
        AlertsState.sortOrder = AlertsState.sortOrder === 'asc' ? 'desc' : 'asc';
      } else {
        AlertsState.sortBy = sortBy;
        AlertsState.sortOrder = 'desc';
      }
      
      sortButtons.forEach(b => {
        b.classList.remove('active');
        b.removeAttribute('data-order');
        const indicator = b.querySelector('.sort-indicator');
        if (indicator) indicator.textContent = '';
      });
      
      btn.classList.add('active');
      btn.setAttribute('data-order', AlertsState.sortOrder);
      const indicator = btn.querySelector('.sort-indicator');
      if (indicator) {
        indicator.textContent = AlertsState.sortOrder === 'asc' ? '↑' : '↓';
      }
      
      applyFilters();
      renderAlerts();
    });
  });
}

function toggleAlertSelection(alertId, checked) {
  if (checked) {
    AlertsState.selectedAlerts.add(alertId);
  } else {
    AlertsState.selectedAlerts.delete(alertId);
  }
  
  updateBulkActions();
}

function toggleSelectAll() {
  const checkbox = u.$('#select-all-alerts');
  if (!checkbox) return;
  
  const start = (AlertsState.currentPage - 1) * AlertsState.pageSize;
  const end = start + AlertsState.pageSize;
  const pageAlerts = AlertsState.filteredAlerts.slice(start, end);
  
  if (checkbox.checked) {
    pageAlerts.forEach(alert => AlertsState.selectedAlerts.add(alert._id));
  } else {
    pageAlerts.forEach(alert => AlertsState.selectedAlerts.delete(alert._id));
  }
  
  renderAlerts();
  updateBulkActions();
}

function updateBulkActions() {
  const bulkBar = u.$('#bulk-actions-bar');
  const count = u.$('#selected-count');
  
  if (!bulkBar) return;
  
  if (AlertsState.selectedAlerts.size > 0) {
    u.show(bulkBar);
    if (count) {
      count.textContent = `${AlertsState.selectedAlerts.size} selected`;
    }
  } else {
    u.hide(bulkBar);
  }
}

function switchViewMode(mode) {
  AlertsState.viewMode = mode;
  
  const tableView = u.$('#table-view-section');
  const cardView = u.$('#card-view-section');
  const tableBtn = u.$('#view-table');
  const cardBtn = u.$('#view-cards');
  
  if (mode === 'table') {
    u.show(tableView);
    u.hide(cardView);
    if (tableBtn) {
      tableBtn.classList.add('active');
      tableBtn.setAttribute('aria-pressed', 'true');
    }
    if (cardBtn) {
      cardBtn.classList.remove('active');
      cardBtn.setAttribute('aria-pressed', 'false');
    }
  } else {
    u.hide(tableView);
    u.show(cardView);
    if (tableBtn) {
      tableBtn.classList.remove('active');
      tableBtn.setAttribute('aria-pressed', 'false');
    }
    if (cardBtn) {
      cardBtn.classList.add('active');
      cardBtn.setAttribute('aria-pressed', 'true');
    }
  }
  
  renderAlerts();
}

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
  ];
  
  const detailsGrid = u.createElement('div', { className: 'details-grid' });
  
  details.forEach(({ label, value }) => {
    const row = u.createElement('div', { className: 'detail-row' }, [
      u.createElement('dt', { className: 'detail-label' }, label),
      u.createElement('dd', { className: 'detail-value' }, value),
    ]);
    detailsGrid.appendChild(row);
  });
  
  body.appendChild(detailsGrid);
  app.openModal('alert-detail-modal');
}

function updateResultsCount() {
  const count = u.$('#results-count');
  if (count) {
    const total = AlertsState.filteredAlerts.length;
    count.textContent = `${u.formatNumber(total)} alert${total !== 1 ? 's' : ''} found`;
  }
}

// ============================================
// Event Listeners
// ============================================

function initEventListeners() {
  const filterForm = u.$('#alerts-filter-form');
  if (filterForm) {
    filterForm.addEventListener('submit', (e) => {
      e.preventDefault();
      AlertsState.filters.search = u.$('#search-input')?.value || '';
      AlertsState.filters.severity = u.$('#severity-filter')?.value || '';
      AlertsState.filters.attackType = u.$('#attack-type-filter')?.value || '';
      AlertsState.filters.session = u.$('#session-filter')?.value || '';
      AlertsState.filters.dateFrom = u.$('#date-from')?.value || '';
      AlertsState.filters.dateTo = u.$('#date-to')?.value || '';
      
      applyFilters();
      renderAlerts();
      updateActiveFilters();
      updateResultsCount();
    });
  }
  
  const searchInput = u.$('#search-input');
  if (searchInput) {
    searchInput.addEventListener('input', u.debounce((e) => {
      AlertsState.filters.search = e.target.value;
      applyFilters();
      renderAlerts();
      updateActiveFilters();
      updateResultsCount();
      
      const clearBtn = u.$('#search-clear');
      if (clearBtn) clearBtn.hidden = !e.target.value;
    }, 300));
  }
  
  const searchClear = u.$('#search-clear');
  if (searchClear) {
    searchClear.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      AlertsState.filters.search = '';
      searchClear.hidden = true;
      applyFilters();
      renderAlerts();
      updateActiveFilters();
      updateResultsCount();
    });
  }
  
  const resetBtn = u.$('#reset-filters-btn');
  if (resetBtn) resetBtn.addEventListener('click', resetFilters);
  
  const clearAllBtn = u.$('#clear-all-filters');
  if (clearAllBtn) clearAllBtn.addEventListener('click', resetFilters);
  
  const viewTableBtn = u.$('#view-table');
  const viewCardsBtn = u.$('#view-cards');
  if (viewTableBtn) viewTableBtn.addEventListener('click', () => switchViewMode('table'));
  if (viewCardsBtn) viewCardsBtn.addEventListener('click', () => switchViewMode('cards'));
  
  const firstPageBtn = u.$('#first-page');
  const prevPageBtn = u.$('#prev-page');
  const nextPageBtn = u.$('#next-page');
  const lastPageBtn = u.$('#last-page');
  
  if (firstPageBtn) firstPageBtn.addEventListener('click', () => goToPage(1));
  if (prevPageBtn) prevPageBtn.addEventListener('click', () => goToPage(AlertsState.currentPage - 1));
  if (nextPageBtn) nextPageBtn.addEventListener('click', () => goToPage(AlertsState.currentPage + 1));
  if (lastPageBtn) lastPageBtn.addEventListener('click', () => goToPage(AlertsState.totalPages));
  
  const pageSizeSelect = u.$('#page-size');
  if (pageSizeSelect) {
    pageSizeSelect.value = app.getSetting('pageSize') || 25;
    AlertsState.pageSize = parseInt(pageSizeSelect.value);
    pageSizeSelect.addEventListener('change', changePageSize);
  }
  
  const selectAllCheckbox = u.$('#select-all-alerts');
  if (selectAllCheckbox) {
    selectAllCheckbox.addEventListener('change', toggleSelectAll);
  }
  
  const closeBulkBtn = u.$('#close-bulk-actions');
  if (closeBulkBtn) {
    closeBulkBtn.addEventListener('click', () => {
      AlertsState.selectedAlerts.clear();
      updateBulkActions();
      renderAlerts();
    });
  }
  
  setupSorting();
  
  // Export button
  const exportBtn = u.$('#export-alerts-btn');
  if (exportBtn) {
    exportBtn.addEventListener('click', showExportModal);
  }
  
  const exportCsvBtn = u.$('#export-csv-btn');
  if (exportCsvBtn) {
    exportCsvBtn.addEventListener('click', () => exportAlerts('csv'));
  }
  
  const exportJsonBtn = u.$('#export-json-btn');
  if (exportJsonBtn) {
    exportJsonBtn.addEventListener('click', () => exportAlerts('json'));
  }
}

// ============================================
// Export Functions
// ============================================

function showExportModal() {
  app.openModal('export-modal');
}

async function exportAlerts(format) {
  try {
    app.showLoading();
    
    const options = {
      format,
      limit: 1000,
      severity: AlertsState.filters.severity,
      attackType: AlertsState.filters.attackType,
    };
    
    if (format === 'csv') {
      const blob = await api.exportAlerts(options);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nids_alerts_${Date.now()}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      app.showToast('Alerts exported as CSV', 'success');
    } else {
      const data = await api.exportAlerts(options);
      const json = JSON.stringify(data, null, 2);
      const blob = new Blob([json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `nids_alerts_${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      
      app.showToast('Alerts exported as JSON', 'success');
    }
    
    app.closeModal('export-modal');
    
  } catch (error) {
    app.handleError(error, 'Exporting alerts');
  } finally {
    app.hideLoading();
  }
}

// ============================================
// Initialization
// ============================================

async function initAlertsPage() {
  console.log('🚨 Initializing alerts page...');
  
  initEventListeners();
  await loadAlertsData();
  
  console.log('✅ Alerts page initialized');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAlertsPage);
} else {
  initAlertsPage();
}
