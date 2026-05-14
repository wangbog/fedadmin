$(document).ready(function () {
    // Listening to file upload
    $('#sp_metadata_file, #idp_metadata_file').change(function (e) {
        var input = this;
        var file = e.target.files[0];
        if (!file) return;

        var reader = new FileReader();
        reader.onload = function (e) {
            var xml = e.target.result;
            var parser = new DOMParser();
            var xmlDoc = parser.parseFromString(xml, "text/xml");

            // 1. XML validation
            if (xmlDoc.documentElement.nodeName === "parsererror") {
                showError("Invalid XML file.");
                return;
            }

            // 2. Parse entityID
            var entityId = xmlDoc.documentElement.getAttribute("entityID");
            if (entityId) {
                if (input.id === 'sp_metadata_file') {
                    $('#sp_entityid').val(entityId);
                } else if (input.id === 'idp_metadata_file') {
                    $('#idp_entityid').val(entityId);
                }
            } else {
                showError("Cannot find entityID in the metadata.");
                return;
            }

            // 3. Parse scope (IdP only)
            if (input.id === 'idp_metadata_file') {
                var namespaceResolver = function (prefix) {
                    var ns = {
                        'md': 'urn:oasis:names:tc:SAML:2.0:metadata',
                        'shibmd': 'urn:mace:shibboleth:metadata:1.0'
                    };
                    return ns[prefix] || null;
                };

                var xpath = "//md:IDPSSODescriptor/md:Extensions/shibmd:Scope";
                var scopeElem = xmlDoc.evaluate(
                    xpath,
                    xmlDoc,
                    namespaceResolver,
                    XPathResult.FIRST_ORDERED_NODE_TYPE,
                    null
                ).singleNodeValue;

                if (scopeElem) {
                    var scope = scopeElem.textContent;
                    var regexp = scopeElem.getAttribute("regexp");

                    if (regexp && regexp.toLowerCase() !== "false") {
                        showError("Scope regexp must be 'false' (current: " + regexp + "). This metadata will be rejected.");
                        $('#idp_scope').val('');
                    } else {
                        $('#idp_scope').val(scope);
                    }
                } else {
                    showError("No valid shibmd:Scope found in metadata. This metadata will be rejected.");
                    $('#idp_scope').val('');
                }
            }
        };
        reader.readAsText(file, "UTF-8");
    });
});