from pathlib import Path

from lxml import etree

from app.extensions import db
from app.models import Federation
from app.models.edugain_status import EdugainStatus
from app.services.metadata import MetadataService
from tests.conftest import make_organization, make_sp


SP_METADATA = """\
<md:EntityDescriptor
    xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
    entityID="https://sp.example.org/metadata"
    validUntil="2030-01-01T00:00:00Z">
  <!-- removed by transformation -->
  <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:AssertionConsumerService
      Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
      Location="https://sp.example.org/acs"
      index="0"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>
"""


def test_transform_entity_adds_federation_metadata_smoke(app, clean_db):
    org = make_organization("Member One")
    db.session.add(
        Federation(
            registration_authority="https://fed.example.org",
            registration_policy_url="https://fed.example.org/policy",
            publisher="https://fed.example.org/metadata",
        )
    )
    sp = make_sp(org, "private/members/1/sp.xml")
    sp.coco_enabled = True
    sp.rs_enabled = True
    sp.sirtfi_enabled = True
    db.session.commit()

    source = Path(app.config["STORAGE_ROOT"]) / sp.sp_metadata_file
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text(SP_METADATA, encoding="utf-8")

    transformed = MetadataService(app)._transform_entity(
        "sp", sp.sp_id, str(source), org.organization_id
    )

    root = etree.parse(transformed).getroot()
    ns = MetadataService.NAMESPACES
    assert "validUntil" not in root.attrib
    assert root.find("md:Extensions/mdrpi:RegistrationInfo", ns) is not None
    assert root.find(".//mdui:DisplayName", ns).text == sp.sp_name
    assert root.find("md:Organization/md:OrganizationName", ns).text == org.organization_name
    assert root.find("md:ContactPerson/md:EmailAddress", ns).text == "mailto:tech@example.org"
    assert root.find(".//mdattr:EntityAttributes", ns) is not None


def test_collect_source_files_skips_edugain_disabled_entities(app, clean_db):
    org = make_organization("Member One")
    included = make_sp(org, "private/members/1/included.xml")
    excluded = make_sp(
        org,
        "private/members/1/excluded.xml",
        entity_id="https://excluded.example.org/metadata",
    )
    excluded.sp_edugain = EdugainStatus.NO.value
    db.session.commit()

    storage_root = Path(app.config["STORAGE_ROOT"])
    for entity in (included, excluded):
        transformed = storage_root / entity.sp_metadata_file.replace(
            ".xml", "-transformed.xml"
        )
        transformed.parent.mkdir(parents=True, exist_ok=True)
        transformed.write_text("<xml/>", encoding="utf-8")

    sources = MetadataService(app)._collect_source_files(edugain_only=True)

    assert sources == [
        (
            str(storage_root / "private/members/1/included-transformed.xml"),
            "sp",
        )
    ]
