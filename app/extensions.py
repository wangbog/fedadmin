from flask_sqlalchemy import SQLAlchemy
from flask_security import Security
from flask_admin import Admin
from flask_admin.theme import Bootstrap4Theme
from flask_mail import Mail

db = SQLAlchemy()
security = Security()
mail = Mail()

federation_admin = Admin(
    name="Federation Admin",
    theme=Bootstrap4Theme(),
    url="/federation",
    endpoint="federation_admin",
)
member_admin = Admin(
    name="Member Admin",
    theme=Bootstrap4Theme(),
    url="/member",
    endpoint="member_admin",
)
