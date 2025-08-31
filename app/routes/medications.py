"""
Routes for medication management - NOW REDIRECTS TO INGREDIENTS SYSTEM.
All medication routes redirect to the new ingredients/products structure.
"""

# Standard library imports
import logging
from datetime import datetime, timezone

# Third-party imports
from flask import (
    Blueprint,
    flash,
    redirect,
    url_for,
)
from flask_babel import gettext as _

# Local application imports
from models import Medication, db

# Create a logger for this module
logger = logging.getLogger(__name__)

# Create a blueprint for medication routes
medication_bp = Blueprint("medications", __name__, url_prefix="/medications")


@medication_bp.route("/")
def index():
    """Redirect to new ingredients/products view."""
    return redirect(url_for('ingredients.index'))


@medication_bp.route("/new", methods=["GET", "POST"])
def new():
    """Redirect to new ingredients view."""
    return redirect(url_for('ingredients.index'))


@medication_bp.route("/<int:id>", methods=["GET"])
def show(id: int):
    """Redirect medication view to ingredient or product."""
    medication = Medication.query.get_or_404(id)
    
    # Try to find the linked active ingredient through migrated product
    from models import MedicationProduct
    product = MedicationProduct.query.filter_by(legacy_medication_id=id).first()
    
    if product and product.active_ingredient_id:
        # Redirect to active ingredient view
        return redirect(url_for('ingredients.show', id=product.active_ingredient_id))
    elif product:
        # Redirect to product view
        return redirect(url_for('ingredients.show_product', id=product.id))
    else:
        # No migration exists, redirect to ingredients index with message
        flash(_("This medication needs to be migrated to the new system"), "info")
        return redirect(url_for('ingredients.index'))


@medication_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id: int):
    """Redirect medication edit to ingredient or product."""
    medication = Medication.query.get_or_404(id)
    
    # Try to find the linked active ingredient through migrated product
    from models import MedicationProduct
    product = MedicationProduct.query.filter_by(legacy_medication_id=id).first()
    
    if product and product.active_ingredient_id:
        # Redirect to active ingredient edit
        return redirect(url_for('ingredients.edit', id=product.active_ingredient_id))
    elif product:
        # Redirect to product edit
        return redirect(url_for('ingredients.edit_product', id=product.id))
    else:
        # No migration exists, redirect to ingredients index with message
        flash(_("This medication needs to be migrated to the new system"), "info")
        return redirect(url_for('ingredients.index'))


@medication_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """Redirect medication delete - medications should be migrated first."""
    flash(_("Please migrate this medication to the new system before deleting"), "warning")
    return redirect(url_for('ingredients.index'))


@medication_bp.route("/<int:id>/inventory")
def inventory(id: int):
    """Redirect to inventory view."""
    medication = Medication.query.get_or_404(id)
    if medication.inventory:
        return redirect(url_for('inventory.show', id=medication.inventory.id))
    else:
        flash(_("No inventory found for this medication"), "warning")
        return redirect(url_for('inventory.index'))


# API endpoints for AJAX requests
@medication_bp.route("/<int:id>/package_sizes", methods=["GET"])
def get_package_sizes(id: int):
    """API endpoint to get package sizes - redirect to product API."""
    from models import MedicationProduct
    from flask import jsonify
    
    product = MedicationProduct.query.filter_by(legacy_medication_id=id).first()
    
    if product:
        # Return package information from product
        packages = []
        for pkg in product.packages:
            packages.append({
                'size': pkg.package_size,
                'quantity': pkg.quantity
            })
        return jsonify({'packages': packages})
    else:
        # Return legacy package sizes
        medication = Medication.query.get_or_404(id)
        return jsonify({
            'packages': [
                {'size': 'N1', 'quantity': medication.package_size_n1 or 0},
                {'size': 'N2', 'quantity': medication.package_size_n2 or 0},
                {'size': 'N3', 'quantity': medication.package_size_n3 or 0}
            ]
        })