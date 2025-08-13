"""
Routes for physician management.
"""

# Standard library imports
import logging
from datetime import datetime, timezone

# Third-party imports
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_babel import gettext as _

# Local application imports
from models import (
    Physician,
    db,
)
from utils import to_local_timezone

# Create a logger for this module
logger = logging.getLogger(__name__)

# Create a blueprint for physician routes
physician_bp = Blueprint("physicians", __name__, url_prefix="/physicians")


@physician_bp.route("/")
def index():
    """Display list of all physicians."""
    physicians = Physician.query.all()
    return render_template(
        "physicians/index.html",
        local_time=to_local_timezone(datetime.now(timezone.utc)),
        physicians=physicians,
    )


@physician_bp.route("/new", methods=["GET", "POST"])
def new():
    """Create a new physician."""
    if request.method == "POST":
        # Extract form data
        name = request.form.get("name", "").strip()
        specialty = request.form.get("specialty", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        notes = request.form.get("notes", "").strip()

        # Validate required fields
        if not name:
            flash(_("Physician name is required."), "error")
            return render_template("physicians/new.html")

        try:
            # Create new physician
            physician = Physician(
                name=name,
                specialty=specialty if specialty else None,
                phone=phone if phone else None,
                email=email if email else None,
                address=address if address else None,
                notes=notes if notes else None,
            )

            db.session.add(physician)
            db.session.commit()

            flash(_("Physician '{}' has been created successfully.").format(name), "success")
            logger.info(f"Created new physician: {name}")

            return redirect(url_for("physicians.index"))

        except Exception as e:
            db.session.rollback()
            flash(_("Error creating physician: {}").format(str(e)), "error")
            logger.error(f"Error creating physician: {str(e)}")

    return render_template("physicians/new.html")


@physician_bp.route("/<int:physician_id>")
def show(physician_id):
    """Show physician details."""
    physician = Physician.query.get_or_404(physician_id)

    return render_template(
        "physicians/show.html",
        physician=physician,
        local_time=to_local_timezone(datetime.now(timezone.utc)),
    )


@physician_bp.route("/<int:physician_id>/edit", methods=["GET", "POST"])
def edit(physician_id):
    """Edit a physician."""
    physician = Physician.query.get_or_404(physician_id)

    if request.method == "POST":
        # Extract form data
        name = request.form.get("name", "").strip()
        specialty = request.form.get("specialty", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()
        address = request.form.get("address", "").strip()
        notes = request.form.get("notes", "").strip()

        # Validate required fields
        if not name:
            flash(_("Physician name is required."), "error")
            return render_template("physicians/edit.html", physician=physician)

        try:
            # Update physician
            physician.name = name
            physician.specialty = specialty if specialty else None
            physician.phone = phone if phone else None
            physician.email = email if email else None
            physician.address = address if address else None
            physician.notes = notes if notes else None

            db.session.commit()

            flash(_("Physician '{}' has been updated successfully.").format(name), "success")
            logger.info(f"Updated physician: {name}")

            return redirect(url_for("physicians.show", physician_id=physician.id))

        except Exception as e:
            db.session.rollback()
            flash(_("Error updating physician: {}").format(str(e)), "error")
            logger.error(f"Error updating physician: {str(e)}")

    return render_template("physicians/edit.html", physician=physician)


@physician_bp.route("/<int:physician_id>/delete", methods=["POST"])
def delete(physician_id):
    """Delete a physician."""
    physician = Physician.query.get_or_404(physician_id)

    try:
        # Check if physician has associated medications or visits
        if physician.medications or physician.visits:
            flash(
                _("Cannot delete physician who has associated medications or visits. Please reassign them first."),
                "error"
            )
            return redirect(url_for("physicians.show", physician_id=physician.id))

        physician_name = physician.name
        db.session.delete(physician)
        db.session.commit()

        flash(_("Physician '{}' has been deleted successfully.").format(physician_name), "success")
        logger.info(f"Deleted physician: {physician_name}")

        return redirect(url_for("physicians.index"))

    except Exception as e:
        db.session.rollback()
        flash(_("Error deleting physician: {}").format(str(e)), "error")
        logger.error(f"Error deleting physician: {str(e)}")
        return redirect(url_for("physicians.show", physician_id=physician.id))
