from ..extensions import db


class Federation(db.Model):
    """Federation-wide configuration (single row)"""

    __tablename__ = "federation"
    id = db.Column(db.Integer, primary_key=True)
    registration_authority = db.Column(
        db.String(255), nullable=False, default="https://www.example.com"
    )
    registration_policy_url = db.Column(
        db.String(255), nullable=False, default="https://example.com/policy"
    )
    publisher = db.Column(
        db.String(255), nullable=False, default="https://www.example.com"
    )
