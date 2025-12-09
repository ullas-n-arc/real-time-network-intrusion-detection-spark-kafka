/**
 * NIDS Dashboard - Settings Page JavaScript
 * User preferences and system configuration management
 */

// ============================================
// Settings State
// ============================================

const SettingsState = {
  settings: {
    theme: 'dark',
    accentColor: '#3b82f6',
    fontSize: 'medium',
    notifications: true,
    soundAlerts: false,
    autoRefresh: true,
    refreshInterval: 30,
    pageSize: 25,
  },
  modified: false,
};

// ============================================
// Load Settings
// ============================================

function loadSettings() {
  const saved = u.getLocal('nids_settings');
  if (saved) {
    SettingsState.settings = { ...SettingsState.settings, ...saved };
  }
  
  applySettings();
  populateForm();
}

function populateForm() {
  // Theme
  const themeRadios = document.querySelectorAll('input[name="theme"]');
  themeRadios.forEach(radio => {
    radio.checked = radio.value === SettingsState.settings.theme;
  });
  
  // Accent color
  const accentColor = u.$('#accent-color');
  if (accentColor) accentColor.value = SettingsState.settings.accentColor;
  
  const accentPreview = u.$('#accent-preview');
  if (accentPreview) accentPreview.style.backgroundColor = SettingsState.settings.accentColor;
  
  // Font size
  const fontSize = u.$('#font-size');
  if (fontSize) fontSize.value = SettingsState.settings.fontSize;
  
  // Notifications
  const notifications = u.$('#enable-notifications');
  if (notifications) notifications.checked = SettingsState.settings.notifications;
  
  const soundAlerts = u.$('#sound-alerts');
  if (soundAlerts) soundAlerts.checked = SettingsState.settings.soundAlerts;
  
  // Auto refresh
  const autoRefresh = u.$('#enable-auto-refresh');
  if (autoRefresh) autoRefresh.checked = SettingsState.settings.autoRefresh;
  
  const refreshInterval = u.$('#refresh-interval');
  if (refreshInterval) refreshInterval.value = SettingsState.settings.refreshInterval;
  
  // Page size
  const pageSize = u.$('#default-page-size');
  if (pageSize) pageSize.value = SettingsState.settings.pageSize;
}

function applySettings() {
  // Apply theme
  document.documentElement.setAttribute('data-theme', SettingsState.settings.theme);
  
  // Apply accent color
  document.documentElement.style.setProperty('--color-primary', SettingsState.settings.accentColor);
  
  // Apply font size
  const fontSizeMap = {
    small: '14px',
    medium: '16px',
    large: '18px',
  };
  document.documentElement.style.setProperty('--font-size-base', fontSizeMap[SettingsState.settings.fontSize] || '16px');
  
  // Store in localStorage
  u.setLocal('nids_settings', SettingsState.settings);
}

// ============================================
// Event Handlers
// ============================================

function handleThemeChange(event) {
  SettingsState.settings.theme = event.target.value;
  SettingsState.modified = true;
  applySettings();
  app.showToast(`Theme changed to ${event.target.value}`, 'success');
}

function handleAccentColorChange(event) {
  SettingsState.settings.accentColor = event.target.value;
  SettingsState.modified = true;
  
  const preview = u.$('#accent-preview');
  if (preview) preview.style.backgroundColor = event.target.value;
  
  applySettings();
}

function handleFontSizeChange(event) {
  SettingsState.settings.fontSize = event.target.value;
  SettingsState.modified = true;
  applySettings();
  app.showToast(`Font size changed to ${event.target.value}`, 'success');
}

function handleNotificationsChange(event) {
  SettingsState.settings.notifications = event.target.checked;
  SettingsState.modified = true;
  applySettings();
  
  if (event.target.checked) {
    requestNotificationPermission();
  }
}

function handleSoundAlertsChange(event) {
  SettingsState.settings.soundAlerts = event.target.checked;
  SettingsState.modified = true;
  applySettings();
}

function handleAutoRefreshChange(event) {
  SettingsState.settings.autoRefresh = event.target.checked;
  SettingsState.modified = true;
  applySettings();
  
  app.showToast(`Auto-refresh ${event.target.checked ? 'enabled' : 'disabled'}`, 'info');
}

function handleRefreshIntervalChange(event) {
  const value = parseInt(event.target.value);
  if (value >= 10 && value <= 300) {
    SettingsState.settings.refreshInterval = value;
    SettingsState.modified = true;
    applySettings();
  }
}

function handlePageSizeChange(event) {
  SettingsState.settings.pageSize = parseInt(event.target.value);
  SettingsState.modified = true;
  applySettings();
}

