"""Federation module for Flask-Admin views."""

from .base import FederationBaseView
from .user import FederationUserModelView
from .organization import FederationOrganizationModelView
from .federation import FederationFederationModelView
from .idp import FederationIdpModelView
from .sp import FederationSpModelView

__all__ = [
    "FederationBaseView",
    "FederationUserModelView",
    "FederationOrganizationModelView",
    "FederationFederationModelView",
    "FederationIdpModelView",
    "FederationSpModelView",
]
