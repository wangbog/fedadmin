from ..extensions import db
from .entity_status import EntityStatus
from .edugain_status import EdugainStatus


class Sp(db.Model):
    """Service Provider model"""

    __tablename__ = "sp"

    entity_type = "sp"

    sp_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sp_status = db.Column(
        db.Integer, nullable=False, default=EntityStatus.INIT.value, index=True
    )
    sp_name = db.Column(db.String(255), nullable=False)
    sp_description = db.Column(db.String(255), nullable=False)
    sp_entityid = db.Column(db.String(255), nullable=False, unique=True)
    sp_metadata_file = db.Column(db.String(255), nullable=False)
    sp_logo = db.Column(db.String(255), nullable=False)
    sp_edugain = db.Column(db.Integer, nullable=False, default=EdugainStatus.YES.value)
    sp_metadata_sha1 = db.Column(
        db.String(40), nullable=True
    )  # SHA1 hash of eduGAIN metadata

    contact_technical_name = db.Column(db.String(255), nullable=False)
    contact_technical_email = db.Column(db.String(255), nullable=False)
    security_contact_name = db.Column(db.String(255), nullable=False)
    security_contact_email = db.Column(db.String(255), nullable=False)

    # REFEDS entity category support
    sirtfi_enabled = db.Column(db.Boolean, default=False, nullable=False)
    rs_enabled = db.Column(db.Boolean, default=False, nullable=False)
    coco_enabled = db.Column(db.Boolean, default=False, nullable=False)

    # Information/Privacy Statement URL for SP
    information_url = db.Column(db.String(255), nullable=False, default="")
    privacy_statement_url = db.Column(db.String(255), nullable=False, default="")

    organization_id = db.Column(
        db.Integer, db.ForeignKey("organization.organization_id"), nullable=False
    )

    def __repr__(self):
        return f"<Sp {self.sp_name}>"
