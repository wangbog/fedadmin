/**
 * Federation forms functionality
 * Handles form interactions specific to federation management
 */
$(document).ready(function () {
    /**
     * Federation form submission confirmation
     * Shows warning before submitting Federation form changes
     */
    if (isOnPage('/federation/federation_config/')) {
        $('form[method="POST"]').on('submit', function (e) {
            if (!confirm("⚠️  WARNING: Modifying federation configuration will trigger automatic re-transformation of all entities and regeneration of federation metadata.\n\nAre you sure you want to save?")) {
                e.preventDefault();
                return false;
            }
            return true;
        });
    }
});