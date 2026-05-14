from ..extensions import db
from .entity_status import EntityStatus
from .edugain_status import EdugainStatus


class Idp(db.Model):
    """Identity Provider model"""

    __tablename__ = "idp"

    entity_type = "idp"

    idp_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idp_status = db.Column(
        db.Integer, nullable=False, default=EntityStatus.INIT.value, index=True
    )
    idp_name = db.Column(db.String(255), nullable=False)
    idp_description = db.Column(db.String(255), nullable=False)
    idp_scope = db.Column(db.String(255), nullable=False)
    idp_entityid = db.Column(db.String(255), nullable=False, unique=True)
    idp_metadata_file = db.Column(db.String(255), nullable=False)
    idp_logo = db.Column(db.String(255), nullable=False)
    idp_edugain = db.Column(db.Integer, nullable=False, default=EdugainStatus.YES.value)
    idp_metadata_sha1 = db.Column(
        db.String(40), nullable=True
    )  # SHA1 hash of eduGAIN metadata

    contact_technical_name = db.Column(db.String(255), nullable=False)
    contact_technical_email = db.Column(db.String(255), nullable=False)
    security_contact_name = db.Column(db.String(255), nullable=False)
    security_contact_email = db.Column(db.String(255), nullable=False)

    # REFEDS entity category support
    sirtfi_enabled = db.Column(db.Boolean, default=False, nullable=False)
    rs_enabled = db.Column(db.Boolean, default=False, nullable=False)

    organization_id = db.Column(
        db.Integer, db.ForeignKey("organization.organization_id"), nullable=False
    )

    def __repr__(self):
        return f"<Idp {self.idp_name}>"
