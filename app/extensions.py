from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_security import Security
from flask_admin import Admin
from flask_admin.theme import Bootstrap4Theme
from flask_mail import Mail

db = SQLAlchemy()
migrate = Migrate()
security = Security()
mail = Mail()

from app.modules.federation.index import FederationAdminIndexView
from app.modules.member.index import MemberAdminIndexView

federation_admin = Admin(
    name="Federation Admin",
    theme=Bootstrap4Theme(),
    url="/federation",
    endpoint="federation_admin",
    index_view=FederationAdminIndexView(
        name="Home",
        endpoint="federation_admin",
        url="/federation",
    ),
)
member_admin = Admin(
    name="Member Admin",
    theme=Bootstrap4Theme(),
    url="/member",
    endpoint="member_admin",
    index_view=MemberAdminIndexView(
        name="Home",
        endpoint="member_admin",
        url="/member",
    ),
)
