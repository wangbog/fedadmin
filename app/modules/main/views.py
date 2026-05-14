import os
from flask import (
    render_template,
    redirect,
    url_for,
    send_from_directory,
    abort,
    current_app,
    send_file,
    request,
)
from flask_security import auth_required, current_user
from . import main_bp
from app.models import Idp, Sp
from app.utils.logging_helpers import logger, get_client_ip

# Entity type mapping: key used in URL, value is (model class, file field name)
ENTITY_MODELS = {
    "idp-metadata": (Idp, "idp_metadata_file"),
    "sp-metadata": (Sp, "sp_metadata_file"),
}


@main_bp.route("/")
def index():
    return render_template("main/index.html")


@main_bp.before_app_request
def before_request():
    # Log logout events (Flask-Security signal doesn't work correctly)
    if request.path == "/auth/logout" and current_user.is_authenticated:
        client_ip = get_client_ip()
        logger.info(
            f"[{client_ip}] [LOGOUT] - User {current_user.id}({current_user.email}) logged out"
        )


@main_bp.route("/post-login")
@auth_required()
def post_login():
    client_ip = get_client_ip()
    logger.info(
        f"[{client_ip}] [LOGIN] - User {current_user.id}({current_user.email}) logged in successfully"
    )
    if current_user.has_role("federation"):
        return redirect(url_for("federation_admin.index"))
    else:
        return redirect(url_for("member_admin.index"))


@main_bp.route("/storage/<path:filename>")
def public_storage(filename):
    # Prevent path traversal attacks
    if ".." in filename or filename.startswith("/"):
        abort(404)
    # Only allow access to files under the public/ directory
    if not filename.startswith("public/"):
        abort(404)
    storage_root = current_app.config["STORAGE_ROOT"]
    return send_from_directory(storage_root, filename)


@main_bp.route("/download/<entity_type>/<int:entity_id>")
@auth_required()
def download_file(entity_type, entity_id):
    """
    Generic file download endpoint. Only allows access if the current user
    belongs to the same organization as the entity.
    """
    if entity_type not in ENTITY_MODELS:
        abort(404)

    model_cls, file_field = ENTITY_MODELS[entity_type]
    entity = model_cls.query.get_or_404(entity_id)

    # Permission check: federation admin or current user must belong to the same organization
    if not (
        current_user.has_role("federation")
        or current_user.organization_id == entity.organization_id
    ):
        abort(403)

    # Retrieve the file path stored in the database (relative path)
    file_relative = getattr(entity, file_field)
    if not file_relative:
        abort(404)

    # Build the full file path
    storage_root = current_app.config["STORAGE_ROOT"]
    real_storage = os.path.realpath(storage_root)
    abs_path = os.path.realpath(os.path.join(storage_root, file_relative))
    if not abs_path.startswith(real_storage):
        abort(404)
    if not os.path.isfile(abs_path):
        abort(404)

    return send_file(
        abs_path, as_attachment=True, download_name=os.path.basename(abs_path)
    )
