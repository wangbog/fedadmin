"""Federation module for Flask-Admin views."""

__all__ = [
    "FederationBaseView",
    "FederationAdminIndexView",
    "FederationUserModelView",
    "FederationOrganizationModelView",
    "FederationFederationModelView",
    "FederationIdpModelView",
    "FederationSpModelView",
]


def __getattr__(name):
    if name == "FederationBaseView":
        from .base import FederationBaseView

        return FederationBaseView
    if name == "FederationAdminIndexView":
        from .index import FederationAdminIndexView

        return FederationAdminIndexView
    if name == "FederationUserModelView":
        from .user import FederationUserModelView

        return FederationUserModelView
    if name == "FederationOrganizationModelView":
        from .organization import FederationOrganizationModelView

        return FederationOrganizationModelView
    if name == "FederationFederationModelView":
        from .federation import FederationFederationModelView

        return FederationFederationModelView
    if name == "FederationIdpModelView":
        from .idp import FederationIdpModelView

        return FederationIdpModelView
    if name == "FederationSpModelView":
        from .sp import FederationSpModelView

        return FederationSpModelView
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
