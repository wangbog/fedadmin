import pytest

from app import create_app
from app.extensions import db
from app.models import Organization, Role, Sp, User
from app.models.edugain_status import EdugainStatus
from app.models.entity_status import EntityStatus
from app.models.organization_type import OrganizationType


@pytest.fixture(scope="session")
def app(tmp_path_factory):
    app = create_app("testing")
    storage_root = tmp_path_factory.mktemp("storage")
    app.config.update(STORAGE_ROOT=str(storage_root))
    return app


@pytest.fixture()
def app_ctx(app):
    with app.app_context():
        yield


@pytest.fixture()
def clean_db(app_ctx):
    db.drop_all()
    db.create_all()
    yield
    db.session.remove()
    db.drop_all()


@pytest.fixture()
def client(app, clean_db):
    return app.test_client()


@pytest.fixture()
def roles(clean_db):
    role_map = {}
    for name in ("federation", "full_member", "sp_member"):
        role = Role(name=name)
        db.session.add(role)
        role_map[name] = role
    db.session.commit()
    return role_map


def make_organization(name, organization_type=OrganizationType.FULL_MEMBER.value):
    org = Organization(
        organization_type=organization_type,
        organization_name=name,
        organization_description=f"{name} description",
        organization_url=f"https://{name.lower().replace(' ', '-')}.example.org",
    )
    db.session.add(org)
    db.session.flush()
    return org


def make_user(username, organization, role):
    user = User(
        username=username,
        email=f"{username}@example.org",
        password="unused-in-tests",
        active=True,
        organization_id=organization.organization_id,
        roles=[role],
    )
    db.session.add(user)
    db.session.flush()
    return user


def make_sp(
    organization,
    metadata_file,
    status=EntityStatus.INIT.value,
    entity_id=None,
):
    if entity_id is None:
        safe_suffix = (
            metadata_file.replace("/", "-").replace("\\", "-").replace(".", "-")
        )
        entity_id = f"https://sp{organization.organization_id}.example.org/{safe_suffix}"

    sp = Sp(
        sp_status=status,
        sp_name=f"{organization.organization_name} SP",
        sp_description="Service provider for tests",
        sp_entityid=entity_id,
        sp_metadata_file=metadata_file,
        sp_logo="https://example.org/logo.png",
        sp_edugain=EdugainStatus.YES.value,
        contact_technical_name="Tech Contact",
        contact_technical_email="tech@example.org",
        security_contact_name="Security Contact",
        security_contact_email="security@example.org",
        organization_id=organization.organization_id,
    )
    db.session.add(sp)
    db.session.flush()
    return sp


def login_client(client, user):
    with client.session_transaction() as session:
        session["_user_id"] = user.fs_uniquifier
        session["_fresh"] = True