// ============================================
// Notifications
// ============================================

async function requestNotificationPermission() {
  if (!('Notification' in window)) {
    app.showToast('Notifications not supported in this browser', 'error');
    return;
  }
  
  if (Notification.permission === 'granted') {
    app.showToast('Notifications already enabled', 'success');
    return;
  }
  
  if (Notification.permission !== 'denied') {
    const permission = await Notification.requestPermission();
    if (permission === 'granted') {
      app.showToast('Notifications enabled', 'success');
      showTestNotification();
    } else {
      app.showToast('Notification permission denied', 'error');
      SettingsState.settings.notifications = false;
      const checkbox = u.$('#enable-notifications');
      if (checkbox) checkbox.checked = false;
    }
  } else {
    app.showToast('Notifications blocked. Please enable in browser settings.', 'error');
  }
}

function showTestNotification() {
  if (Notification.permission === 'granted') {
    new Notification('NIDS Dashboard', {
      body: 'Notifications are now enabled',
      icon: '/static/favicon.ico',
    });
  }
}

// ============================================
// Data Management
// ============================================

function clearCache() {
  const confirmed = confirm('Clear all cached data? This will refresh the page.');
  
  if (confirmed) {
    // Clear session storage
    sessionStorage.clear();
    
    // Clear specific localStorage items (preserve settings)
    const keysToRemove = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key && key !== 'nids_settings') {
        keysToRemove.push(key);
      }
    }
    keysToRemove.forEach(key => localStorage.removeItem(key));
    
    app.showToast('Cache cleared', 'success');
    
    setTimeout(() => {
      window.location.reload();
    }, 1000);
  }
}

