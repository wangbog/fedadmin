import uuid
from flask_security import UserMixin as SecurityUserMixin
from ..extensions import db
from .role import user_roles


class User(db.Model, SecurityUserMixin):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    active = db.Column(db.Boolean(), default=True)
    confirmed_at = db.Column(db.DateTime)
    fs_uniquifier = db.Column(
        db.String(64), unique=True, nullable=False, default=lambda: uuid.uuid4().hex
    )
    organization_id = db.Column(
        db.Integer, db.ForeignKey("organization.organization_id"), nullable=False
    )

    roles = db.relationship("Role", secondary=user_roles, backref="users")
    organization = db.relationship("Organization", back_populates="users")

    def __repr__(self):
        return f"<User {self.username}>"
