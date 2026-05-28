from datetime import datetime, timezone

from ..extensions import db


class EmailDelivery(db.Model):
    __tablename__ = "email_delivery"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    recipient = db.Column(db.String(255), nullable=False, index=True)
    subject = db.Column(db.String(255), nullable=False)
    template = db.Column(db.String(80), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, index=True)
    error_message = db.Column(db.Text, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        index=True,
        default=lambda: datetime.now(timezone.utc),
    )
    sent_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref=db.backref("email_deliveries", lazy=True))

    def __repr__(self):
        return f"<EmailDelivery {self.template} {self.status} to {self.recipient}>"
