/**
 * Entity forms functionality
 * Handles complex form interactions for entity management
 */
$(document).ready(function () {
    // Cache DOM elements for better performance
    var sirtfiCheckbox = getElement('#sirtfi_enabled');
    var securityNameField = getElement('#security_contact_name').closest('.form-group');
    var securityEmailField = getElement('#security_contact_email').closest('.form-group');
    var securityNameInput = getElement('#security_contact_name');
    var securityEmailInput = getElement('#security_contact_email');

    // Metadata files
    var metadataFileInput = getElement('#idp_metadata_file, #sp_metadata_file');

    // eduGAIN fields
    var edugainSelect = getElement('#idp_edugain, #sp_edugain');
    var entityIdInput = getElement('#idp_entityid, #sp_entityid');

    // Fields to hide in ALREADY_IN mode
    var fieldsToHide = $([
        '#idp_description', '#sp_description',
        '#idp_scope',
        '#idp_logo', '#sp_logo',
        '#contact_technical_name', '#contact_technical_email',
        '#sirtfi_enabled',
        '#security_contact_name', '#security_contact_email',
        '#rs_enabled', '#coco_enabled',
        '#information_url', '#privacy_statement_url',
        '#idp_metadata_file', '#sp_metadata_file'
    ].join(', '));
    var fieldGroupsToHide = fieldsToHide.closest('.form-group');

    // Fields not required in normal mode
    var fieldsNotRequire = $([
        '#sirtfi_enabled',
        '#rs_enabled', '#coco_enabled',
        '#information_url', '#privacy_statement_url'
    ].join(', '));

    // Get default values from data attributes (only present on create form)
    var defaultName = securityNameInput ? securityNameInput.data('default-username') || '' : '';
    var defaultEmail = securityEmailInput ? securityEmailInput.data('default-email') || '' : '';

    /**
     * Update form fields based on current states
     * This is a unified method that handles both eduGAIN and SIRTFI states
     */
    function updateFormFields() {
        try {
            var edugainValue = edugainSelect.val();
            var isSirtfiChecked = sirtfiCheckbox ? sirtfiCheckbox.is(':checked') : false;

            if (edugainValue == '2') {  // ALREADY_IN mode
                // Entity ID is editable and required in ALREADY_IN mode
                entityIdInput.prop('readonly', false);
                entityIdInput.prop('required', true);

                // Hide all fields and remove required attribute
                if (fieldGroupsToHide) fieldGroupsToHide.hide();
                if (fieldsToHide) fieldsToHide.prop('required', false);
            } else {  // Normal mode
                // Entity ID is readonly in normal mode
                entityIdInput.prop('readonly', true);
                entityIdInput.prop('required', false);

                // Show all fields
                if (fieldGroupsToHide) fieldGroupsToHide.show();

                // Set required for fields: step 1, set all to required by default
                if (fieldsToHide) fieldsToHide.prop('required', true);

                // Set required for fields: step 2, set not required fields
                if (fieldsNotRequire) fieldsNotRequire.prop('required', false);

                // Set required for fields: step 3, sirtfi controls security contact fields
                if (sirtfiCheckbox) {
                    if (sirtfiCheckbox.is(':checked')) {
                        if (securityNameField) securityNameField.show();
                        if (securityEmailField) securityEmailField.show();
                        if (securityNameInput) {
                            securityNameInput.prop('required', true);
                            // Fill with defaults only if empty (for create form)
                            if (!securityNameInput.val()) {
                                securityNameInput.val(defaultName);
                            }
                        }
                        if (securityEmailInput) {
                            securityEmailInput.prop('required', true);
                            // Fill with defaults only if empty (for create form)
                            if (!securityEmailInput.val()) {
                                securityEmailInput.val(defaultEmail);
                            }
                        }
                    } else {
                        if (securityNameField) securityNameField.hide();
                        if (securityEmailField) securityEmailField.hide();
                        if (securityNameInput) securityNameInput.prop('required', false);
                        if (securityEmailInput) securityEmailInput.prop('required', false);
                    }
                }

                // Set required for fields: step 4, metadat fields
                if (isEditMode()) {
                    if (metadataFileInput) metadataFileInput.prop('required', false);
                } else {
                    if (metadataFileInput) metadataFileInput.prop('required', true);
                }
            }
        } catch (error) {
            console.error('Error in updateFormFields:', error);
        }
    }

    // Use setTimeout to ensure Flask Admin has fully initialized all form fields
    // Flask Admin dynamically generates form elements, so we need a small delay
    // to ensure all elements exist before trying to interact with them
    setTimeout(function () {
        try {
            updateFormFields();
        } catch (error) {
            console.error('Error during form initialization:', error);
        }
    }, 100);

    // Bind change events with modern jQuery syntax
    if (sirtfiCheckbox) {
        sirtfiCheckbox.on('change', updateFormFields);
    }
    if (edugainSelect) {
        edugainSelect.on('change', updateFormFields);
    }

    /**
     * Entity form submission confirmation
     * Shows warning before submitting Entity form changes
     */
    if (isOnPage('/member/member_idp/') || isOnPage('/member/member_sp/')) {
        $('form[method="POST"]').on('submit', function (e) {
            if (!confirm("⚠️  WARNING: Creating/modifying this entity will trigger automatic re-transformation of this entity and regeneration of federation metadata (beta).\n\nAre you sure you want to save?")) {
                e.preventDefault();
                return false;
            }
            return true;
        });
    }
});