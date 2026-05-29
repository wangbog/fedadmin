from io import BytesIO

from werkzeug.datastructures import FileStorage

from app.services.metadata_validator import MetadataValidator


SP_METADATA = """\
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
  entityID="https://upload-sp.example.org/metadata">
  <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:AssertionConsumerService
      Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
      Location="https://upload-sp.example.org/acs"
      index="0"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>
"""


IDP_METADATA = """\
<md:EntityDescriptor
  xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
  xmlns:shibmd="urn:mace:shibboleth:metadata:1.0"
  entityID="https://upload-idp.example.org/metadata">
  <md:IDPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:Extensions>
      <shibmd:Scope regexp="false">example.org</shibmd:Scope>
    </md:Extensions>
    <md:SingleSignOnService
      Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-Redirect"
      Location="https://upload-idp.example.org/sso"/>
  </md:IDPSSODescriptor>
</md:EntityDescriptor>
"""


def _upload(content):
    return FileStorage(stream=BytesIO(content.encode("utf-8")), filename="metadata.xml")


def test_sp_upload_metadata_validation_extracts_entity_id(clean_db):
    result = MetadataValidator.validate("sp", _upload(SP_METADATA))

    assert result.success
    assert result.entity_id == "https://upload-sp.example.org/metadata"


def test_idp_upload_metadata_validation_extracts_scope(clean_db):
    result = MetadataValidator.validate("idp", _upload(IDP_METADATA))

    assert result.success
    assert result.entity_id == "https://upload-idp.example.org/metadata"
    assert result.scope == "example.org"


def test_upload_rejects_aggregated_entities_descriptor(clean_db):
    content = """\
<md:EntitiesDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata">
  <md:EntityDescriptor entityID="https://sp.example.org/metadata"/>
</md:EntitiesDescriptor>
"""

    result = MetadataValidator.validate("sp", _upload(content))

    assert not result.success
    assert result.errors[0].code == "E003"
