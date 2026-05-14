from ..extensions import db
from .entity_status import EntityStatus
from .organization_type import OrganizationType


class Organization(db.Model):
    """Organization model"""

    __tablename__ = "organization"

    organization_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    organization_status = db.Column(
        db.Integer, nullable=False, default=EntityStatus.READY.value, index=True
    )
    organization_type = db.Column(
        db.Integer,
        nullable=False,
        default=OrganizationType.FULL_MEMBER.value,
        index=True,
    )
    organization_name = db.Column(db.String(255), nullable=False)
    organization_description = db.Column(db.String(255), nullable=False)
    organization_url = db.Column(db.String(255), nullable=False)

    # Relationships
    sps = db.relationship("Sp", backref="organization", lazy=True)
    idps = db.relationship("Idp", backref="organization", lazy=True)
    users = db.relationship("User", back_populates="organization", lazy=True)

    def __repr__(self):
        return f"<Organization {self.organization_name}>"
