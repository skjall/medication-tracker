"""
Routes for hospital visit management.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

from models import db, HospitalVisit, Order, OrderItem, Medication

visit_bp = Blueprint("visits", __name__, url_prefix="/visits")


@visit_bp.route("/")
def index():
    """Display list of all hospital visits."""
    # Get upcoming visits
    upcoming_visits = (
        HospitalVisit.query.filter(
            HospitalVisit.visit_date >= datetime.now(timezone.utc)
        )
        .order_by(HospitalVisit.visit_date)
        .all()
    )

    # Get past visits
    past_visits = (
        HospitalVisit.query.filter(
            HospitalVisit.visit_date < datetime.now(timezone.utc)
        )
        .order_by(HospitalVisit.visit_date.desc())
        .limit(10)
        .all()
    )

    return render_template(
        "visits/index.html", upcoming_visits=upcoming_visits, past_visits=past_visits
    )


@visit_bp.route("/new", methods=["GET", "POST"])
def new():
    """Create a new hospital visit."""
    if request.method == "POST":
        # Extract form data
        visit_date_str = request.form.get("visit_date", "")
        notes = request.form.get("notes", "")

        try:
            # Parse date from form
            visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d")
            # Make the datetime timezone-aware
            visit_date = visit_date.replace(tzinfo=timezone.utc)

            # Create new visit
            visit = HospitalVisit(visit_date=visit_date, notes=notes)

            db.session.add(visit)
            db.session.commit()

            flash(f"Hospital visit scheduled for {visit_date_str}", "success")

            # Check if we should create an order automatically
            create_order = request.form.get("create_order", "no")
            if create_order == "yes":
                return redirect(url_for("orders.new", visit_id=visit.id))
            else:
                return redirect(url_for("visits.show", id=visit.id))

        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD format.", "error")

    return render_template("visits/new.html")


@visit_bp.route("/<int:id>", methods=["GET"])
def show(id: int):
    """Display details for a specific hospital visit."""
    visit = HospitalVisit.query.get_or_404(id)

    # Get orders for this visit
    orders = Order.query.filter_by(hospital_visit_id=visit.id).all()

    # Get all medications for medication needs calculation
    medications = Medication.query.all()
    medication_needs = {}

    for med in medications:
        if med.inventory:
            needed = med.calculate_needed_until_visit(visit.visit_date)
            current = med.inventory.current_count
            additional = max(0, needed - current)
            packages = med.calculate_packages_needed(additional)

            medication_needs[med.id] = {
                "medication": med,
                "needed_units": needed,
                "current_inventory": current,
                "additional_needed": additional,
                "packages": packages,
            }

    return render_template(
        "visits/show.html",
        visit=visit,
        orders=orders,
        medication_needs=medication_needs,
    )


@visit_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id: int):
    """Edit an existing hospital visit."""
    visit = HospitalVisit.query.get_or_404(id)

    if request.method == "POST":
        # Extract form data
        visit_date_str = request.form.get("visit_date", "")
        notes = request.form.get("notes", "")

        try:
            # Parse date from form
            visit_date = datetime.strptime(visit_date_str, "%Y-%m-%d")
            # Make the datetime timezone-aware
            visit_date = visit_date.replace(tzinfo=timezone.utc)

            # Update visit
            visit.visit_date = visit_date
            visit.notes = notes

            db.session.commit()

            flash(f"Hospital visit updated to {visit_date_str}", "success")
            return redirect(url_for("visits.show", id=visit.id))

        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD format.", "error")

    # Format date for the form
    formatted_date = visit.visit_date.strftime("%Y-%m-%d")

    return render_template(
        "visits/edit.html", visit=visit, formatted_date=formatted_date
    )


@visit_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """Delete a hospital visit."""
    visit = HospitalVisit.query.get_or_404(id)

    # Check if there are orders associated with this visit
    orders = Order.query.filter_by(hospital_visit_id=visit.id).all()
    if orders:
        flash(
            "Cannot delete visit with associated orders. Delete the orders first.",
            "error",
        )
        return redirect(url_for("visits.show", id=visit.id))

    db.session.delete(visit)
    db.session.commit()

    flash("Hospital visit deleted successfully", "success")
    return redirect(url_for("visits.index"))


@visit_bp.route("/next")
def next_visit():
    """Display details about the next upcoming hospital visit."""
    next_visit = (
        HospitalVisit.query.filter(
            HospitalVisit.visit_date >= datetime.now(timezone.utc)
        )
        .order_by(HospitalVisit.visit_date)
        .first()
    )

    if not next_visit:
        flash("No upcoming hospital visits scheduled", "warning")
        return redirect(url_for("visits.new"))

    return redirect(url_for("visits.show", id=next_visit.id))
