from pathlib import Path
from unittest.mock import patch

from app.extensions import db
from app.models.entity_status import EntityStatus
from tests.conftest import login_client, make_organization, make_sp, make_user


def _csrf_token(client):
    token = "test-csrf-token"
    with client.session_transaction() as session:
        session["csrf_token"] = token
    return token


def _write_pair(storage_root, relative_path):
    original = Path(storage_root) / relative_path
    transformed = Path(str(original).replace(".xml", "-transformed.xml"))
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text("<xml/>", encoding="utf-8")
    transformed.write_text("<xml/>", encoding="utf-8")


def test_member_apply_and_cancel_status_flow(client, app, roles):
    org = make_organization("Member One")
    user = make_user("member-one", org, roles["full_member"])
    sp = make_sp(org, "private/members/1/sp.xml")
    _write_pair(app.config["STORAGE_ROOT"], sp.sp_metadata_file)
    db.session.commit()
    login_client(client, user)
    token = _csrf_token(client)

    with patch("app.utils.security_helpers.validate_csrf_token", return_value=True):
        apply_response = client.post(
            "/member/member_sp/apply/",
            data={"id": sp.sp_id, "csrf_token": token},
        )
    assert apply_response.status_code == 302
    assert db.session.get(type(sp), sp.sp_id).sp_status == EntityStatus.APPROVING.value

    token = _csrf_token(client)
    with patch("app.utils.security_helpers.validate_csrf_token", return_value=True):
        cancel_response = client.post(
            "/member/member_sp/cancel/",
            data={"id": sp.sp_id, "csrf_token": token},
        )
    assert cancel_response.status_code == 302
    assert db.session.get(type(sp), sp.sp_id).sp_status == EntityStatus.INIT.value


def test_federation_approve_rolls_back_when_metadata_regeneration_fails(client, roles):
    fed_org = make_organization("Fed Admin")
    member_org = make_organization("Member One")
    fed_user = make_user("fed-admin", fed_org, roles["federation"])
    sp = make_sp(member_org, "private/members/2/sp.xml", EntityStatus.APPROVING.value)
    db.session.commit()
    login_client(client, fed_user)
    token = _csrf_token(client)

    view = client.application.view_functions["federation_sp.approve"].__self__
    with (
        patch("app.utils.security_helpers.validate_csrf_token", return_value=True),
        patch.object(view, "_regenerate_metadata", side_effect=RuntimeError("boom")),
    ):
        response = client.post(
            "/federation/federation_sp/approve/",
            data={"id": sp.sp_id, "csrf_token": token},
        )

    assert response.status_code == 302
    assert db.session.get(type(sp), sp.sp_id).sp_status == EntityStatus.APPROVING.value


def test_federation_reject_returns_entity_to_init(client, roles):
    fed_org = make_organization("Fed Admin")
    member_org = make_organization("Member One")
    fed_user = make_user("fed-admin", fed_org, roles["federation"])
    sp = make_sp(member_org, "private/members/2/sp.xml", EntityStatus.APPROVING.value)
    db.session.commit()
    login_client(client, fed_user)
    token = _csrf_token(client)

    with patch("app.utils.security_helpers.validate_csrf_token", return_value=True):
        response = client.post(
            "/federation/federation_sp/reject/",
            data={"id": sp.sp_id, "csrf_token": token},
        )

    assert response.status_code == 302
    assert db.session.get(type(sp), sp.sp_id).sp_status == EntityStatus.INIT.value


def test_member_withdraw_rolls_back_when_metadata_regeneration_fails(client, roles):
    org = make_organization("Member One")
    user = make_user("member-one", org, roles["full_member"])
    sp = make_sp(org, "private/members/1/sp.xml", EntityStatus.READY.value)
    db.session.commit()
    login_client(client, user)
    token = _csrf_token(client)

    view = client.application.view_functions["member_sp.withdraw"].__self__
    with (
        patch("app.utils.security_helpers.validate_csrf_token", return_value=True),
        patch.object(view, "_regenerate_metadata", side_effect=RuntimeError("boom")),
    ):
        response = client.post(
            "/member/member_sp/withdraw/",
            data={"id": sp.sp_id, "csrf_token": token},
        )

    assert response.status_code == 302
    assert db.session.get(type(sp), sp.sp_id).sp_status == EntityStatus.READY.value
