"""
Scanner routes for barcode/QR code medication package tracking.
"""

from datetime import datetime
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
)
from flask_babel import gettext as _

from models import (
    db,
    MedicationPackage,
    ProductPackage,
    ScannedItem,
    PackageInventory,
)
from scanner_parser import (
    parse_datamatrix,
    parse_expiry_date,
    format_national_number_display,
    validate_gtin,
)
from barcode_validator import identify_barcode_format, validate_de_pzn

bp = Blueprint("scanner", __name__, url_prefix="/scanner")


@bp.route("/")
def index():
    """Redirect directly to scanner."""
    return redirect(url_for("scanner.scan"))


@bp.route("/scan", methods=["GET", "POST"])
def scan():
    """Handle barcode scanning."""
    if request.method == "GET":
        return render_template("scanner/scan.html")

    # Process scanned data
    data = request.json
    barcode_data = data.get("barcode")

    if not barcode_data:
        return jsonify({"error": _("No barcode data provided")}), 400

    # Clean up barcode data - remove leading minus sign (standard for Code 39 PZN barcodes)
    # All German PZN barcodes are printed with "-" prefix in Code 39 format
    barcode_data = str(barcode_data).lstrip("-")

    # Try to identify standalone barcode format (PZN, CIP, CNK, etc.)
    barcode_info = identify_barcode_format(barcode_data)

    if barcode_info:
        # This is a recognized standalone pharmaceutical barcode
        national_number, number_type = barcode_info
        parsed = {
            "gtin": None,
            "serial": f"{number_type}_{national_number}_{datetime.now().timestamp()}",  # Generate unique serial
            "expiry": None,
            "batch": None,
            "national_number": national_number,
            "national_number_type": number_type,
        }
    else:
        # Parse as DataMatrix or other GS1 format
        parsed = parse_datamatrix(barcode_data)

        # If DataMatrix parsing also failed, create minimal structure for unknown barcode
        if not parsed.get("serial"):
            parsed = {
                "gtin": None,
                "serial": f"UNKNOWN_{barcode_data[:20]}_{datetime.now().timestamp()}",
                "expiry": None,
                "batch": None,
                "national_number": None,
                "national_number_type": None,
            }

    if not parsed.get("serial"):
        return (
            jsonify({"error": _("Invalid barcode: missing serial number")}),
            400,
        )

    # Check if this package is already in active inventory
    existing_scanned = ScannedItem.query.filter_by(
        serial_number=parsed["serial"]
    ).first()
    if existing_scanned:
        # Check if it's in active inventory
        active_inventory = (
            PackageInventory.query.filter_by(
                scanned_item_id=existing_scanned.id
            )
            .filter(PackageInventory.status.in_(["sealed", "open"]))
            .first()
        )

        if active_inventory:
            # Package is already in active inventory - reject
            medication_name = _("Unknown")
            if active_inventory.medication:
                medication_name = active_inventory.medication.name

            return (
                jsonify(
                    {
                        "error": _("Package already in inventory"),
                        "details": {
                            "scanned_at": existing_scanned.scanned_at.isoformat(),
                            "medication": medication_name,
                            "status": active_inventory.status,
                            "units_remaining": f"{active_inventory.current_units}/{active_inventory.original_units}",
                        },
                    }
                ),
                409,
            )

        # Package was scanned before but not in active inventory - allow re-use
        # Update the existing scanned item with new data if available
        if parsed.get("batch"):
            existing_scanned.batch_number = parsed["batch"]
        if parsed.get("expiry"):
            expiry_date = parse_expiry_date(parsed["expiry"])
            if expiry_date:
                existing_scanned.expiry_date = expiry_date.date()
        existing_scanned.status = "active"
        existing_scanned.scanned_at = datetime.utcnow()
        db.session.flush()

    # Find package - check both new ProductPackage and old MedicationPackage tables
    # Try GTIN first, then national number
    package = None
    product_package = None

    # First check new ProductPackage table
    if parsed.get("gtin"):
        product_package = ProductPackage.query.filter_by(
            gtin=parsed["gtin"]
        ).first()

    if not product_package and parsed.get("national_number"):
        # Try with exact type if we know it
        if parsed.get("national_number_type"):
            product_package = ProductPackage.query.filter_by(
                national_number=parsed["national_number"],
                national_number_type=parsed["national_number_type"],
            ).first()

        # If still not found, try just the number
        if not product_package:
            product_package = ProductPackage.query.filter_by(
                national_number=parsed["national_number"]
            ).first()

    # If found in new system, handle it properly
    if product_package:
        # Update ProductPackage with missing information from scan
        updated = False
        if not product_package.gtin and parsed.get("gtin"):
            product_package.gtin = parsed["gtin"]
            updated = True

        # Update national number if it was found by GTIN but missing national number
        if not product_package.national_number and parsed.get(
            "national_number"
        ):
            product_package.national_number = parsed["national_number"]
            product_package.national_number_type = parsed.get(
                "national_number_type"
            )
            updated = True

        if updated:
            db.session.flush()
            flash(_("Package configuration updated with scanned data"), "info")

        # Check if this product is linked to a legacy medication for inventory
        # If the product has a legacy_medication_id, we can add it to inventory
        if product_package.product.legacy_medication_id:
            # Use existing scanned item or create new one
            if existing_scanned:
                scanned_item = existing_scanned
            else:
                # Create new scanned item
                expiry_date = None
                if parsed.get("expiry"):
                    expiry_date = parse_expiry_date(parsed["expiry"])
                    if expiry_date:
                        expiry_date = expiry_date.date()

                is_gs1 = bool(parsed.get("batch") or parsed.get("expiry"))

                scanned_item = ScannedItem(
                    medication_package_id=None,  # Not linked to old MedicationPackage
                    gtin=parsed.get("gtin"),
                    national_number=parsed.get("national_number"),
                    national_number_type=parsed.get("national_number_type"),
                    serial_number=parsed["serial"],
                    batch_number=parsed.get("batch"),
                    expiry_date=expiry_date,
                    is_gs1=is_gs1,
                    raw_data=barcode_data,
                    status="active",
                )
                db.session.add(scanned_item)
                db.session.flush()

            # Find pending order item for this medication
            from models import Order, OrderItem

            pending_order_item = None
            fulfillment_message = None

            # Look for the oldest pending or partial order with this medication that still needs units
            pending_order_item = (
                OrderItem.query.join(Order)
                .filter(
                    OrderItem.medication_id
                    == product_package.product.legacy_medication_id,
                    OrderItem.fulfillment_status.in_(["pending", "partial"]),
                    OrderItem.units_received < OrderItem.quantity_needed,
                    Order.status.in_(["planned", "printed"]),
                )
                .order_by(Order.created_date.asc())
                .first()
            )

            # Update order fulfillment if order found
            if pending_order_item:
                units_still_needed = (
                    pending_order_item.quantity_needed
                    - pending_order_item.units_received
                )
                pending_order_item.units_received += product_package.quantity

                # Check if this fulfills or overfills the order
                if (
                    pending_order_item.units_received
                    >= pending_order_item.quantity_needed
                ):
                    pending_order_item.fulfillment_status = "fulfilled"
                    pending_order_item.fulfilled_at = datetime.utcnow()
                    if (
                        pending_order_item.units_received
                        > pending_order_item.quantity_needed
                    ):
                        overage = (
                            pending_order_item.units_received
                            - pending_order_item.quantity_needed
                        )
                        fulfillment_message = _(
                            "Order fulfilled with %(overage)d extra units",
                            overage=overage,
                        )
                        pending_order_item.fulfillment_notes = f"Order fulfilled. Received {product_package.quantity} units in {product_package.package_size}. {overage} extra units."
                    else:
                        fulfillment_message = _("Order fulfilled exactly")
                else:
                    pending_order_item.fulfillment_status = "partial"
                    remaining = (
                        pending_order_item.quantity_needed
                        - pending_order_item.units_received
                    )
                    fulfillment_message = _(
                        "Partial fulfillment: %(remaining)d units still needed",
                        remaining=remaining,
                    )
                    pending_order_item.fulfillment_notes = f"Partially fulfilled. Received {product_package.quantity} units in {product_package.package_size}. Still need {remaining} units."

                # Update the order status
                pending_order_item.order.update_status_from_items()

            # Create PackageInventory entry linked to the legacy medication
            inventory_item = PackageInventory(
                medication_id=product_package.product.legacy_medication_id,
                scanned_item_id=scanned_item.id,
                current_units=product_package.quantity,
                original_units=product_package.quantity,
                status="sealed",
                order_item_id=(
                    pending_order_item.id if pending_order_item else None
                ),
            )
            db.session.add(inventory_item)

            # Update inventory log
            from models import Inventory, InventoryLog

            inventory = Inventory.query.filter_by(
                medication_id=product_package.product.legacy_medication_id
            ).first()

            if inventory:
                # Get current total before adding this package
                medication = product_package.product.legacy_medication
                old_total = (
                    medication.total_inventory_count - product_package.quantity
                )

                # Create log entry
                log_entry = InventoryLog(
                    inventory_id=inventory.id,
                    previous_count=old_total,
                    adjustment=product_package.quantity,
                    new_count=medication.total_inventory_count,
                    notes=f"Package scanned: {product_package.package_size} ({product_package.quantity} units) - Batch: {parsed.get('batch', 'N/A')}",
                )
                db.session.add(log_entry)

            db.session.commit()

            # Build response message
            message = f"Added to inventory: {product_package.product.display_name} {product_package.package_size} ({product_package.quantity} units)"
            if fulfillment_message:
                message += f". {fulfillment_message}"

            # Return success with inventory added
            response_data = {
                "success": True,
                "product_package": True,
                "inventory_added": True,
                "package_info": {
                    "id": product_package.id,
                    "product_name": product_package.product.display_name,
                    "package_size": product_package.package_size,
                    "quantity": product_package.quantity,
                    "manufacturer": product_package.manufacturer
                    or product_package.product.manufacturer,
                },
                "parsed_data": {
                    "serial": parsed["serial"],
                    "batch": parsed.get("batch"),
                    "expiry": expiry_date.isoformat() if expiry_date else None,
                    "national_number": parsed.get("national_number"),
                    "national_number_type": parsed.get("national_number_type"),
                    "gtin": parsed.get("gtin"),
                },
                "message": message,
            }

            # Add order fulfillment info if applicable
            if pending_order_item:
                response_data["order_fulfillment"] = {
                    "order_id": pending_order_item.order_id,
                    "units_received": pending_order_item.units_received,
                    "units_needed": pending_order_item.quantity_needed,
                    "status": pending_order_item.fulfillment_status,
                    "progress": pending_order_item.fulfillment_progress,
                }

            return jsonify(response_data)
        else:
            # Product not linked to legacy system - can't add to inventory yet
            return (
                jsonify(
                    {
                        "error": _(
                            "Product found but not linked to inventory system"
                        ),
                        "hint": _(
                            "This product needs to be linked to a medication record for inventory tracking"
                        ),
                        "product_info": {
                            "name": product_package.product.display_name,
                            "package_size": product_package.package_size,
                            "quantity": product_package.quantity,
                        },
                    }
                ),
                400,
            )

    # Continue with old MedicationPackage handling if not found in new system

    # If not found in new system, check old MedicationPackage table
    if not product_package and not package:
        if parsed.get("gtin"):
            package = MedicationPackage.query.filter_by(
                gtin=parsed["gtin"]
            ).first()

        if not package and parsed.get("national_number"):
            if parsed.get("national_number_type"):
                package = MedicationPackage.query.filter_by(
                    national_number=parsed["national_number"],
                    national_number_type=parsed["national_number_type"],
                ).first()

            if not package:
                package = MedicationPackage.query.filter_by(
                    national_number=parsed["national_number"]
                ).first()

    # If package found, update missing information
    if package:
        updated = False
        # If package has no GTIN but we scanned one, add it
        if not package.gtin and parsed.get("gtin"):
            package.gtin = parsed["gtin"]
            updated = True

        # If package has no national number but we extracted one, add it
        if not package.national_number and parsed.get("national_number"):
            package.national_number = parsed["national_number"]
            package.national_number_type = parsed["national_number_type"]
            package.country_code = (
                parsed.get("national_number_type", "").split("_")[0]
                if parsed.get("national_number_type")
                else None
            )
            updated = True

        if updated:
            db.session.flush()
            flash(_("Package information updated with scanned data"), "info")

    # If no package found (but maybe found ProductPackage), return appropriate message
    if not package and not product_package:
        # Create user-friendly error message based on what we recognized
        if parsed.get("national_number") and parsed.get(
            "national_number_type"
        ):
            # We have a recognized pharmaceutical code
            type_labels = {
                "DE_PZN": "PZN",
                "FR_CIP13": "CIP13",
                "FR_CIP7": "CIP7",
                "BE_CNK": "CNK",
                "NL_ZINDEX": "Z-Index",
                "ES_CN": "CN",
                "IT_AIC": "AIC",
            }
            label = type_labels.get(
                parsed["national_number_type"], parsed["national_number_type"]
            )
            error_msg = (
                f"{label} {parsed['national_number']} not found in database"
            )
            hint = _("Please add this medication first, then scan again")
        else:
            # Unknown barcode format
            error_msg = _("Unrecognized barcode format")
            hint = _("This barcode type is not supported")

        # Build onboarding URL with scanned data
        onboarding_params = {
            "gtin": parsed.get("gtin"),
            "national_number": parsed.get("national_number"),
            "national_number_type": parsed.get("national_number_type"),
            "batch": parsed.get("batch"),
            "expiry": (
                parse_expiry_date(parsed["expiry"]).isoformat()
                if parsed.get("expiry")
                else None
            ),
            "serial": parsed.get("serial"),
        }

        # Build query string
        from urllib.parse import urlencode

        query_string = urlencode(
            {k: v for k, v in onboarding_params.items() if v}
        )
        onboarding_url = (
            url_for("package_onboarding.onboard_package", _external=False)
            + "?"
            + query_string
        )

        return (
            jsonify(
                {
                    "error": error_msg,
                    "hint": hint,
                    "details": {
                        "national_number": parsed.get("national_number"),
                        "national_number_type": parsed.get(
                            "national_number_type"
                        ),
                        "gtin": parsed.get("gtin"),
                        "batch": parsed.get("batch"),
                        "expiry": (
                            parse_expiry_date(parsed["expiry"]).isoformat()
                            if parsed.get("expiry")
                            else None
                        ),
                    },
                    "onboarding_url": onboarding_url,
                    "action_required": "onboard_package",
                }
            ),
            404,
        )

    # Use existing scanned item or create new one
    if existing_scanned:
        scanned_item = existing_scanned
        # Update package link if found
        if package:
            scanned_item.medication_package_id = package.id
    else:
        # Create new scanned item only if package is known
        expiry_date = None
        if parsed.get("expiry"):
            expiry_date = parse_expiry_date(parsed["expiry"])
            if expiry_date:
                expiry_date = expiry_date.date()

        # Determine if this is a GS1 scan (has batch or expiry data)
        is_gs1 = bool(parsed.get("batch") or parsed.get("expiry"))

        scanned_item = ScannedItem(
            medication_package_id=package.id if package else None,
            gtin=parsed.get("gtin"),
            national_number=parsed.get("national_number"),
            national_number_type=parsed.get("national_number_type"),
            serial_number=parsed["serial"],
            batch_number=parsed.get("batch"),
            expiry_date=expiry_date,
            is_gs1=is_gs1,
            raw_data=barcode_data,
            status="active",
        )
        db.session.add(scanned_item)
        db.session.flush()

    # Add to inventory if package is identified
    if package and package.medication:
        # Determine package size
        quantity = package.quantity
        if not quantity:
            # Try to determine from package size
            med = package.medication
            if package.package_size == "N1":
                quantity = med.package_size_n1
            elif package.package_size == "N2":
                quantity = med.package_size_n2
            elif package.package_size == "N3":
                quantity = med.package_size_n3

        if quantity:
            # Find pending order item for this medication
            from models import Order, OrderItem

            pending_order_item = None
            fulfillment_message = None

            # Look for the oldest pending or partial order with this medication that still needs units
            pending_order_item = (
                OrderItem.query.join(Order)
                .filter(
                    OrderItem.medication_id == package.medication_id,
                    OrderItem.fulfillment_status.in_(["pending", "partial"]),
                    OrderItem.units_received < OrderItem.quantity_needed,
                    Order.status.in_(["planned", "printed"]),
                )
                .order_by(Order.created_date.asc())
                .first()
            )

            # Update order fulfillment if order found
            if pending_order_item:
                units_still_needed = (
                    pending_order_item.quantity_needed
                    - pending_order_item.units_received
                )
                pending_order_item.units_received += quantity

                # Check if this fulfills or overfills the order
                if (
                    pending_order_item.units_received
                    >= pending_order_item.quantity_needed
                ):
                    pending_order_item.fulfillment_status = "fulfilled"
                    pending_order_item.fulfilled_at = datetime.utcnow()
                    if (
                        pending_order_item.units_received
                        > pending_order_item.quantity_needed
                    ):
                        overage = (
                            pending_order_item.units_received
                            - pending_order_item.quantity_needed
                        )
                        fulfillment_message = f"Order fulfilled with {overage} extra units"
                        pending_order_item.fulfillment_notes = f"Order fulfilled. Received {quantity} units in {package.package_size}. {overage} extra units."
                    else:
                        fulfillment_message = "Order fulfilled exactly"
                else:
                    pending_order_item.fulfillment_status = "partial"
                    remaining = (
                        pending_order_item.quantity_needed
                        - pending_order_item.units_received
                    )
                    fulfillment_message = (
                        f"Partial fulfillment: {remaining} units still needed"
                    )
                    pending_order_item.fulfillment_notes = f"Partially fulfilled. Received {quantity} units in {package.package_size}. Still need {remaining} units."

                # Update the order status
                pending_order_item.order.update_status_from_items()

            inventory_item = PackageInventory(
                medication_id=package.medication_id,
                scanned_item_id=scanned_item.id,
                current_units=quantity,
                original_units=quantity,
                status="sealed",
                order_item_id=(
                    pending_order_item.id if pending_order_item else None
                ),
            )
            db.session.add(inventory_item)

            # Create inventory log entry for the package addition
            from models import Inventory, InventoryLog

            inventory = Inventory.query.filter_by(
                medication_id=package.medication_id
            ).first()
            if inventory:
                # Calculate new total (legacy + all packages)
                old_total = package.medication.total_inventory_count
                new_total = old_total + quantity

                # Create log entry showing the package addition
                log_entry = InventoryLog(
                    inventory_id=inventory.id,
                    previous_count=old_total - quantity,  # Before this package
                    adjustment=quantity,
                    new_count=old_total,  # After this package (current total)
                    notes=f"Package scanned: {package.package_size} ({quantity} units) - Batch: {parsed.get('batch', 'N/A')}",
                )
                db.session.add(log_entry)

    db.session.commit()

    # Prepare response
    response = {
        "success": True,
        "scanned_item_id": scanned_item.id,
        "parsed_data": {
            "gtin": parsed.get("gtin"),
            "serial": parsed.get("serial"),
            "batch": parsed.get("batch"),
            "expiry": expiry_date.isoformat() if expiry_date else None,
            "national_number": (
                format_national_number_display(
                    parsed["national_number"], parsed["national_number_type"]
                )
                if parsed.get("national_number")
                else None
            ),
        },
    }

    if package and package.medication:
        response["medication"] = {
            "id": package.medication.id,
            "name": package.medication.name,
            "package_size": package.package_size,
            "quantity": quantity,
        }

        # Add order fulfillment info if applicable
        if pending_order_item:
            response["order_fulfillment"] = {
                "order_id": pending_order_item.order_id,
                "units_received": pending_order_item.units_received,
                "units_needed": pending_order_item.quantity_needed,
                "status": pending_order_item.fulfillment_status,
                "progress": pending_order_item.fulfillment_progress,
                "message": fulfillment_message,
            }

    return jsonify(response)


