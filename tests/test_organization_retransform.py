from pathlib import Path
from unittest.mock import patch

from app.extensions import db
from tests.conftest import make_organization, make_sp


def test_member_organization_update_retransforms_member_entities(app, roles):
    org = make_organization("Member One")
    sp = make_sp(org, "private/members/1/sp.xml")
    source = Path(app.config["STORAGE_ROOT"]) / sp.sp_metadata_file
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("<xml/>", encoding="utf-8")
    db.session.commit()

    view = app.view_functions["member_organization.edit_view"].__self__
    with (
        app.test_request_context("/member/member_organization/edit/"),
        patch("app.modules.member.organization.current_user") as current_user,
        patch(
            "app.modules.member.organization.MetadataService.safe_transform"
        ) as transform,
        patch.object(view, "_regenerate_metadata", return_value=True) as regenerate,
    ):
        current_user.id = 1
        current_user.email = "member-one@example.org"
        current_user.organization_id = org.organization_id

        view.after_model_change(None, org, is_created=False)

    transform.assert_called_once_with(
        entity_type="sp",
        entity_id=sp.sp_id,
        original_path=str(source),
        organization_id=org.organization_id,
        raise_on_error=True,
    )
    regenerate.assert_called_once_with(raise_on_error=True)


def test_member_organization_update_skips_regeneration_when_transform_fails(app, roles):
    org = make_organization("Member One")
    sp = make_sp(org, "private/members/1/sp.xml")
    source = Path(app.config["STORAGE_ROOT"]) / sp.sp_metadata_file
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("<xml/>", encoding="utf-8")
    db.session.commit()

    view = app.view_functions["member_organization.edit_view"].__self__
    with (
        app.test_request_context("/member/member_organization/edit/"),
        patch("app.modules.member.organization.current_user") as current_user,
        patch(
            "app.modules.member.organization.MetadataService.safe_transform",
            side_effect=RuntimeError("bad metadata"),
        ),
        patch.object(view, "_regenerate_metadata", return_value=True) as regenerate,
    ):
        current_user.id = 1
        current_user.email = "member-one@example.org"
        current_user.organization_id = org.organization_id

        view.after_model_change(None, org, is_created=False)

    regenerate.assert_not_called()
