/**
 * NIDS Dashboard - Main JavaScript
 * Core functionality and UI management
 */

// ============================================
// Global State
// ============================================

const AppState = {
  theme: 'dark',
  autoRefresh: true,
  refreshInterval: 10000, // 10 seconds
  refreshTimer: null,
  connectionStatus: 'connecting',
  settings: {
    notifications: false,
    soundAlerts: false,
    alertThreshold: 'MEDIUM',
    pageSize: 25,
    debugMode: false,
  },
};

// ============================================
// Theme Management
// ============================================

function initTheme() {
  // Load theme from storage or system preference
  const savedTheme = u.loadFromStorage('theme');
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  const theme = savedTheme || systemTheme;
  
  setTheme(theme);
  
  // Listen for theme toggle
  const themeToggle = u.$('#theme-toggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', toggleTheme);
  }
  
  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!u.loadFromStorage('theme')) {
      setTheme(e.matches ? 'dark' : 'light');
    }
  });
}

function setTheme(theme) {
  AppState.theme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  u.saveToStorage('theme', theme);
}

function toggleTheme() {
  const newTheme = AppState.theme === 'dark' ? 'light' : 'dark';
  setTheme(newTheme);
}

// ============================================
// Navigation
// ============================================

function initNavigation() {
  // Mobile menu toggle
  const navbarToggle = u.$('#navbar-toggle');
  const navbarMenu = u.$('#navbar-menu');
  
  if (navbarToggle && navbarMenu) {
    navbarToggle.addEventListener('click', () => {
      const isExpanded = navbarToggle.getAttribute('aria-expanded') === 'true';
      navbarToggle.setAttribute('aria-expanded', !isExpanded);
      navbarMenu.classList.toggle('active');
    });
    
    // Close menu when clicking outside
    document.addEventListener('click', (e) => {
      if (!navbarToggle.contains(e.target) && !navbarMenu.contains(e.target)) {
        navbarToggle.setAttribute('aria-expanded', 'false');
        navbarMenu.classList.remove('active');
      }
    });
  }
}

// ============================================
// Connection Status
// ============================================

async function checkConnection() {
  const statusDot = u.$('#status-dot');
  const statusText = u.$('#status-text');
  
  if (!statusDot || !statusText) return;
  
  try {
    const health = await api.healthCheck();
    
    if (health.mongodb === 'connected') {
      AppState.connectionStatus = 'online';
      statusDot.className = 'status-dot online';
      statusText.textContent = 'Connected';
    } else {
      AppState.connectionStatus = 'degraded';
      statusDot.className = 'status-dot offline';
      statusText.textContent = 'Degraded';
    }
  } catch (error) {
    AppState.connectionStatus = 'offline';
    statusDot.className = 'status-dot offline';
    statusText.textContent = 'Disconnected';
    console.error('Connection check failed:', error);
  }
}

// ============================================
// Toast Notifications
// ============================================

/**
 * Show a toast notification
 * @param {string} message - Notification message
 * @param {string} type - Type (success, error, warning, info)
 * @param {number} duration - Duration in ms (0 = persistent)
 */
function showToast(message, type = 'info', duration = 5000) {
  const container = u.$('#toast-container');
  if (!container) return;
  
  const icons = {
    success: '✅',
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️',
  };
  
  const toast = u.createElement('div', {
    className: `toast toast-${type}`,
    role: 'alert',
    'aria-live': 'polite',
  }, [
    u.createElement('span', { className: 'toast-icon', 'aria-hidden': 'true' }, icons[type] || icons.info),
    u.createElement('div', { className: 'toast-content' }, [
      u.createElement('p', { className: 'toast-message' }, message),
    ]),
    u.createElement('button', {
      className: 'toast-close',
      'aria-label': 'Close notification',
      onClick: () => removeToast(toast),
    }, '×'),
  ]);
  
  container.appendChild(toast);
  
  // Auto-remove after duration
  if (duration > 0) {
    setTimeout(() => removeToast(toast), duration);
  }
  
  return toast;
}

function removeToast(toast) {
  toast.style.opacity = '0';
  toast.style.transform = 'translateX(400px)';
  setTimeout(() => toast.remove(), 300);
}

// ============================================
// Loading Overlay
// ============================================

function showLoading() {
  const overlay = u.$('#loading-overlay');
  if (overlay) {
    overlay.classList.add('active');
    overlay.removeAttribute('aria-hidden');
  }
}

function hideLoading() {
  const overlay = u.$('#loading-overlay');
  if (overlay) {
    overlay.classList.remove('active');
    overlay.setAttribute('aria-hidden', 'true');
  }
}

// ============================================
// Modal Management
// ============================================

function initModals() {
  // Close modal when clicking backdrop or close button
  document.addEventListener('click', (e) => {
    if (e.target.hasAttribute('data-close-modal')) {
      const modal = e.target.closest('.modal');
      if (modal) closeModal(modal);
    }
  });
  
  // Close modal on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const modal = u.$('.modal:not([hidden])');
      if (modal) closeModal(modal);
    }
  });
}

function openModal(modalId) {
  const modal = u.$(`#${modalId}`);
  if (!modal) return;
  
  modal.removeAttribute('hidden');
  
  // Focus first focusable element
  const focusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
  if (focusable) {
    setTimeout(() => focusable.focus(), 100);
  }
  
  // Prevent body scroll
  document.body.style.overflow = 'hidden';
}

