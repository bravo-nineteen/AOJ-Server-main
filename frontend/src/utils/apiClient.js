/**
 * API Client Utility with Response Validation
 * Provides type-safe API calls with automatic error handling and response validation
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Standardized API response structure
 * @typedef {Object} APIResponse
 * @property {boolean} success - Whether the request succeeded
 * @property {*} data - Response payload (present on success)
 * @property {Object} error - Error details (present on failure)
 * @property {Object} meta - Metadata (pagination, timing, etc)
 */

class APIError extends Error {
  constructor(code, message, details, requestId) {
    super(message);
    this.code = code;
    this.details = details;
    this.requestId = requestId;
    this.name = 'APIError';
  }
}

/**
 * Validates API response structure
 * @param {*} response - Response object to validate
 * @returns {APIResponse} Validated response
 * @throws {APIError} If response is invalid
 */
function validateResponse(response, requestId = null) {
  if (!response || typeof response !== 'object') {
    throw new APIError(
      'INVALID_RESPONSE',
      'API returned invalid response format',
      { received: typeof response },
      requestId
    );
  }

  // Handle error responses
  if (response.success === false) {
    const error = response.error || {};
    throw new APIError(
      error.code || 'UNKNOWN_ERROR',
      error.message || 'An error occurred',
      error.details,
      error.request_id || requestId
    );
  }

  // Validate success response
  if (response.success !== true) {
    throw new APIError(
      'INVALID_RESPONSE',
      'Response missing success field',
      { received: response },
      requestId
    );
  }

  return response;
}

/**
 * Make an authenticated HTTP request with response validation
 * @param {string} method - HTTP method (GET, POST, PUT, DELETE, etc)
 * @param {string} path - API path (e.g., '/api/missions')
 * @param {Object} options - Request options
 * @returns {Promise<*>} Response data on success
 * @throws {APIError} With standardized error structure
 */
async function request(method, path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const requestId = generateRequestId();

  try {
    const response = await fetch(url, {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-Request-ID': requestId,
        ...options.headers,
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      ...options,
    });

    const contentType = response.headers.get('content-type');
    
    // Handle non-JSON responses
    if (!contentType?.includes('application/json')) {
      if (!response.ok) {
        throw new APIError(
          'HTTP_ERROR',
          `HTTP ${response.status}: ${response.statusText}`,
          { status: response.status },
          requestId
        );
      }
      // For successful non-JSON responses (e.g., files), return text
      return { data: await response.text() };
    }

    // Parse JSON response
    let data;
    try {
      data = await response.json();
    } catch {
      throw new APIError(
        'PARSE_ERROR',
        'Failed to parse response JSON',
        { status: response.status },
        requestId
      );
    }

    // HTTP error with JSON error structure
    if (!response.ok) {
      const error = data.error || {};
      throw new APIError(
        error.code || `HTTP_${response.status}`,
        error.message || response.statusText,
        { ...error.details, status: response.status },
        error.request_id || requestId
      );
    }

    // Validate and return success response
    const validated = validateResponse(data, requestId);
    return validated.data;
  } catch (error) {
    // Re-throw APIErrors as-is
    if (error instanceof APIError) {
      throw error;
    }

    // Convert fetch errors to APIErrors
    if (error instanceof TypeError && error.message.includes('fetch')) {
      throw new APIError(
        'NETWORK_ERROR',
        'Failed to connect to server. Check your network connection.',
        { originalError: error.message },
        requestId
      );
    }

    // Unknown errors
    throw new APIError(
      'UNKNOWN_ERROR',
      error.message || 'An unexpected error occurred',
      { originalError: error.toString() },
      requestId
    );
  }
}

/**
 * Generate a request ID for tracing
 * @returns {string} Unique request ID
 */
function generateRequestId() {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

// ============================================
// Convenience methods for common HTTP verbs
// ============================================

const api = {
  /**
   * GET request
   * @param {string} path - API path
   * @param {Object} options - Optional request options
   * @returns {Promise<*>} Response data
   */
  get: (path, options = {}) => request('GET', path, options),

  /**
   * POST request with validation
   * @param {string} path - API path
   * @param {*} body - Request body
   * @param {Object} options - Optional request options
   * @returns {Promise<*>} Response data
   */
  post: (path, body, options = {}) =>
    request('POST', path, { ...options, body }),

  /**
   * PUT request with validation
   * @param {string} path - API path
   * @param {*} body - Request body
   * @param {Object} options - Optional request options
   * @returns {Promise<*>} Response data
   */
  put: (path, body, options = {}) =>
    request('PUT', path, { ...options, body }),

  /**
   * PATCH request with validation
   * @param {string} path - API path
   * @param {*} body - Request body
   * @param {Object} options - Optional request options
   * @returns {Promise<*>} Response data
   */
  patch: (path, body, options = {}) =>
    request('PATCH', path, { ...options, body }),

  /**
   * DELETE request with validation
   * @param {string} path - API path
   * @param {Object} options - Optional request options
   * @returns {Promise<*>} Response data
   */
  delete: (path, options = {}) => request('DELETE', path, options),

  /**
   * Handle API errors with user-friendly messages
   * @param {Error} error - Error object
   * @returns {string} User-friendly error message
   */
  getErrorMessage(error) {
    if (error instanceof APIError) {
      // Map common error codes to user-friendly messages
      const messages = {
        NETWORK_ERROR: 'Network connection failed. Please check your connection.',
        VALIDATION_ERROR: 'Invalid input. Please check your entries.',
        NOT_FOUND: 'The requested item was not found.',
        UNAUTHORIZED: 'You are not authorized. Please log in again.',
        FORBIDDEN: 'You do not have permission to perform this action.',
        CONFLICT: 'This action conflicts with existing data.',
        SERVICE_UNAVAILABLE: 'The service is temporarily unavailable. Please try again later.',
        INVALID_STATE: 'This action cannot be performed in the current state.',
      };
      return messages[error.code] || error.message;
    }
    return error.message || 'An unexpected error occurred';
  },

  /**
   * Log API error for debugging
   * @param {Error} error - Error object
   * @param {string} context - Context where error occurred
   */
  logError(error, context = 'API Call') {
    if (error instanceof APIError) {
      console.error(`${context} Failed [${error.code}]:`, {
        message: error.message,
        details: error.details,
        requestId: error.requestId,
      });
    } else {
      console.error(`${context} Failed:`, error);
    }
  },
};

export default api;
export { APIError, validateResponse, generateRequestId };
