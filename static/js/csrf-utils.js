/**
 * WORLD-CLASS: CSRF Utility Functions
 * 
 * Provides helper functions for handling Django CSRF tokens in AJAX requests
 * Following Django's official documentation and best practices
 */

/**
 * Get CSRF token from cookie
 * 
 * Django stores the CSRF token in a cookie named 'csrftoken'
 * This function retrieves it for use in AJAX requests
 * 
 * @param {string} name - Cookie name (default: 'csrftoken')
 * @returns {string|null} - CSRF token value or null if not found
 */
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

/**
 * Get CSRF token for AJAX requests
 * 
 * @returns {string|null} - CSRF token value
 */
function getCSRFToken() {
    return getCookie('csrftoken');
}

/**
 * Get headers for AJAX requests with CSRF token
 * 
 * Returns an object with headers needed for Django AJAX requests:
 * - Content-Type: application/json
 * - X-CSRFToken: CSRF token from cookie
 * - X-Requested-With: XMLHttpRequest (identifies AJAX requests)
 * 
 * @param {Object} additionalHeaders - Additional headers to include
 * @returns {Object} - Headers object for fetch requests
 */
function getAjaxHeaders(additionalHeaders = {}) {
    return {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken(),
        'X-Requested-With': 'XMLHttpRequest',
        ...additionalHeaders
    };
}

/**
 * Make a POST request with CSRF protection
 * 
 * Convenience function for making POST requests with proper CSRF handling
 * 
 * @param {string} url - URL to POST to
 * @param {Object} data - Data to send (will be JSON stringified)
 * @param {Object} options - Additional fetch options
 * @returns {Promise<Response>} - Fetch promise
 */
async function postWithCSRF(url, data, options = {}) {
    return fetch(url, {
        method: 'POST',
        headers: getAjaxHeaders(options.headers || {}),
        credentials: 'same-origin',
        body: JSON.stringify(data),
        ...options
    });
}

/**
 * Make a PUT request with CSRF protection
 * 
 * @param {string} url - URL to PUT to
 * @param {Object} data - Data to send (will be JSON stringified)
 * @param {Object} options - Additional fetch options
 * @returns {Promise<Response>} - Fetch promise
 */
async function putWithCSRF(url, data, options = {}) {
    return fetch(url, {
        method: 'PUT',
        headers: getAjaxHeaders(options.headers || {}),
        credentials: 'same-origin',
        body: JSON.stringify(data),
        ...options
    });
}

/**
 * Make a DELETE request with CSRF protection
 * 
 * @param {string} url - URL to DELETE
 * @param {Object} options - Additional fetch options
 * @returns {Promise<Response>} - Fetch promise
 */
async function deleteWithCSRF(url, options = {}) {
    return fetch(url, {
        method: 'DELETE',
        headers: getAjaxHeaders(options.headers || {}),
        credentials: 'same-origin',
        ...options
    });
}

// Export functions for use in other scripts
if (typeof window !== 'undefined') {
    window.getCookie = getCookie;
    window.getCSRFToken = getCSRFToken;
    window.getAjaxHeaders = getAjaxHeaders;
    window.postWithCSRF = postWithCSRF;
    window.putWithCSRF = putWithCSRF;
    window.deleteWithCSRF = deleteWithCSRF;
}
