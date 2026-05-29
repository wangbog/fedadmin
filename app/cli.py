import os
import click
import subprocess
import secrets
import string
from flask import current_app
from flask.cli import with_appcontext
from flask_security.utils import hash_password
from .extensions import db, security
from app.services.metadata import MetadataService
from .models.federation import Federation
from .models.organization import Organization
from .models.organization_type import OrganizationType
from .models.entity_status import EntityStatus
from .models.role import Role
from app.utils.role_helpers import assign_user_roles
from app.utils.logging_helpers import logger


@click.command("init-certs")
@with_appcontext
def init_certs_command():
    """Generate self-signed certificate for federation metadata signing."""

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
    """Insert default roles, federation configuration, and admin data if they don't exist."""

    actions_taken = []

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
        actions_taken.append(
            "Created default roles (federation, full_member, sp_member)"
        )
    else:
        actions_taken.append("Default roles already exist")

    # Insert default federation configuration if table is empty
    if not Federation.query.first():
        default_fed = Federation(
            registration_authority="https://example.com",
            registration_policy_url="https://example.com/policy",
            publisher="https://example.com",
        )
        db.session.add(default_fed)
        db.session.commit()
        actions_taken.append("Created default federation configuration")
    else:
        actions_taken.append("Federation configuration already exists")

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
        actions_taken.append("Created Federation Admin Organization")

        # Create federation admin user
        password = _generate_secure_password()
        user_datastore = security.datastore
        fed_admin_user = user_datastore.create_user(
            username="fedadmin",
            email="fed@example.com",
            password=hash_password(password),
            organization_id=fed_admin_org.organization_id,
            active=True,
        )

        # Assign federation admin roles
        assign_user_roles(fed_admin_user, fed_admin_org)
        db.session.commit()
        actions_taken.append(
            "Created federation admin user (fed@example.com / fedadmin) with randomly generated password"
        )

        # Store the password for display
        generated_password = password
    else:
        actions_taken.append("Federation Admin Organization and user already exist")

    # Display summary of actions
    click.echo("\n=== Database Initialization Summary ===")
    for action in actions_taken:
        click.echo(f"- {action}")

    if any("already exist" in action for action in actions_taken):
        click.echo("\nNote: Some data already existed and was not modified.")
    else:
        # Display generated password with warning
        click.echo("\n=== FEDERATION ADMIN USER CREDENTIALS ===")
        click.echo("Username: fedadmin")
        click.echo("Email: fed@example.com")
        click.echo(f"Password: {generated_password}")
        click.echo("\n⚠️  IMPORTANT: Please save this password immediately!")
        click.echo(
            "   This is your federation admin password. It will NOT be displayed again."
        )
        click.echo("   If you lose this password, you will need to reset it manually.")

    click.echo("\nDatabase initialization completed.")


@click.command("ensure-metadata")
@with_appcontext
def ensure_metadata_command():
    """Generate missing federation metadata files without overwriting existing files."""

    generated = []
    existing = []
    failed = []

    _ensure_metadata_output_dirs()

    for label, output_path_key, statuses, edugain_only in _metadata_targets():
        output_path = current_app.config[output_path_key]
        if os.path.exists(output_path):
            existing.append((label, output_path))
            continue

        click.echo(f"Generating missing {label}: {output_path}")
        result = MetadataService.safe_regenerate(
            output_path_key=output_path_key,
            statuses=statuses,
            edugain_only=edugain_only,
        )

        if result and os.path.exists(output_path):
            generated.append((label, output_path))
        else:
            failed.append((label, output_path))

    for label, output_path in existing:
        click.echo(f"Exists: {label} ({output_path})")
    for label, output_path in generated:
        click.echo(f"Generated: {label} ({output_path})")

    if failed:
        for label, output_path in failed:
            click.echo(f"Failed: {label} ({output_path})", err=True)
        raise click.ClickException(
            "Some metadata files could not be generated. Check logs and signing certificate configuration."
        )

    click.echo("Federation metadata files are present.")


@click.command("regenerate-metadata")
@with_appcontext
def regenerate_metadata_command():
    """Regenerate all federation metadata files.

    This command should be called by system cron for scheduled tasks.
    It uses file locks to prevent concurrent execution.
    """

    try:
        logger.info("Starting scheduled metadata regeneration job")
        _regenerate_all_metadata()
        logger.info("Scheduled metadata regeneration job completed successfully")
        click.echo("Metadata regeneration completed successfully!")
    except Exception as e:
        logger.error(f"Scheduled metadata regeneration job failed: {e}", exc_info=True)
        click.echo(f"Metadata regeneration failed: {e}", err=True)
        raise


@click.command("check-edugain-updates")
@with_appcontext
def check_edugain_updates_command():
    """Check for eduGAIN metadata updates.

    This command should be called by system cron for scheduled tasks.
    It uses file locks to prevent concurrent execution.
    """

    try:
        logger.info("Starting scheduled eduGAIN metadata updates check job")
        # Check for eduGAIN updates using SHA1 comparison and get statistics
        stats = MetadataService.check_edugain_updates(current_app)
        # Regenerate federation metadata if any updates were made
        if stats["updated"] > 0:
            logger.info(
                f"eduGAIN updates found ({stats['updated']} entities). Regenerating federation metadata."
            )
            _regenerate_all_metadata()
        logger.info(f"Scheduled eduGAIN metadata updates check job completed: {stats}")
        click.echo(f"eduGAIN update check completed: {stats}")
    except Exception as e:
        logger.error(
            f"Scheduled eduGAIN metadata updates check job failed: {e}", exc_info=True
        )
        click.echo(f"eduGAIN update check failed: {e}", err=True)
        raise


def register_commands(app):
    app.cli.add_command(init_certs_command)
    app.cli.add_command(init_db_command)
    app.cli.add_command(ensure_metadata_command)
    app.cli.add_command(regenerate_metadata_command)
    app.cli.add_command(check_edugain_updates_command)


def _metadata_targets():
    """Return metadata generation targets in dashboard order."""
    return [
        (
            "Production metadata",
            "FEDERATION_METADATA_OUTPUT",
            [EntityStatus.READY.value],
            False,
        ),
        (
            "eduGAIN metadata",
            "FEDERATION_METADATA_EDUGAIN_OUTPUT",
            [EntityStatus.READY.value],
            True,
        ),
        (
            "Beta metadata",
            "FEDERATION_METADATA_BETA_OUTPUT",
            [EntityStatus.INIT.value, EntityStatus.APPROVING.value],
            False,
        ),
    ]


def _ensure_metadata_output_dirs():
    """Create directories that hold generated federation metadata files."""
    for _, output_path_key, _, _ in _metadata_targets():
        output_dir = os.path.dirname(current_app.config[output_path_key])
        os.makedirs(output_dir, exist_ok=True)


def _regenerate_all_metadata():
    """Helper function to regenerate all three federation metadata files.

    This function generates:
    - fed-metadata-beta.xml: For INIT and APPROVING status entities
    - fed-metadata.xml: For READY status entities
    - fed-metadata-edugain.xml: For READY status entities with eduGAIN participation enabled
    """

    logger.info("Regenerating all federation metadata files")

    _ensure_metadata_output_dirs()

    for label, output_path_key, statuses, edugain_only in _metadata_targets():
        logger.info("Regenerating %s", label)
        MetadataService.safe_regenerate(
            output_path_key=output_path_key,
            statuses=statuses,
            edugain_only=edugain_only,
            raise_on_error=True,
        )

    logger.info("All federation metadata files regenerated successfully")


def _generate_secure_password(length=16):
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password
