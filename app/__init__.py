import os
import pytz
from datetime import datetime
from flask import Flask
from flask_admin.menu import MenuLink
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
from app.utils.logging_helpers import setup_logging, logger
from app.modules.admin.widgets import SwitchRoleLink
from app.models.entity_status import EntityStatus
from app.services.metadata import MetadataService
from config import config
from app.extensions import db, federation_admin, member_admin, security, mail


def create_app(config_name="default"):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    # Initialize logging system early, before other initializations
    setup_logging(app)

    # Validate configuration based on environment
    if config_name == "production":
        from config import validate_production_config

        validate_production_config(app)
    elif config_name == "development":
        from config import validate_development_config

        validate_development_config(app)

    # Initialize extensions
    db.init_app(app)
    mail.init_app(app)

    # Register blueprints
    from app.modules.main import main_bp

    app.register_blueprint(main_bp)

    # Initialize Flask-admin instances
    federation_admin.init_app(app)
    member_admin.init_app(app)

    # Ensure instance directory exists
    os.makedirs(app.instance_path, exist_ok=True)

    # Create storage directories
    storage_root = app.config["STORAGE_ROOT"]
    storage_dirs = [
        os.path.join(storage_root, "public", "members"),
        os.path.join(storage_root, "public", "federation"),
        os.path.join(storage_root, "private", "members"),
        os.path.join(storage_root, "private", "federation"),
    ]
    for dir_path in storage_dirs:
        os.makedirs(dir_path, exist_ok=True)

    with app.app_context():
        # Import models
        from app.models import User, Role, Organization, Sp, Idp, Federation

        # Initialize Flask-Security
        from flask_security import SQLAlchemyUserDatastore

        user_datastore = SQLAlchemyUserDatastore(db, User, Role)
        security.init_app(app, user_datastore)

        # Logout link for both admin interfaces
        logout_link = MenuLink(
            name="Logout",
            endpoint="auth.logout",
            icon_type="fa",
            icon_value="fa-sign-out",
            category="Site",
        )

        # Change password link for both admin interfaces
        change_password_link = MenuLink(
            name="Change Password",
            endpoint="auth.change_password",
            icon_type="fa",
            icon_value="fa-key",
            category="Site",
        )

        # Add Flask-admin views: Federation admin views
        from app.modules.federation import (
            FederationUserModelView,
            FederationOrganizationModelView,
            FederationIdpModelView,
            FederationSpModelView,
            FederationFederationModelView,
        )

        federation_admin.add_view(
            FederationUserModelView(
                User, db.session, name="User", endpoint="federation_user"
            )
        )
        federation_admin.add_view(
            FederationOrganizationModelView(
                Organization,
                db.session,
                name="Organization",
                endpoint="federation_organization",
            )
        )
        federation_admin.add_view(
            FederationFederationModelView(
                Federation, db.session, name="Federation", endpoint="federation_config"
            )
        )
        federation_admin.add_view(
            FederationIdpModelView(
                Idp, db.session, name="IdP", endpoint="federation_idp"
            )
        )
        federation_admin.add_view(
            FederationSpModelView(Sp, db.session, name="SP", endpoint="federation_sp")
        )

        federation_admin.add_category(
            name="Site",
            icon_type="fa",
            icon_value="fa-user",
        )
        federation_admin.add_link(
            SwitchRoleLink("member_admin.index", "Switch to Member Admin", "Site")
        )
        federation_admin.add_link(logout_link)
        federation_admin.add_link(change_password_link)

        # Add Flask-admin views: Member admin views
        from app.modules.member import (
            MemberUserModelView,
            MemberOrganizationModelView,
            MemberIdpModelView,
            MemberSpModelView,
        )

        member_admin.add_view(
            MemberUserModelView(User, db.session, name="User", endpoint="member_user")
        )
        member_admin.add_view(
            MemberOrganizationModelView(
                Organization,
                db.session,
                name="Organization",
                endpoint="member_organization",
            )
        )
        member_admin.add_view(
            MemberIdpModelView(Idp, db.session, name="IdP", endpoint="member_idp")
        )
        member_admin.add_view(
            MemberSpModelView(Sp, db.session, name="SP", endpoint="member_sp")
        )

        member_admin.add_category(
            name="Site",
            icon_type="fa",
            icon_value="fa-user",
        )
        member_admin.add_link(
            SwitchRoleLink(
                "federation_admin.index", "Switch to Federation Admin", "Site"
            )
        )
        member_admin.add_link(logout_link)
        member_admin.add_link(change_password_link)

    # Initialize APScheduler for background tasks
    # Note: In Flask debug mode, Werkzeug reloader spawns a child process.
    # We only want the scheduler to run in the main application process,
    # not in the monitor/parent process, to avoid duplicate job execution.
    # WERKZEUG_RUN_MAIN is set to "true" in the child process.
    if not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        # Configure executors and job stores for serial execution
        executors = {
            "default": ThreadPoolExecutor(
                max_workers=1
            )  # Only 1 worker for serial execution
        }

        jobstores = {"default": MemoryJobStore()}

        # Create scheduler with serial execution configuration
        scheduler = BackgroundScheduler(
            executors=executors,
            jobstores=jobstores,
            job_defaults={
                "coalesce": False,  # Don't merge missed executions
                "max_instances": 1,  # Max 1 instance per job
            },
        )
        scheduler.start()
        app.scheduler = scheduler

        # Parse metadata regeneration time from config (format: "hour:minute")
        regen_time = app.config.get("METADATA_REGENERATION_TIME")
        regen_hour, regen_minute = map(int, regen_time.split(":"))
        misfire_grace_time = app.config.get("METADATA_REGENERATION_MISFIRE_GRACE_TIME")

        # Schedule daily metadata regeneration to update validUntil
        def regenerate_metadata_job():
            """Wrapper to ensure app context is available for scheduled job.

            This job generates all three metadata files:
            - Beta metadata (for entities in INIT/APPROVING status)
            - Main metadata (for entities in READY status)
            - eduGAIN metadata (for READY entities with eduGAIN enabled)
            """
            try:
                with app.app_context():
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
                    logger.info(
                        "Scheduled metadata regeneration job completed successfully"
                    )
            except Exception as e:
                with app.app_context():
                    logger.error(
                        f"Scheduled metadata regeneration job failed: {e}",
                        exc_info=True,
                    )
                raise

        job_id = f"daily_metadata_regeneration_{datetime.now(pytz.UTC).timestamp()}"
        scheduler.add_job(
            regenerate_metadata_job,
            trigger=CronTrigger(hour=regen_hour, minute=regen_minute, timezone="UTC"),
            id=job_id,
            replace_existing=False,
            misfire_grace_time=misfire_grace_time,
        )

        # Schedule eduGAIN metadata updates check
        def check_edugain_updates_job():
            """Wrapper to ensure app context is available for scheduled job.

            This job checks for updates to eduGAIN metadata for ALREADY_IN entities
            using SHA1 comparison and updates local metadata files if changes are found.
            """
            try:
                with app.app_context():
                    logger.info("Starting scheduled eduGAIN metadata updates check job")
                    # Check for eduGAIN updates using SHA1 comparison and get statistics
                    stats = MetadataService.check_edugain_updates(app)

                    # Regenerate federation metadata if any updates were made
                    if stats["updated"] > 0:
                        logger.info(
                            f"eduGAIN updates found ({stats['updated']} entities). Regenerating federation metadata."
                        )
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

                    logger.info(
                        f"Scheduled eduGAIN metadata updates check job completed: {stats}"
                    )
            except Exception as e:
                with app.app_context():
                    logger.error(
                        f"Scheduled eduGAIN metadata updates check job failed: {e}",
                        exc_info=True,
                    )
                raise

        # Get eduGAIN check interval from config
        edugain_check_interval = app.config.get("EDUGAIN_CHECK_INTERVAL", 1)

        edugain_job_id = f"edugain_updates_check_{datetime.now(pytz.UTC).timestamp()}"
        scheduler.add_job(
            check_edugain_updates_job,
            trigger=CronTrigger(hour=f"*/{edugain_check_interval}", timezone="UTC"),
            id=edugain_job_id,
            replace_existing=False,
            misfire_grace_time=misfire_grace_time,
        )

    # Register custom CLI commands
    from app.cli import register_commands

    register_commands(app)

    return app
