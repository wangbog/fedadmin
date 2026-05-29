import pytest

from config import TestingConfig, validate_production_config


def test_testing_config_uses_isolated_defaults():
    assert TestingConfig.TESTING is True
    assert TestingConfig.SQLALCHEMY_DATABASE_URI == "sqlite://"
    assert TestingConfig.SECRET_KEY
    assert TestingConfig.SECURITY_PASSWORD_SALT
    assert TestingConfig.MAIL_SUPPRESS_SEND is True


def test_production_config_validation_reports_missing_required_values():
    class DummyApp:
        config = {
            "FEDERATION_NAME": "samplefed",
            "SECRET_KEY": None,
            "SECURITY_PASSWORD_SALT": None,
            "MAIL_SERVER": "smtp.example.org",
            "MAIL_USERNAME": None,
            "MAIL_PASSWORD": None,
        }

    with pytest.raises(ValueError) as exc_info:
        validate_production_config(DummyApp())

    message = str(exc_info.value)
    assert "SECRET_KEY" in message
    assert "SECURITY_PASSWORD_SALT" in message
    assert "MAIL_USERNAME" in message
    assert "MAIL_PASSWORD" in message
