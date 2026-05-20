import os
import click
import subprocess
import secrets
import string
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
        password = generate_secure_password()
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


@click.command("regenerate-metadata")
@with_appcontext
def regenerate_metadata_command():
    """Regenerate all federation metadata files.

    This command should be called by system cron for scheduled tasks.
    It uses file locks to prevent concurrent execution.
    """
    from app.services.metadata import MetadataService
    from app.models.entity_status import EntityStatus
    from app.utils.logging_helpers import logger

    try:
        logger.info("Starting scheduled metadata regeneration job")

        # Generate beta metadata (for entities not yet ready)
        MetadataService.safe_regenerate(
            output_path_key="FEDERATION_METADATA_BETA_OUTPUT",
            statuses=[
                EntityStatus.INIT.value,
                EntityStatus.APPROVING.value,
            ],
        )
        # Generate main metadata (for ready entities)
        MetadataService.safe_regenerate(
            output_path_key="FEDERATION_METADATA_OUTPUT",
            statuses=[EntityStatus.READY.value],
        )
        # Generate eduGAIN metadata (for eduGAIN-enabled entities)
        MetadataService.safe_regenerate(
            output_path_key="FEDERATION_METADATA_EDUGAIN_OUTPUT",
            statuses=[EntityStatus.READY.value],
            edugain_only=True,
        )
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
    from app.services.metadata import MetadataService
    from app.utils.logging_helpers import logger

    try:
        logger.info("Starting scheduled eduGAIN metadata updates check job")
        # Check for eduGAIN updates using SHA1 comparison and get statistics
        stats = MetadataService.check_edugain_updates(app)
        # Regenerate federation metadata if any updates were made
        if stats["updated"] > 0:
            logger.info(
                f"eduGAIN updates found ({stats['updated']} entities). Regenerating federation metadata."
            )
            from app.models.entity_status import EntityStatus

            MetadataService.safe_regenerate(
                output_path_key="FEDERATION_METADATA_BETA_OUTPUT",
                statuses=[
                    EntityStatus.INIT.value,
                    EntityStatus.APPROVING.value,
                ],
            )
            MetadataService.safe_regenerate(
                output_path_key="FEDERATION_METADATA_OUTPUT",
                statuses=[EntityStatus.READY.value],
            )
            MetadataService.safe_regenerate(
                output_path_key="FEDERATION_METADATA_EDUGAIN_OUTPUT",
                statuses=[EntityStatus.READY.value],
                edugain_only=True,
            )
        logger.info(f"Scheduled eduGAIN metadata updates check job completed: {stats}")
        click.echo(f"eduGAIN update check completed: {stats}")
    except Exception as e:
        logger.error(
            f"Scheduled eduGAIN metadata updates check job failed: {e}", exc_info=True
        )
        click.echo(f"eduGAIN update check failed: {e}", err=True)
        raise


def generate_secure_password(length=16):
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = "".join(secrets.choice(alphabet) for _ in range(length))
    return password


def register_commands(app):
    app.cli.add_command(init_certs_command)
    app.cli.add_command(init_db_command)
    app.cli.add_command(regenerate_metadata_command)
    app.cli.add_command(check_edugain_updates_command)
