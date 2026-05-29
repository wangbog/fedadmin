from pathlib import Path

from app.extensions import db
from app.models.organization_type import OrganizationType
from tests.conftest import login_client, make_organization, make_sp, make_user


def _write_metadata(storage_root, relative_path, content="<xml/>"):
    path = Path(storage_root) / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_member_can_download_own_entity_metadata(client, app, roles):
    org = make_organization("Member One")
    user = make_user("member-one", org, roles["full_member"])
    _write_metadata(app.config["STORAGE_ROOT"], "private/members/1/sp.xml")
    sp = make_sp(org, "private/members/1/sp.xml")
    db.session.commit()

    login_client(client, user)
    response = client.get(f"/download/sp-metadata/{sp.sp_id}")

    assert response.status_code == 200
    assert response.data == b"<xml/>"


def test_member_cannot_download_other_organization_metadata(client, app, roles):
    own_org = make_organization("Member One")
    other_org = make_organization("Member Two")
    user = make_user("member-one", own_org, roles["full_member"])
    _write_metadata(app.config["STORAGE_ROOT"], "private/members/2/sp.xml")
    sp = make_sp(other_org, "private/members/2/sp.xml")
    db.session.commit()

    login_client(client, user)
    response = client.get(f"/download/sp-metadata/{sp.sp_id}")

    assert response.status_code == 403


def test_federation_admin_can_download_member_metadata(client, app, roles):
    fed_org = make_organization(
        "Federation Admin", OrganizationType.FEDERATION_ADMIN.value
    )
    member_org = make_organization("Member One")
    user = make_user("fed-admin", fed_org, roles["federation"])
    _write_metadata(app.config["STORAGE_ROOT"], "private/members/2/sp.xml")
    sp = make_sp(member_org, "private/members/2/sp.xml")
    db.session.commit()

    login_client(client, user)
    response = client.get(f"/download/sp-metadata/{sp.sp_id}")

    assert response.status_code == 200
    assert response.data == b"<xml/>"


def test_download_rejects_metadata_path_outside_storage(client, roles):
    org = make_organization("Member One")
    user = make_user("member-one", org, roles["full_member"])
    sp = make_sp(org, "../secret.xml")
    db.session.commit()

    login_client(client, user)
    response = client.get(f"/download/sp-metadata/{sp.sp_id}")

    assert response.status_code == 404