@bp.route("/package/<int:id>")
def package_details(id):
    """View package details."""
    scanned_item = ScannedItem.query.get_or_404(id)

    # Get inventory info if exists
    inventory = PackageInventory.query.filter_by(scanned_item_id=id).first()

    return render_template(
        "scanner/package_details.html",
        scanned_item=scanned_item,
        inventory=inventory,
    )


@bp.route("/package/<int:id>/consume", methods=["POST"])
def consume_units(id):
    """Consume units from a package."""
    inventory = PackageInventory.query.filter_by(scanned_item_id=id).first()

    if not inventory:
        flash(_("Package not in inventory"), "error")
        return redirect(url_for("scanner.package_details", id=id))

    units = request.form.get("units", type=int)
    if not units or units <= 0:
        flash(_("Invalid number of units"), "error")
        return redirect(url_for("scanner.package_details", id=id))

    if units > inventory.current_units:
        flash(_("Not enough units in package"), "error")
        return redirect(url_for("scanner.package_details", id=id))

    # Update inventory
    inventory.current_units -= units

    # Open package if sealed
    if inventory.status == "sealed":
        inventory.open_package()

    # Mark as consumed if empty
    if inventory.current_units == 0:
        inventory.consume_package()
        inventory.scanned_item.status = "consumed"

    db.session.commit()

    flash(_("%(units)d units consumed", units=units), "success")
    return redirect(url_for("scanner.package_details", id=id))


@bp.route("/package/<int:id>/expire", methods=["POST"])
def mark_expired(id):
    """Mark a package as expired."""
    scanned_item = ScannedItem.query.get_or_404(id)
    inventory = PackageInventory.query.filter_by(scanned_item_id=id).first()

    scanned_item.status = "expired"
    if inventory:
        inventory.status = "expired"

    db.session.commit()

    flash(_("Package marked as expired"), "warning")
    return redirect(url_for("scanner.index"))


@bp.route("/validate", methods=["POST"])
def validate_code():
    """Validate a pharmaceutical code."""
    data = request.json
    code = data.get("code", "")
    code_type = data.get("type", "auto")

    result = {"valid": False, "type": None, "formatted": None}

    if code_type == "auto" or code_type == "gtin":
        if validate_gtin(code):
            result["valid"] = True
            result["type"] = "GTIN"
            result["formatted"] = code

    if not result["valid"] and (code_type == "auto" or code_type == "pzn"):
        if len(code) == 8 and validate_de_pzn(code):
            result["valid"] = True
            result["type"] = "PZN"
            result["formatted"] = format_national_number_display(
                code, "DE_PZN"
            )

    return jsonify(result)
