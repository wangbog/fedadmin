/**
 * Form utility functions for consistent behavior across forms
 */

/**
 * Check if we're in edit mode based on URL path
 * @returns {boolean} True if in edit mode
 */
function isEditMode() {
    return window.location.pathname.includes('/edit/');
}

/**
 * Check if we're on a specific page based on URL path
 * @param {string} path - Path to check for
 * @returns {boolean} True if on the specified page
 */
function isOnPage(path) {
    return window.location.pathname.includes(path);
}

/**
 * Safely get an element by selector
 * @param {string} selector - jQuery selector
 * @returns {jQuery|null} jQuery object if found, null otherwise
 */
function getElement(selector) {
    return $(selector).length > 0 ? $(selector) : null;
}