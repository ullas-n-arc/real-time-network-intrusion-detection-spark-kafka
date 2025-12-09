/**
 * NIDS Dashboard - API Client
 * Handles all API requests with error handling and retries
 */

class APIClient {
  constructor(baseURL = '/api') {
    this.baseURL = baseURL;
    this.defaultHeaders = {
      'Content-Type': 'application/json',
    };
    this.timeout = 30000; // 30 seconds
    this.maxRetries = 3;
    this.retryDelay = 1000; // 1 second
  }

  /**
   * Make an HTTP request
   * @param {string} endpoint - API endpoint
   * @param {Object} options - Request options
   * @returns {Promise<any>} Response data
   */
  async request(endpoint, options = {}) {
    const {
      method = 'GET',
      headers = {},
      body = null,
      params = null,
      retries = this.maxRetries,
    } = options;

    // Build URL with query parameters
    let url = `${this.baseURL}${endpoint}`;
    if (params) {
      url += u.buildQueryString(params);
    }

    // Build request config
    const config = {
      method,
      headers: { ...this.defaultHeaders, ...headers },
      signal: AbortSignal.timeout(this.timeout),
    };

    if (body && method !== 'GET' && method !== 'HEAD') {
      config.body = typeof body === 'string' ? body : JSON.stringify(body);
    }

    // Attempt request with retries
    for (let attempt = 0; attempt <= retries; attempt++) {
      try {
        const response = await fetch(url, config);

        // Handle non-OK responses
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          const error = new Error(errorData.error || `HTTP ${response.status}: ${response.statusText}`);
          error.status = response.status;
          error.data = errorData;
          throw error;
        }

        // Parse JSON response
        const data = await response.json();
        return data;

      } catch (error) {
        // Don't retry on client errors (4xx) or if we're out of retries
        if (error.status >= 400 && error.status < 500) {
          throw error;
        }

        if (attempt === retries) {
          console.error(`API request failed after ${retries + 1} attempts:`, error);
          throw error;
        }

        // Wait before retrying
        console.warn(`API request failed (attempt ${attempt + 1}/${retries + 1}), retrying...`);
        await this.sleep(this.retryDelay * (attempt + 1));
      }
    }
  }

  /**
   * Sleep for a specified duration
   * @param {number} ms - Duration in milliseconds
   * @returns {Promise<void>}
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  // ============================================
  // GET Requests
  // ============================================

  /**
   * GET request
   * @param {string} endpoint - API endpoint
   * @param {Object} params - Query parameters
   * @returns {Promise<any>} Response data
   */
  async get(endpoint, params = null) {
    return this.request(endpoint, { method: 'GET', params });
  }

  // ============================================
  // POST Requests
  // ============================================

  /**
   * POST request
   * @param {string} endpoint - API endpoint
   * @param {Object} body - Request body
   * @returns {Promise<any>} Response data
   */
  async post(endpoint, body = null) {
    return this.request(endpoint, { method: 'POST', body });
  }

  // ============================================
  // PUT Requests
  // ============================================

  /**
   * PUT request
   * @param {string} endpoint - API endpoint
   * @param {Object} body - Request body
   * @returns {Promise<any>} Response data
   */
  async put(endpoint, body = null) {
    return this.request(endpoint, { method: 'PUT', body });
  }

  // ============================================
  // DELETE Requests
  // ============================================

  /**
   * DELETE request
   * @param {string} endpoint - API endpoint
   * @param {Object} params - Query parameters
   * @returns {Promise<any>} Response data
   */
  async delete(endpoint, params = null) {
    return this.request(endpoint, { method: 'DELETE', params });
  }

  // ============================================
  // Health Check
  // ============================================

  /**
   * Check API health
   * @returns {Promise<Object>} Health status
   */
  async healthCheck() {
    return this.get('/health');
  }

  // ============================================
  // Alerts Endpoints
  // ============================================

  /**
   * Get recent alerts
   * @param {Object} params - Query parameters
   * @returns {Promise<Array>} Alerts
   */
  async getAlerts(params = {}) {
    return this.get('/alerts', params);
  }

  /**
   * Get alert statistics
   * @param {number} hours - Number of hours to look back
   * @returns {Promise<Object>} Statistics
   */
  async getAlertStats(hours = 24) {
    return this.get('/alerts/stats', { hours });
  }

  /**
   * Get alert timeline
   * @param {number} hours - Number of hours to look back
   * @param {number} interval - Interval in minutes
   * @returns {Promise<Array>} Timeline data
   */
  async getAlertTimeline(hours = 24, interval = 60) {
    return this.get('/alerts/timeline', { hours, interval });
  }

  // ============================================
  // Sessions Endpoints
  // ============================================

  /**
   * Get list of sessions
   * @returns {Promise<Array>} Sessions
   */
  async getSessions() {
    return this.get('/sessions');
  }

  /**
   * Get current session
   * @returns {Promise<Object>} Current session
   */
  async getCurrentSession() {
    return this.get('/session/current');
  }

  /**
   * Set current session
   * @param {string|null} sessionId - Session ID or null for all
   * @returns {Promise<Object>} Result
   */
  async setSession(sessionId) {
    return this.post('/session/set', { session_id: sessionId });
  }

  /**
   * Delete a session
   * @param {string} sessionId - Session ID to delete
   * @returns {Promise<Object>} Result
   */
  async deleteSession(sessionId) {
    return this.delete('/session/delete', { session_id: sessionId });
  }

  /**
   * Delete all sessions
   * @returns {Promise<Object>} Result
   */
  async deleteAllSessions() {
    return this.delete('/sessions/delete-all');
  }

  // ============================================
  // Attack Types Endpoint
  // ============================================

  /**
   * Get attack type mappings
   * @returns {Promise<Object>} Attack type mappings
   */
  async getAttackTypes() {
    return this.get('/attack-types');
  }

  /**
   * Get alert count statistics
   * @param {number} minutes - Minutes to look back for recent count
   * @returns {Promise<Object>} Total and recent alert counts
   */
  async getAlertCount(minutes = 5) {
    return this.get('/alerts/count', { minutes });
  }

  /**
   * Get severity distribution
   * @param {number} hours - Hours to look back
   * @returns {Promise<Object>} Alert counts by severity
   */
  async getSeverityDistribution(hours = 24) {
    return this.get('/alerts/severity-distribution', { hours });
  }

  /**
   * Export alerts
   * @param {Object} options - Export options
   * @param {string} options.format - 'csv' or 'json'
   * @param {number} options.limit - Max alerts
   * @param {string} options.severity - Filter by severity
   * @param {string} options.attackType - Filter by attack type
   * @returns {Promise<Blob>} Export data
   */
  async exportAlerts(options = {}) {
    const params = new URLSearchParams();
    if (options.format) params.append('format', options.format);
    if (options.limit) params.append('limit', options.limit);
    if (options.severity) params.append('severity', options.severity);
    if (options.attackType) params.append('attack_type', options.attackType);
    
    const url = `${this.baseURL}/alerts/export?${params.toString()}`;
    
    if (options.format === 'csv') {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Export failed: ${response.statusText}`);
      }
      return response.blob();
    } else {
      return this.get('/alerts/export', Object.fromEntries(params));
    }
  }

  /**
   * Clear API cache
   * @returns {Promise<Object>} Success response
   */
  async clearCache() {
    return this.post('/cache/clear');
  }

  /**
   * Get version info
   * @returns {Promise<Object>} Version information
   */
  async getVersion() {
    return this.get('/version');
  }
}

// Create global API instance
window.api = new APIClient();
