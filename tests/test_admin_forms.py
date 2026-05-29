from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.extensions import db
from app.models import Sp
from app.models.edugain_status import EdugainStatus
from app.models.entity_status import EntityStatus
from tests.conftest import login_client, make_organization, make_user


SP_METADATA = """\
<md:EntityDescriptor xmlns:md="urn:oasis:names:tc:SAML:2.0:metadata"
  entityID="https://form-sp.example.org/metadata">
  <md:SPSSODescriptor protocolSupportEnumeration="urn:oasis:names:tc:SAML:2.0:protocol">
    <md:AssertionConsumerService
      Binding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
      Location="https://form-sp.example.org/acs"
      index="0"/>
  </md:SPSSODescriptor>
</md:EntityDescriptor>
"""


def _metadata_upload():
    return (BytesIO(SP_METADATA.encode("utf-8")), "metadata.xml")


def test_member_sp_create_form_persists_entity_and_prepares_metadata(
    client, app, roles
):
    org = make_organization("Member One")
    user = make_user("member-one", org, roles["full_member"])
    view = app.view_functions["member_sp.create_view"].__self__

    with (
        app.test_request_context(
            "/member/member_sp/new/",
            method="POST",
            data={
                "sp_name": "Form SP",
                "sp_edugain": str(EdugainStatus.YES.value),
                "sp_description": "Created through Flask-Admin form",
                "sp_entityid": "",
                "sp_logo": "https://example.org/logo.png",
                "sp_metadata_file": _metadata_upload(),
                "contact_technical_name": "Tech Contact",
                "contact_technical_email": "tech@example.org",
                "security_contact_name": "",
                "security_contact_email": "",
                "information_url": "https://example.org/info",
                "privacy_statement_url": "https://example.org/privacy",
            },
            content_type="multipart/form-data",
        ),
        patch("app.modules.member.base.current_user") as base_current_user,
        patch("app.modules.member.sp.current_user") as current_user,
        patch("app.modules.member.sp.validate_xml"),
        patch.object(
            view, "_regenerate_metadata_beta", return_value=True
        ) as regenerate,
    ):
        for patched_user in (base_current_user, current_user):
            patched_user.id = user.id
            patched_user.email = user.email
            patched_user.username = user.username
            patched_user.organization_id = org.organization_id
        form = view.create_form()

        created = view.create_model(form)

    sp = Sp.query.filter_by(sp_entityid="https://form-sp.example.org/metadata").one()
    assert created.sp_id == sp.sp_id
    assert sp.organization_id == org.organization_id
    assert sp.sp_name == "Form SP"
    assert sp.sp_metadata_file.endswith("metadata.xml")
    regenerate.assert_called_once_with(raise_on_error=True)


def test_member_sp_edit_hook_rejects_non_init_entity(app, roles):
    org = make_organization("Member One")
    user = make_user("member-one", org, roles["full_member"])
    sp = Sp(
        sp_status=EntityStatus.READY.value,
        sp_name="Ready SP",
        sp_description="Ready entity",
        sp_entityid="https://ready-sp.example.org/metadata",
        sp_metadata_file="private/members/1/ready.xml",
        sp_logo="https://example.org/logo.png",
        sp_edugain=EdugainStatus.YES.value,
        contact_technical_name="Tech Contact",
        contact_technical_email="tech@example.org",
        security_contact_name="",
        security_contact_email="",
        organization_id=org.organization_id,
    )

    db.session.add(sp)
    db.session.commit()
    view = app.view_functions["member_sp.edit_view"].__self__

    with (
        app.test_request_context(f"/member/member_sp/edit/?id={sp.sp_id}"),
        patch("app.modules.member.sp.current_user") as current_user,
    ):
        current_user.id = user.id
        current_user.email = user.email
        current_user.organization_id = org.organization_id

        with pytest.raises(ValueError, match="Only INIT entities can be edited"):
            view.on_model_change(
                SimpleNamespace(sp_metadata_file=SimpleNamespace(data=None)), sp, False
            )

    assert db.session.get(Sp, sp.sp_id).sp_name == "Ready SP"