function exportSettings() {
  const data = {
    version: '1.0',
    exported: new Date().toISOString(),
    settings: SettingsState.settings,
  };
  
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const a = document.createElement('a');
  a.href = url;
  a.download = `nids-settings-${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  
  app.showToast('Settings exported', 'success');
}

function importSettings() {
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = 'application/json';
  
  input.onchange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    try {
      const text = await file.text();
      const data = JSON.parse(text);
      
      if (data.version && data.settings) {
        SettingsState.settings = { ...SettingsState.settings, ...data.settings };
        applySettings();
        populateForm();
        app.showToast('Settings imported successfully', 'success');
      } else {
        app.showToast('Invalid settings file', 'error');
      }
    } catch (error) {
      app.showToast('Failed to import settings', 'error');
      console.error('Import error:', error);
    }
  };
  
  input.click();
}

function resetSettings() {
  const confirmed = confirm('Reset all settings to defaults?');
  
  if (confirmed) {
    SettingsState.settings = {
      theme: 'dark',
      accentColor: '#3b82f6',
      fontSize: 'medium',
      notifications: true,
      soundAlerts: false,
      autoRefresh: true,
      refreshInterval: 30,
      pageSize: 25,
    };
    
    applySettings();
    populateForm();
    app.showToast('Settings reset to defaults', 'success');
  }
}

// ============================================
// System Information
// ============================================

async function loadSystemInfo() {
  try {
    const health = await api.getHealth();
    
    const statusBadge = u.$('#system-status-badge');
    const statusText = u.$('#system-status-text');
    const lastUpdate = u.$('#last-system-update');
    
    if (health && health.status === 'healthy') {
      if (statusBadge) {
        statusBadge.className = 'status-badge status-success';
        statusBadge.textContent = 'Operational';
      }
      if (statusText) statusText.textContent = 'All systems operational';
    } else {
      if (statusBadge) {
        statusBadge.className = 'status-badge status-error';
        statusBadge.textContent = 'Issues Detected';
      }
      if (statusText) statusText.textContent = 'Some services may be unavailable';
    }
    
    if (lastUpdate) {
      lastUpdate.textContent = `Last checked: ${u.formatDate(new Date())}`;
    }
    
  } catch (error) {
    console.error('Failed to load system info:', error);
    
    const statusBadge = u.$('#system-status-badge');
    const statusText = u.$('#system-status-text');
    
    if (statusBadge) {
      statusBadge.className = 'status-badge status-error';
      statusBadge.textContent = 'Unknown';
    }
    if (statusText) statusText.textContent = 'Unable to check system status';
  }
}

async function checkForUpdates() {
  app.showLoading();
  
  // Simulate update check
  setTimeout(() => {
    app.hideLoading();
    app.showToast('You are running the latest version', 'success');
  }, 1500);
}

// ============================================
// Storage Usage
// ============================================

function updateStorageInfo() {
  const localStorageSize = new Blob(Object.values(localStorage)).size;
  const sessionStorageSize = new Blob(Object.values(sessionStorage)).size;
  
  const localStorageEl = u.$('#local-storage-usage');
  const sessionStorageEl = u.$('#session-storage-usage');
  
  if (localStorageEl) {
    localStorageEl.textContent = u.formatBytes(localStorageSize);
  }
  
  if (sessionStorageEl) {
    sessionStorageEl.textContent = u.formatBytes(sessionStorageSize);
  }
}

// ============================================
// Keyboard Shortcuts
// ============================================

function showKeyboardShortcuts() {
  const shortcuts = [
    { key: 'Ctrl + K', description: 'Quick search' },
    { key: 'Ctrl + B', description: 'Toggle sidebar' },
    { key: 'Ctrl + T', description: 'Toggle theme' },
    { key: 'Ctrl + R', description: 'Refresh data' },
    { key: 'Esc', description: 'Close modal' },
    { key: '/', description: 'Focus search' },
  ];
  
  const list = u.createElement('ul', { className: 'shortcuts-list' });
  
  shortcuts.forEach(({ key, description }) => {
    const item = u.createElement('li', { className: 'shortcut-item' }, [
      u.createElement('kbd', {}, key),
      u.createElement('span', {}, description),
    ]);
    list.appendChild(item);
  });
  
  const modal = app.createModal('keyboard-shortcuts', 'Keyboard Shortcuts', list);
  document.body.appendChild(modal);
  app.openModal('keyboard-shortcuts');
}

// ============================================
// Event Listeners
// ============================================

function initEventListeners() {
  // Theme radios
  const themeRadios = document.querySelectorAll('input[name="theme"]');
  themeRadios.forEach(radio => {
    radio.addEventListener('change', handleThemeChange);
  });
  
  // Accent color
  const accentColor = u.$('#accent-color');
  if (accentColor) {
    accentColor.addEventListener('input', u.debounce(handleAccentColorChange, 300));
  }
  
  // Font size
  const fontSize = u.$('#font-size');
  if (fontSize) {
    fontSize.addEventListener('change', handleFontSizeChange);
  }
  
  // Notifications
  const notifications = u.$('#enable-notifications');
  if (notifications) {
    notifications.addEventListener('change', handleNotificationsChange);
  }
  
  const soundAlerts = u.$('#sound-alerts');
  if (soundAlerts) {
    soundAlerts.addEventListener('change', handleSoundAlertsChange);
  }
  
  // Auto refresh
  const autoRefresh = u.$('#enable-auto-refresh');
  if (autoRefresh) {
    autoRefresh.addEventListener('change', handleAutoRefreshChange);
  }
  
  const refreshInterval = u.$('#refresh-interval');
  if (refreshInterval) {
    refreshInterval.addEventListener('change', handleRefreshIntervalChange);
  }
  
  // Page size
  const pageSize = u.$('#default-page-size');
  if (pageSize) {
    pageSize.addEventListener('change', handlePageSizeChange);
  }
  
  // Data management buttons
  const clearCacheBtn = u.$('#clear-cache-btn');
  if (clearCacheBtn) {
    clearCacheBtn.addEventListener('click', clearCache);
  }
  
  const exportSettingsBtn = u.$('#export-settings-btn');
  if (exportSettingsBtn) {
    exportSettingsBtn.addEventListener('click', exportSettings);
  }
  
  const importSettingsBtn = u.$('#import-settings-btn');
  if (importSettingsBtn) {
    importSettingsBtn.addEventListener('click', importSettings);
  }
  
  const resetSettingsBtn = u.$('#reset-settings-btn');
  if (resetSettingsBtn) {
    resetSettingsBtn.addEventListener('click', resetSettings);
  }
  
  // System buttons
  const checkUpdatesBtn = u.$('#check-updates-btn');
  if (checkUpdatesBtn) {
    checkUpdatesBtn.addEventListener('click', checkForUpdates);
  }
  
  const refreshSystemBtn = u.$('#refresh-system-status');
  if (refreshSystemBtn) {
    refreshSystemBtn.addEventListener('click', loadSystemInfo);
  }
  
  const keyboardShortcutsBtn = u.$('#keyboard-shortcuts-btn');
  if (keyboardShortcutsBtn) {
    keyboardShortcutsBtn.addEventListener('click', showKeyboardShortcuts);
  }
}

// ============================================
// Initialization
// ============================================

function initSettingsPage() {
  console.log('⚙️ Initializing settings page...');
  
  loadSettings();
  initEventListeners();
  loadSystemInfo();
  updateStorageInfo();
  
  console.log('✅ Settings page initialized');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initSettingsPage);
} else {
  initSettingsPage();
}
