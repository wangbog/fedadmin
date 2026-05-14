import os
import click
import subprocess
from flask import current_app
from flask.cli import with_appcontext
from flask_security.utils import hash_password
from .extensions import db, security
from .models.federation import Federation
from .models.organization import Organization
from .models.organization_type import OrganizationType
from .models.entity_status import EntityStatus
from .models.role import Role
from app.utils.role_helpers import assign_user_roles


@click.command("init-certs")
@with_appcontext
def init_certs_command():
    private_storage = current_app.config.get("PRIVATE_STORAGE")
    if not private_storage:
        private_storage = os.path.join(current_app.root_path, "storage", "private")
    cert_dir = os.path.join(private_storage, "federation")
    key_path = os.path.join(cert_dir, "fed.key")
    cert_path = os.path.join(cert_dir, "fed.crt")

    os.makedirs(cert_dir, exist_ok=True)

    if os.path.exists(key_path) or os.path.exists(cert_path):
        click.confirm("Certificate files already exist. Overwrite?", abort=True)

    fed_name = current_app.config.get("FEDERATION_NAME", "samplefed")
    cmd = [
        "openssl",
        "req",
        "-x509",
        "-newkey",
        "rsa:2048",
        "-keyout",
        key_path,
        "-out",
        cert_path,
        "-days",
        "3650",
        "-nodes",
        "-subj",
        f"/CN=fed-{fed_name}.example.com",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        click.echo("Certificate generated successfully:")
        click.echo(f"  Key: {key_path}")
        click.echo(f"  Cert: {cert_path}")
    except subprocess.CalledProcessError as e:
        click.echo(f"Error generating certificate: {e.stderr}", err=True)
    except FileNotFoundError:
        click.echo(
            "OpenSSL not found. Please install OpenSSL and ensure it's in your PATH.",
            err=True,
        )


@click.command("init-db")
@with_appcontext
def init_db_command():
    """Clear existing data and create new tables."""
    db_path = current_app.config.get("SQLALCHEMY_DATABASE_URI", "").replace(
        "sqlite:///", ""
    )
    if db_path and os.path.exists(db_path):
        click.confirm(
            f"Database file '{db_path}' already exists. Initializing will delete all existing data. Continue?",
            abort=True,
        )

    db.drop_all()
    db.create_all()

    # Insert default roles if table is empty
    if not Role.query.first():
        default_roles = [
            Role(name="federation", description="Federation administrator"),
            Role(
                name="full_member",
                description="Full(Identity Provider + Service Provider) member",
            ),
            Role(name="sp_member", description="Service Provider member"),
        ]

        for role in default_roles:
            db.session.add(role)
        db.session.commit()
        click.echo("Default roles created.")

    # Insert default federation configuration if table is empty
    if not Federation.query.first():
        default_fed = Federation(
            registration_authority="https://example.com",
            registration_policy_url="https://example.com/policy",
            publisher="https://example.com",
        )
        db.session.add(default_fed)
        db.session.commit()
        click.echo("Default federation configuration created.")

    # Create default federation admin organization if not exists
    if not Organization.query.filter_by(
        organization_type=OrganizationType.FEDERATION_ADMIN.value
    ).first():
        # Create federation admin organization
        fed_admin_org = Organization(
            organization_name="Federation Admin Org",
            organization_description="This is the federation admin organization.",
            organization_type=OrganizationType.FEDERATION_ADMIN.value,
            organization_status=EntityStatus.READY.value,
            organization_url="https://example.com",
        )
        db.session.add(fed_admin_org)
        db.session.commit()
        click.echo("Federation admin organization created.")

        # Create federation admin user
        user_datastore = security.datastore
        fed_admin_user = user_datastore.create_user(
            username="fedadmin",
            email="fed@example.com",
            password=hash_password("fedadmin"),
            organization_id=fed_admin_org.organization_id,
            active=True,
        )

        # Assign federation admin roles
        assign_user_roles(fed_admin_user, fed_admin_org)
        db.session.commit()
        click.echo("Federation admin user created (fed@example.com / fedadmin).")

    click.echo("Initialized the database.")


@click.command("createorganization")
@click.option("--name", prompt=True, help="Organization name")
@click.option("--description", default="", help="Organization description")
@click.option(
    "--type",
    "organization_type",
    type=click.Choice(
        ["full_member", "sp_member", "federation_admin"], case_sensitive=False
    ),
    default="full_member",
    help="Organization type: full_member, sp_member, or federation_admin",
)
@click.option("--status", default="ready", help="Organization status (ongoing/ready)")
@click.option("--url", default="", help="Organization URL (e.g., https://example.com)")
@with_appcontext
def create_organization_command(name, description, organization_type, status, url):
    """Create a new organization."""
    if not description:
        description = "A federation member organization."

    # Uniqueness check: only one federation_admin allowed
    if organization_type == "federation_admin":
        existing = Organization.query.filter_by(
            organization_type=OrganizationType.FEDERATION_ADMIN.value
        ).first()
        if existing:
            click.echo(
                "Error: A federation admin organization already exists. Cannot create another."
            )
            return

    type_map = {
        "full_member": OrganizationType.FULL_MEMBER.value,
        "sp_member": OrganizationType.SP_MEMBER.value,
        "federation_admin": OrganizationType.FEDERATION_ADMIN.value,
    }
    type_value = type_map[organization_type]

    status_value = (
        EntityStatus.INIT.value if status == "ongoing" else EntityStatus.READY.value
    )

    # Create organization
    organization = Organization(
        organization_name=name,
        organization_description=description,
        organization_type=type_value,
        organization_status=status_value,
        organization_url=url,
    )
    db.session.add(organization)
    db.session.commit()

    click.echo(
        f"Organization '{name}' created with ID {organization.organization_id} (type: {organization_type})"
    )


@click.command("createuser")
@click.option("--username", prompt=True, help="Username")
@click.option("--email", prompt=True, help="Email")
@click.option(
    "--organization-id",
    type=int,
    prompt=True,
    help="ID of the organization this user belongs to",
)
@click.option(
    "--password", default=None, help="Password (if not provided, defaults to username)"
)
@with_appcontext
def create_user_command(username, email, organization_id, password):
    """Create a new user associated with an organization, using Flask-Security."""
    organization = Organization.query.get(organization_id)
    if not organization:
        click.echo(f"Error: Organization with ID {organization_id} does not exist.")
        return

    if password is None:
        password = username
        click.echo(f"Password not provided, using username as default password.")

    user_datastore = current_app.extensions["security"].datastore

    # Hash password before creating user
    hashed_password = hash_password(password)

    user = user_datastore.create_user(
        username=username,
        email=email,
        password=hashed_password,
        organization_id=organization_id,
        active=True,
    )

    # Assign roles based on organization type
    assign_user_roles(user, organization)

    db.session.commit()
    click.echo(
        f"User '{username}' created, associated with organization "
        f"'{organization.organization_name}' (ID: {organization_id}) with appropriate roles."
    )


def register_commands(app):
    app.cli.add_command(init_certs_command)
    app.cli.add_command(init_db_command)
    app.cli.add_command(create_organization_command)
    app.cli.add_command(create_user_command)
