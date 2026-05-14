/**
 * Organization forms functionality
 * Handles form interactions specific to organization management
 */
$(document).ready(function () {
    /**
     * Organization form submission confirmation
     * Shows warning before submitting Organization form changes
     */
    if (isOnPage('/member/member_organization/')) {
        $('form[method="POST"]').on('submit', function (e) {
            if (!confirm("⚠️  WARNING: Modifying this organization will trigger automatic re-transformation of all entities in this organization and regeneration of federation metadata.\n\nAre you sure you want to save?")) {
                e.preventDefault();
                return false;
            }
            return true;
        });
    }
});