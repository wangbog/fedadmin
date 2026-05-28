import os
from flask import Flask
from flask_admin.menu import MenuLink
from app.utils.logging_helpers import setup_logging
from app.models import User, Role, Organization, Sp, Idp, Federation, EmailDelivery
from app.modules.admin.widgets import CurrentUserLink, SwitchRoleLink
from config import config
from app.extensions import db, migrate, federation_admin, member_admin, security, mail


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
    migrate.init_app(app, db)
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
            FederationEmailDeliveryModelView,
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
        federation_admin.add_view(
            FederationEmailDeliveryModelView(
                EmailDelivery,
                db.session,
                name="Email Delivery",
                endpoint="federation_email_delivery",
                category="System",
            )
        )

        federation_admin.add_category(
            name="Site",
            icon_type="fa",
            icon_value="fa-user",
        )
        federation_admin.add_link(CurrentUserLink("Site"))
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
        member_admin.add_link(CurrentUserLink("Site"))
        member_admin.add_link(
            SwitchRoleLink(
                "federation_admin.index", "Switch to Federation Admin", "Site"
            )
        )
        member_admin.add_link(logout_link)
        member_admin.add_link(change_password_link)

    # Register custom CLI commands
    from app.cli import register_commands

    register_commands(app)

    return app
