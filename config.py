import os
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # ---- Storage paths ----
    STORAGE_ROOT = os.path.join(basedir, "app", "storage")
    PUBLIC_STORAGE = os.path.join(STORAGE_ROOT, "public")
    PRIVATE_STORAGE = os.path.join(STORAGE_ROOT, "private")

    # ---- Logging settings ----
    LOG_FILE = os.environ.get(
        "LOG_FILE"
    )  # Log file path (optional, logs to console if not set)
    LOG_LEVEL = os.environ.get(
        "LOG_LEVEL", "INFO"
    )  # Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL

    # ---- Federation settings ----
    FEDERATION_NAME = os.environ.get("FEDERATION_NAME", "samplefed")
    FEDERATION_PUBLIC_FILES_URL = os.environ.get("FEDERATION_PUBLIC_FILES_URL")

    # ---- Federation metadata regeneration settings ----
    # Time to run daily metadata regeneration (UTC). Format: "hour:minute" (e.g., "2:00")
    METADATA_REGENERATION_TIME = os.environ.get("METADATA_REGENERATION_TIME", "2:00")
    # Grace time (in seconds) for async metadata regeneration tasks before they are skipped
    METADATA_REGENERATION_MISFIRE_GRACE_TIME = int(
        os.environ.get("METADATA_REGENERATION_MISFIRE_GRACE_TIME", "60")
    )
    # Time interval for checking eduGAIN updates (hours)
    EDUGAIN_CHECK_INTERVAL = int(os.environ.get("EDUGAIN_CHECK_INTERVAL", "1"))
    FEDERATION_METADATA_BETA_OUTPUT = os.path.join(
        PUBLIC_STORAGE, "federation", "fed-metadata-beta.xml"
    )
    FEDERATION_METADATA_OUTPUT = os.path.join(
        PUBLIC_STORAGE, "federation", "fed-metadata.xml"
    )
    FEDERATION_METADATA_EDUGAIN_OUTPUT = os.path.join(
        PUBLIC_STORAGE, "federation", "fed-metadata-edugain.xml"
    )
    FEDERATION_SIGNING_KEY = os.path.join(PRIVATE_STORAGE, "federation", "fed.key")
    FEDERATION_SIGNING_CERT = os.path.join(PRIVATE_STORAGE, "federation", "fed.crt")

    # ---- General Flask settings ----
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024

    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access
    SESSION_COOKIE_SAMESITE = "Lax"  # CSRF protection

    # Mail server settings (will be overridden by environment variables)
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.your-domain.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "587"))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() in ("true", "1", "t")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", os.environ.get("MAIL_USERNAME")
    )
    # Debug settings for mail
    MAIL_SUPPRESS_SEND = os.environ.get("MAIL_SUPPRESS_SEND", "False").lower() in (
        "true",
        "1",
        "t",
    )

    # ---- Flask-Security settings ----
    SECURITY_PASSWORD_SINGLE = False  # Allow repeated characters in passwords
    SECURITY_PASSWORD_LENGTH_MIN = 8  # Minimum password length
    SECURITY_PASSWORD_COMPLEXITY = True  # Require special characters

    # Email notifications for password changes and resets
    SECURITY_SEND_PASSWORD_CHANGE_EMAIL = os.environ.get(
        "SECURITY_SEND_PASSWORD_CHANGE_EMAIL", "False"
    ).lower() in ("true", "1", "t")
    SECURITY_SEND_PASSWORD_RESET_EMAIL = os.environ.get(
        "SECURITY_SEND_PASSWORD_RESET_EMAIL", "False"
    ).lower() in ("true", "1", "t")

    SECURITY_REGISTERABLE = False
    SECURITY_CONFIRMABLE = False
    SECURITY_RECOVERABLE = True
    SECURITY_CHANGEABLE = True
    SECURITY_TWO_FACTOR = False
    SECURITY_TWO_FACTOR_ENABLED_METHODS = ["authenticator"]
    SECURITY_BLUEPRINT_NAME = "auth"
    SECURITY_URL_PREFIX = "/auth"
    SECURITY_LOGIN_URL = "/login"
    SECURITY_LOGOUT_URL = "/logout"
    SECURITY_REGISTER_URL = "/register"
    SECURITY_RESET_URL = "/reset"
    SECURITY_CONFIRM_URL = "/confirm"
    SECURITY_POST_LOGIN_VIEW = "main.post_login"


class DevelopmentConfig(Config):
    DEBUG = True

    # ---- Security settings (development allows default values) ----
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    SECURITY_PASSWORD_SALT = os.environ.get(
        "SECURITY_PASSWORD_SALT", "dev-password-salt"
    )

    # ---- Database ----
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        basedir, "instance", "fedadmin-dev.db"
    )

    # ---- Session settings ----
    SESSION_COOKIE_SECURE = False
    PERMANENT_SESSION_LIFETIME = 3600 * 24  # 24 hours timeout


class ProductionConfig(Config):
    # ---- Security settings (production reads from environment variables) ----
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT")

    # ---- Database ----
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        basedir, "instance", "fedadmin-prod.db"
    )

    # ---- Session settings ----
    SESSION_COOKIE_SECURE = True
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes timeout


def validate_development_config(app):
    """Validate required development configuration items"""
    required_vars = {
        "FEDERATION_NAME": app.config.get("FEDERATION_NAME"),
        "FEDERATION_PUBLIC_FILES_URL": app.config.get("FEDERATION_PUBLIC_FILES_URL"),
    }
    missing = [key for key, value in required_vars.items() if not value]
    if missing:
        raise ValueError(
            f"Missing required development environment variables: {', '.join(missing)}"
        )


def validate_production_config(app):
    """Validate required production configuration items"""
    required_vars = {
        "SECRET_KEY": app.config.get("SECRET_KEY"),
        "SECURITY_PASSWORD_SALT": app.config.get("SECURITY_PASSWORD_SALT"),
        "FEDERATION_NAME": app.config.get("FEDERATION_NAME"),
        "FEDERATION_PUBLIC_FILES_URL": app.config.get("FEDERATION_PUBLIC_FILES_URL"),
        "MAIL_SERVER": app.config.get("MAIL_SERVER"),
        "MAIL_USERNAME": app.config.get("MAIL_USERNAME"),
        "MAIL_PASSWORD": app.config.get("MAIL_PASSWORD"),
    }
    missing = [key for key, value in required_vars.items() if not value]
    if missing:
        raise ValueError(
            f"Missing required production environment variables: {', '.join(missing)}"
        )


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
