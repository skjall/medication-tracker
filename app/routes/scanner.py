"""
Scanner routes for barcode/QR code medication package tracking.
"""

from datetime import datetime, timezone
from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    flash,
    redirect,
    url_for,
    current_app as app,
)
from flask_babel import gettext as _

from models import (
    db,
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
        # Check if there are medications eligible for migration
        from models import Medication, Inventory

        has_migration_eligible = (
            Medication.query.join(Inventory)
            .filter(Inventory.current_count > 0)
            .count()
            > 0
        )

        return render_template(
            "scanner/scan.html", has_migration_eligible=has_migration_eligible
        )

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
        app.logger.info(
            f"Identified as pharmaceutical code: {number_type} - {national_number}"
        )
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
        if parsed and parsed.get("serial"):
            app.logger.info(
                f"Identified as DataMatrix/GS1 code with GTIN: {parsed.get('gtin', 'N/A')}, Serial: {parsed.get('serial', 'N/A')[:20]}..."
            )

        # If DataMatrix parsing also failed, check if it's a simple product barcode
        if not parsed or not parsed.get("serial"):
            # Check if it's a valid EAN-13, EAN-8, or UPC-A barcode
            import re

            barcode_clean = barcode_data.strip()

            # Log the barcode type being processed
            app.logger.info(
                f"Processing unknown barcode: {barcode_clean[:20]}... (length: {len(barcode_clean)})"
            )

            # EAN-13 (13 digits), EAN-8 (8 digits), UPC-A (12 digits), ASIN (10 alphanumeric)
            if re.match(r"^[0-9]{13}$", barcode_clean):
                app.logger.info(
                    f"Identified as EAN-13 barcode: {barcode_clean}"
                )
                parsed = {
                    "gtin": barcode_clean,
                    "serial": f"EAN13_{barcode_clean}_{datetime.now().timestamp()}",
                    "expiry": None,
                    "batch": None,
                    "national_number": None,
                    "national_number_type": None,
                }
            elif re.match(r"^[0-9]{8}$", barcode_clean):
                app.logger.info(
                    f"Identified as EAN-8 barcode: {barcode_clean}"
                )
                parsed = {
                    "gtin": barcode_clean,
                    "serial": f"EAN8_{barcode_clean}_{datetime.now().timestamp()}",
                    "expiry": None,
                    "batch": None,
                    "national_number": None,
                    "national_number_type": None,
                }
            elif re.match(r"^[0-9]{12}$", barcode_clean):
                app.logger.info(
                    f"Identified as UPC-A barcode: {barcode_clean}"
                )
                parsed = {
                    "gtin": barcode_clean,
                    "serial": f"UPCA_{barcode_clean}_{datetime.now().timestamp()}",
                    "expiry": None,
                    "batch": None,
                    "national_number": None,
                    "national_number_type": None,
                }
            elif re.match(r"^[A-Z0-9]{10}$", barcode_clean, re.IGNORECASE):
                # Amazon ASIN - store as national number, not GTIN
                app.logger.info(f"Identified as Amazon ASIN: {barcode_clean}")
                parsed = {
                    "gtin": None,
                    "serial": f"ASIN_{barcode_clean}_{datetime.now().timestamp()}",
                    "expiry": None,
                    "batch": None,
                    "national_number": barcode_clean,
                    "national_number_type": "ASIN",
                }
            elif re.match(r"^[A-Z0-9]{8,14}$", barcode_clean, re.IGNORECASE):
                # Other alphanumeric product codes - store as vendor-specific national number
                app.logger.info(
                    f"Identified as vendor-specific product code: {barcode_clean}"
                )
                parsed = {
                    "gtin": None,
                    "serial": f"VENDOR_{barcode_clean}_{datetime.now().timestamp()}",
                    "expiry": None,
                    "batch": None,
                    "national_number": barcode_clean,
                    "national_number_type": "VENDOR_CODE",
                }
            else:
                # Truly unknown format - don't offer onboarding
                app.logger.warning(
                    f"Unknown barcode format: {barcode_clean[:50]}... (not EAN/UPC/ASIN/pharmaceutical)"
                )
                return (
                    jsonify(
                        {
                            "error": _("Unsupported barcode format"),
                            "hint": _(
                                "This barcode type is not supported. Only pharmaceutical codes, DataMatrix, and standard product codes (EAN-13, EAN-8, UPC-A, ASIN) are supported."
                            ),
                            "barcode_data": (
                                barcode_clean[:50]
                                if len(barcode_clean) > 50
                                else barcode_clean
                            ),
                        }
                    ),
                    400,
                )

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
            .filter(PackageInventory.status.in_(["sealed", "opened"]))
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
        existing_scanned.scanned_at = datetime.now(timezone.utc)
        db.session.flush()

    # Find package in ProductPackage table
    # Try GTIN first, then national number
    product_package = None

    # First check new ProductPackage table
    if parsed.get("gtin"):
        app.logger.info(
            f"Searching for ProductPackage with GTIN: {parsed['gtin']}"
        )
        product_package = ProductPackage.query.filter_by(
            gtin=parsed["gtin"]
        ).first()
        if product_package:
            app.logger.info(
                f"Found ProductPackage: {product_package.id} - {product_package.product.display_name}"
            )
        else:
            app.logger.info(
                f"No ProductPackage found with GTIN: {parsed['gtin']}"
            )

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

        # Create package inventory for new package-based system
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
                gtin=parsed.get("gtin")
                or product_package.gtin,  # Use package GTIN if not in barcode
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

        # Find pending order item by matching active ingredient
        from models import Order, OrderItem

        pending_order_item = None
        fulfillment_message = None

        # Check if this package matches any pending order
        if product_package.product:
            # Look for the oldest pending or partial order with matching product or ingredient
            pending_order_item = (
                OrderItem.query.join(Order)
                .filter(
                    db.or_(
                        OrderItem.product_id == product_package.product.id,
                        OrderItem.active_ingredient_id
                        == product_package.product.active_ingredient_id,
                    ),
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
                pending_order_item.fulfilled_at = datetime.now(timezone.utc)
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
                    pending_order_item.fulfillment_notes = _(
                        "Order fulfilled. Received %(quantity)d units in %(package_size)s. %(overage)d extra units.",
                        quantity=product_package.quantity,
                        package_size=product_package.package_size,
                        overage=overage,
                    )
                else:
                    fulfillment_message = _("Order fulfilled exactly")
                    pending_order_item.fulfillment_notes = _(
                        "Order fulfilled. Received %(quantity)d units in %(package_size)s.",
                        quantity=product_package.quantity,
                        package_size=product_package.package_size,
                    )
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
                pending_order_item.fulfillment_notes = _(
                    "Partially fulfilled. Received %(quantity)d units in %(package_size)s. Still need %(remaining)d units.",
                    quantity=product_package.quantity,
                    package_size=product_package.package_size,
                    remaining=remaining,
                )

            # Update the order status
            pending_order_item.order.update_status_from_items()

        # Create PackageInventory entry WITHOUT medication_id (pure package-based)
        inventory_item = PackageInventory(
            medication_id=None,  # NO medication_id for new system
            scanned_item_id=scanned_item.id,
            current_units=product_package.quantity,
            original_units=product_package.quantity,
            status="sealed",
            order_item_id=(
                pending_order_item.id if pending_order_item else None
            ),
        )
        db.session.add(inventory_item)

        # Create inventory log for tracking (only if legacy system is linked)
        from models import Inventory, InventoryLog

        # Try to find legacy inventory for logging purposes only
        inventory = None
        if product_package.product.legacy_medication_id:
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
                    notes=_(
                        "Package scanned: %(package_size)s (%(quantity)d units) - Batch: %(batch)s",
                        package_size=product_package.package_size,
                        quantity=product_package.quantity,
                        batch=parsed.get("batch", _("N/A")),
                    ),
                )
                db.session.add(log_entry)

        # Commit the database changes
        db.session.commit()

        # Build response message (for both legacy and new package-based products)
        if fulfillment_message:
            message = _(
                "Added to inventory: %(product_name)s %(package_size)s (%(quantity)d units). %(fulfillment)s",
                product_name=product_package.product.display_name,
                package_size=product_package.package_size,
                quantity=product_package.quantity,
                fulfillment=fulfillment_message,
            )
        else:
            message = _(
                "Added to inventory: %(product_name)s %(package_size)s (%(quantity)d units)",
                product_name=product_package.product.display_name,
                package_size=product_package.package_size,
                quantity=product_package.quantity,
            )

        # Return success with inventory added (for both legacy and new package-based products)
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

    # If not found in new system, return not found response
    if not product_package:
        # Create user-friendly error message based on what we recognized
        if parsed.get("national_number") and parsed.get(
            "national_number_type"
        ):
            # We have a recognized code (pharmaceutical or vendor-specific)
            type_labels = {
                "DE_PZN": "PZN",
                "FR_CIP13": "CIP13",
                "FR_CIP7": "CIP7",
                "BE_CNK": "CNK",
                "NL_ZINDEX": "Z-Index",
                "ES_CN": "CN",
                "IT_AIC": "AIC",
                "ASIN": "Amazon ASIN",
                "VENDOR_CODE": _("Product Code"),
            }
            label = type_labels.get(
                parsed["national_number_type"], parsed["national_number_type"]
            )
            error_msg = _(
                "%(label)s %(number)s not found",
                label=label,
                number=parsed["national_number"],
            )
            hint = _("Please add this package.")
        elif parsed.get("gtin"):
            # We have a recognized GTIN (EAN-13, EAN-8, UPC-A)
            if parsed.get("serial", "").startswith("EAN13"):
                error_msg = _(
                    "EAN-13 barcode %(code)s not found", code=parsed["gtin"]
                )
                hint = _("Please add this package.")
            elif parsed.get("serial", "").startswith("EAN8"):
                error_msg = _(
                    "EAN-8 barcode %(code)s not found", code=parsed["gtin"]
                )
                hint = _("Please add this package.")
            elif parsed.get("serial", "").startswith("UPCA"):
                error_msg = _(
                    "UPC barcode %(code)s not found", code=parsed["gtin"]
                )
                hint = _("Please add this package.")
            else:
                error_msg = _(
                    "Product barcode %(code)s not found", code=parsed["gtin"]
                )
                hint = _("Please add this package.")
        else:
            # This should never happen now since we reject truly unknown formats earlier
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
