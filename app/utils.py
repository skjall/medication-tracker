"""
Utility functions for the Medication Tracker application.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, TypeVar
import os
import csv
from io import StringIO

from flask import current_app, Response
from models import Medication, Inventory, HospitalVisit, Order, OrderItem

# Generic type for min_value function
T = TypeVar("T")


def min_value(a: T, b: T) -> T:
    """
    Return the minimum of two values.

    Args:
        a: First value
        b: Second value

    Returns:
        The minimum value
    """
    return min(a, b)


def format_date(date: datetime) -> str:
    """
    Format a datetime object for display.

    Args:
        date: The datetime object to format

    Returns:
        Formatted date string
    """
    return date.strftime("%Y-%m-%d")


def format_datetime(date: datetime) -> str:
    """
    Format a datetime object with time for display.

    Args:
        date: The datetime object to format

    Returns:
        Formatted datetime string
    """
    return date.strftime("%Y-%m-%d %H:%M")


def calculate_days_until(target_date: datetime) -> int:
    """
    Calculate days until a target date.

    Args:
        target_date: The target date

    Returns:
        Number of days until the target date (0 if in the past)
    """
    delta = target_date - datetime.utcnow()
    return max(0, delta.days)


def get_color_for_inventory_level(medication: Medication) -> str:
    """
    Get a color code based on inventory level.

    Args:
        medication: The medication to check

    Returns:
        CSS color class (text-danger, text-warning, text-success)
    """
    if not medication.inventory:
        return "text-danger"

    if medication.inventory.is_low:
        return "text-danger"

    # If we have less than 30 days supply
    if medication.days_remaining and medication.days_remaining < 30:
        return "text-warning"

    return "text-success"


def export_medications_to_csv() -> Response:
    """
    Export all medications to a CSV file.

    Returns:
        Flask Response object with CSV data
    """
    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(
        [
            "ID",
            "Name",
            "Dosage",
            "Frequency",
            "Daily Usage",
            "Package Size N1",
            "Package Size N2",
            "Package Size N3",
            "Min Threshold",
            "Safety Margin Days",
            "Current Inventory",
            "Days Remaining",
            "Created At",
            "Updated At",
        ]
    )

    # Write data
    medications = Medication.query.all()
    for med in medications:
        writer.writerow(
            [
                med.id,
                med.name,
                med.dosage,
                med.frequency,
                med.daily_usage,
                med.package_size_n1,
                med.package_size_n2,
                med.package_size_n3,
                med.min_threshold,
                med.safety_margin_days,
                med.inventory.current_count if med.inventory else 0,
                round(med.days_remaining, 1) if med.days_remaining else "N/A",
                format_datetime(med.created_at),
                format_datetime(med.updated_at),
            ]
        )

    output = si.getvalue()

    # Create response
    response = Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=medications.csv"},
    )

    return response


def export_inventory_to_csv() -> Response:
    """
    Export current inventory to a CSV file.

    Returns:
        Flask Response object with CSV data
    """
    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(
        [
            "Medication ID",
            "Medication Name",
            "Current Count",
            "Packages N1",
            "Packages N2",
            "Packages N3",
            "Days Remaining",
            "Depletion Date",
            "Last Updated",
        ]
    )

    # Write data
    inventories = Inventory.query.all()
    for inv in inventories:
        depletion_date = inv.medication.depletion_date
        writer.writerow(
            [
                inv.medication_id,
                inv.medication.name,
                inv.current_count,
                inv.packages_n1,
                inv.packages_n2,
                inv.packages_n3,
                (
                    round(inv.medication.days_remaining, 1)
                    if inv.medication.days_remaining
                    else "N/A"
                ),
                format_date(depletion_date) if depletion_date else "N/A",
                format_datetime(inv.last_updated),
            ]
        )

    output = si.getvalue()

    # Create response
    response = Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=inventory.csv"},
    )

    return response


def export_orders_to_csv() -> Response:
    """
    Export all orders to a CSV file.

    Returns:
        Flask Response object with CSV data
    """
    si = StringIO()
    writer = csv.writer(si)

    # Write header
    writer.writerow(
        [
            "Order ID",
            "Visit Date",
            "Status",
            "Created Date",
            "Medication",
            "Quantity Needed",
            "Packages N1",
            "Packages N2",
            "Packages N3",
        ]
    )

    # Write data
    orders = Order.query.all()
    for order in orders:
        for item in order.order_items:
            writer.writerow(
                [
                    order.id,
                    format_date(order.hospital_visit.visit_date),
                    order.status,
                    format_datetime(order.created_date),
                    item.medication.name,
                    item.quantity_needed,
                    item.packages_n1,
                    item.packages_n2,
                    item.packages_n3,
                ]
            )

    output = si.getvalue()

    # Create response
    response = Response(
        output,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=orders.csv"},
    )

    return response