function closeModal(modal) {
  if (typeof modal === 'string') {
    modal = u.$(`#${modal}`);
  }
  
  if (!modal) return;
  
  modal.setAttribute('hidden', '');
  
  // Restore body scroll
  document.body.style.overflow = '';
}

// ============================================
// Form Validation
// ============================================

function validateForm(form) {
  const inputs = form.querySelectorAll('[required]');
  let isValid = true;
  
  inputs.forEach(input => {
    if (!validateInput(input)) {
      isValid = false;
    }
  });
  
  return isValid;
}

function validateInput(input) {
  const value = input.value.trim();
  let isValid = true;
  let errorMessage = '';
  
  // Required check
  if (input.hasAttribute('required') && u.isEmpty(value)) {
    isValid = false;
    errorMessage = 'This field is required';
  }
  
  // Type-specific validation
  if (isValid && value) {
    const type = input.getAttribute('type');
    
    switch (type) {
      case 'email':
        if (!u.isValidEmail(value)) {
          isValid = false;
          errorMessage = 'Please enter a valid email address';
        }
        break;
        
      case 'number':
        const num = parseFloat(value);
        const min = input.getAttribute('min');
        const max = input.getAttribute('max');
        
        if (isNaN(num)) {
          isValid = false;
          errorMessage = 'Please enter a valid number';
        } else if (min !== null && num < parseFloat(min)) {
          isValid = false;
          errorMessage = `Value must be at least ${min}`;
        } else if (max !== null && num > parseFloat(max)) {
          isValid = false;
          errorMessage = `Value must be at most ${max}`;
        }
        break;
    }
  }
  
  // Show/hide error message
  showInputError(input, isValid ? null : errorMessage);
  
  return isValid;
}

function showInputError(input, message) {
  // Remove existing error
  const existingError = input.parentElement.querySelector('.input-error');
  if (existingError) existingError.remove();
  
  if (message) {
    input.classList.add('error');
    input.setAttribute('aria-invalid', 'true');
    
    const error = u.createElement('span', {
      className: 'input-error',
      role: 'alert',
    }, message);
    
    input.parentElement.appendChild(error);
  } else {
    input.classList.remove('error');
    input.removeAttribute('aria-invalid');
  }
}

// ============================================
// Settings Management
// ============================================

function loadSettings() {
  const saved = u.loadFromStorage('nids-settings');
  if (saved) {
    AppState.settings = { ...AppState.settings, ...saved };
  }
}

function saveSettings() {
  u.saveToStorage('nids-settings', AppState.settings);
}

function getSetting(key) {
  return AppState.settings[key];
}

function setSetting(key, value) {
  AppState.settings[key] = value;
  saveSettings();
}

// ============================================
// Keyboard Shortcuts
// ============================================

function initKeyboardShortcuts() {
  document.addEventListener('keydown', (e) => {
    // Ignore if typing in input
    if (e.target.matches('input, textarea, select')) return;
    
    // Ctrl/Cmd + K: Focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      const search = u.$('#search-input');
      if (search) search.focus();
    }
    
    // R: Refresh
    if (e.key === 'r' && !e.ctrlKey && !e.metaKey) {
      e.preventDefault();
      const refreshBtn = u.$('#refresh-btn');
      if (refreshBtn) refreshBtn.click();
    }
    
    // ?: Show keyboard shortcuts help
    if (e.key === '?' && !e.shiftKey) {
      // TODO: Implement shortcuts help modal
    }
  });
}

// ============================================
// Accessibility Improvements
// ============================================

function initAccessibility() {
  // Announce page changes to screen readers
  const announcer = u.createElement('div', {
    className: 'visually-hidden',
    role: 'status',
    'aria-live': 'polite',
    'aria-atomic': 'true',
    id: 'aria-announcer',
  });
  document.body.appendChild(announcer);
  
  // Skip link functionality
  const skipLink = u.$('.skip-link');
  if (skipLink) {
    skipLink.addEventListener('click', (e) => {
      e.preventDefault();
      const target = u.$(skipLink.getAttribute('href'));
      if (target) {
        target.focus();
        target.scrollIntoView();
      }
    });
  }
}

function announce(message) {
  const announcer = u.$('#aria-announcer');
  if (announcer) {
    announcer.textContent = message;
  }
}

// ============================================
// Error Handling
// ============================================

function handleError(error, context = 'Operation') {
  console.error(`${context} failed:`, error);
  
  let message = `${context} failed`;
  
  if (error.message) {
    message = error.message;
  } else if (typeof error === 'string') {
    message = error;
  }
  
  showToast(message, 'error');
  
  // Log to console in debug mode
  if (getSetting('debugMode')) {
    console.group(`Error: ${context}`);
    console.error(error);
    console.trace();
    console.groupEnd();
  }
}

// ============================================
// Initialization
// ============================================

function init() {
  console.log('🛡️ NIDS Dashboard initializing...');
  
  // Load settings
  loadSettings();
  
  // Initialize components
  initTheme();
  initNavigation();
  initModals();
  initAccessibility();
  initKeyboardShortcuts();
  
  // Check connection
  checkConnection();
  setInterval(checkConnection, 30000); // Check every 30 seconds
  
  // Hide loading overlay
  hideLoading();
  
  console.log('✅ NIDS Dashboard initialized');
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// ============================================
// Export to global scope
// ============================================

window.app = {
  state: AppState,
  showToast,
  showLoading,
  hideLoading,
  openModal,
  closeModal,
  validateForm,
  validateInput,
  getSetting,
  setSetting,
  announce,
  handleError,
  checkConnection,
};
