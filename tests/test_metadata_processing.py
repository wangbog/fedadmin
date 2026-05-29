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
    assert (
        root.find("md:Organization/md:OrganizationName", ns).text
        == org.organization_name
    )
    assert (
        root.find("md:ContactPerson/md:EmailAddress", ns).text
        == "mailto:tech@example.org"
    )
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


def test_regenerate_metadata_uses_pyff_and_writes_signed_output(app, clean_db):
    org = make_organization("Member One")
    db.session.add(
        Federation(
            registration_authority="https://fed.example.org",
            registration_policy_url="https://fed.example.org/policy",
            publisher="https://fed.example.org/metadata",
        )
    )
    sp = make_sp(org, "private/members/1/sp.xml")
    db.session.commit()

    storage_root = Path(app.config["STORAGE_ROOT"])
    transformed = storage_root / "private/members/1/sp-transformed.xml"
    transformed.parent.mkdir(parents=True, exist_ok=True)
    transformed.write_text(SP_METADATA, encoding="utf-8")

    key_path = storage_root / "private/federation/fed.key"
    cert_path = storage_root / "private/federation/fed.crt"
    output_path = storage_root / "public/federation/fed-metadata.xml"
    key_path.parent.mkdir(parents=True, exist_ok=True)
    for path in (key_path, cert_path):
        path.unlink(missing_ok=True)

    from app.cli import init_certs_command

    app.config["PRIVATE_STORAGE"] = str(storage_root / "private")
    runner = app.test_cli_runner()
    result = runner.invoke(init_certs_command)
    assert result.exit_code == 0, result.output

    app.config.update(
        FEDERATION_SIGNING_KEY=str(key_path),
        FEDERATION_SIGNING_CERT=str(cert_path),
        FEDERATION_METADATA_OUTPUT=str(output_path),
    )

    MetadataService(app)._regenerate("FEDERATION_METADATA_OUTPUT")

    root = etree.parse(str(output_path)).getroot()
    ns = {
        **MetadataService.NAMESPACES,
        "ds": "http://www.w3.org/2000/09/xmldsig#",
    }
    assert root.tag == f"{{{MetadataService.NAMESPACES['md']}}}EntitiesDescriptor"
    assert root.find("ds:Signature", ns) is not None
    assert root.find("md:EntityDescriptor", ns).get("entityID") == (
        "https://sp.example.org/metadata"
    )
