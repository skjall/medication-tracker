"""
Scanner routes for barcode/QR code medication package tracking.
"""

from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_babel import gettext as _

from models import db, MedicationPackage, ScannedItem, PackageInventory
from scanner_parser import (
    parse_datamatrix, 
    parse_expiry_date, 
    format_national_number_display
)
from barcode_validator import identify_barcode_format

bp = Blueprint('scanner', __name__, url_prefix='/scanner')


@bp.route('/')
def index():
    """Redirect directly to scanner."""
    return redirect(url_for('scanner.scan'))


@bp.route('/scan', methods=['GET', 'POST'])
def scan():
    """Handle barcode scanning."""
    if request.method == 'GET':
        return render_template('scanner/scan.html')
    
    # Process scanned data
    data = request.json
    barcode_data = data.get('barcode')
    
    if not barcode_data:
        return jsonify({'error': _('No barcode data provided')}), 400
    
    # Clean up barcode data - remove leading minus sign (standard for Code 39 PZN barcodes)
    # All German PZN barcodes are printed with "-" prefix in Code 39 format
    barcode_data = str(barcode_data).lstrip('-')
    
    # Try to identify standalone barcode format (PZN, CIP, CNK, etc.)
    barcode_info = identify_barcode_format(barcode_data)
    
    if barcode_info:
        # This is a recognized standalone pharmaceutical barcode
        national_number, number_type = barcode_info
        parsed = {
            'gtin': None,
            'serial': f'{number_type}_{national_number}_{datetime.now().timestamp()}',  # Generate unique serial
            'expiry': None,
            'batch': None,
            'national_number': national_number,
            'national_number_type': number_type
        }
    else:
        # Parse as DataMatrix or other GS1 format
        parsed = parse_datamatrix(barcode_data)
        
        # If DataMatrix parsing also failed, create minimal structure for unknown barcode
        if not parsed.get('serial'):
            parsed = {
                'gtin': None,
                'serial': f'UNKNOWN_{barcode_data[:20]}_{datetime.now().timestamp()}',
                'expiry': None,
                'batch': None,
                'national_number': None,
                'national_number_type': None
            }
    
    if not parsed.get('serial'):
        return jsonify({'error': _('Invalid barcode: missing serial number')}), 400
    
    # Check for duplicate scan
    existing = ScannedItem.query.filter_by(serial_number=parsed['serial']).first()
    if existing:
        return jsonify({
            'error': _('Package already scanned'),
            'details': {
                'scanned_at': existing.scanned_at.isoformat(),
                'medication': existing.package.medication.name if existing.package else _('Unknown')
            }
        }), 409
    
    # Find or create medication package
    # Try GTIN first, then national number
    package = None
    if parsed.get('gtin'):
        package = MedicationPackage.query.filter_by(gtin=parsed['gtin']).first()
    
    # If not found by GTIN, try national number
    if not package and parsed.get('national_number'):
        # First try with the exact type if we know it
        if parsed.get('national_number_type'):
            package = MedicationPackage.query.filter_by(
                national_number=parsed['national_number'],
                national_number_type=parsed['national_number_type']
            ).first()
        
        # If still not found, try just the number (in case type doesn't match)
        if not package:
            package = MedicationPackage.query.filter_by(
                national_number=parsed['national_number']
            ).first()
    
    # If package found, update missing information
    if package:
        updated = False
        # If package has no GTIN but we scanned one, add it
        if not package.gtin and parsed.get('gtin'):
            package.gtin = parsed['gtin']
            updated = True
            
        # If package has no national number but we extracted one, add it
        if not package.national_number and parsed.get('national_number'):
            package.national_number = parsed['national_number']
            package.national_number_type = parsed['national_number_type']
            package.country_code = parsed.get('national_number_type', '').split('_')[0] if parsed.get('national_number_type') else None
            updated = True
            
        if updated:
            db.session.flush()
            flash(_('Package information updated with scanned data'), 'info')
    
    
    # If no package found, return error - don't save unknown items
    if not package:
        # Create user-friendly error message based on what we recognized
        if parsed.get('national_number') and parsed.get('national_number_type'):
            # We have a recognized pharmaceutical code
            type_labels = {
                'DE_PZN': 'PZN',
                'FR_CIP13': 'CIP13',
                'FR_CIP7': 'CIP7',
                'BE_CNK': 'CNK',
                'NL_ZINDEX': 'Z-Index',
                'ES_CN': 'CN',
                'IT_AIC': 'AIC'
            }
            label = type_labels.get(parsed['national_number_type'], parsed['national_number_type'])
            error_msg = f"{label} {parsed['national_number']} not found in database"
            hint = _("Please add this medication first, then scan again")
        else:
            # Unknown barcode format
            error_msg = _('Unrecognized barcode format')
            hint = _("This barcode type is not supported")
        
        return jsonify({
            'error': error_msg,
            'hint': hint,
            'details': {
                'national_number': parsed.get('national_number'),
                'national_number_type': parsed.get('national_number_type'),
                'gtin': parsed.get('gtin'),
                'batch': parsed.get('batch'),
                'expiry': parse_expiry_date(parsed['expiry']).isoformat() if parsed.get('expiry') else None
            }
        }), 404
    
    # Create scanned item only if package is known
    expiry_date = None
    if parsed.get('expiry'):
        expiry_date = parse_expiry_date(parsed['expiry'])
        if expiry_date:
            expiry_date = expiry_date.date()
    
    scanned_item = ScannedItem(
        medication_package_id=package.id if package else None,
        gtin=parsed.get('gtin'),
        national_number=parsed.get('national_number'),
        national_number_type=parsed.get('national_number_type'),
        serial_number=parsed['serial'],
        batch_number=parsed.get('batch'),
        expiry_date=expiry_date,
        raw_data=barcode_data,
        status='active'
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
            if package.package_size == 'N1':
                quantity = med.package_size_n1
            elif package.package_size == 'N2':
                quantity = med.package_size_n2
            elif package.package_size == 'N3':
                quantity = med.package_size_n3
        
        if quantity:
            # Find pending order item for this medication
            from models import Order, OrderItem
            pending_order_item = None
            
            # Look for the oldest pending order with this medication
            pending_order_item = (
                OrderItem.query.join(Order)
                .filter(
                    OrderItem.medication_id == package.medication_id,
                    OrderItem.fulfillment_status == 'pending',
                    Order.status.in_(['planned', 'printed'])
                )
                .order_by(Order.created_date.asc())
                .first()
            )
            
            inventory_item = PackageInventory(
                medication_id=package.medication_id,
                scanned_item_id=scanned_item.id,
                current_units=quantity,
                original_units=quantity,
                status='sealed',
                order_item_id=pending_order_item.id if pending_order_item else None
            )
            db.session.add(inventory_item)
            
            # Create inventory log entry for the package addition
            from models import Inventory, InventoryLog
            inventory = Inventory.query.filter_by(medication_id=package.medication_id).first()
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
                    notes=f"Package scanned: {package.package_size} ({quantity} units) - Batch: {parsed.get('batch', 'N/A')}"
                )
                db.session.add(log_entry)
    
    db.session.commit()
    
    # Prepare response
    response = {
        'success': True,
        'scanned_item_id': scanned_item.id,
        'parsed_data': {
            'gtin': parsed.get('gtin'),
            'serial': parsed.get('serial'),
            'batch': parsed.get('batch'),
            'expiry': expiry_date.isoformat() if expiry_date else None,
            'national_number': format_national_number_display(
                parsed['national_number'], 
                parsed['national_number_type']
            ) if parsed.get('national_number') else None
        }
    }
    
    if package and package.medication:
        response['medication'] = {
            'id': package.medication.id,
            'name': package.medication.name,
            'package_size': package.package_size,
            'quantity': quantity
        }
    
    return jsonify(response)


@bp.route('/package/<int:id>')
def package_details(id):
    """View package details."""
    scanned_item = ScannedItem.query.get_or_404(id)
    
    # Get inventory info if exists
    inventory = PackageInventory.query.filter_by(scanned_item_id=id).first()
    
    return render_template(
        'scanner/package_details.html',
        scanned_item=scanned_item,
        inventory=inventory
    )


@bp.route('/package/<int:id>/consume', methods=['POST'])
def consume_units(id):
    """Consume units from a package."""
    inventory = PackageInventory.query.filter_by(scanned_item_id=id).first()
    
    if not inventory:
        flash(_('Package not in inventory'), 'error')
        return redirect(url_for('scanner.package_details', id=id))
    
    units = request.form.get('units', type=int)
    if not units or units <= 0:
        flash(_('Invalid number of units'), 'error')
        return redirect(url_for('scanner.package_details', id=id))
    
    if units > inventory.current_units:
        flash(_('Not enough units in package'), 'error')
        return redirect(url_for('scanner.package_details', id=id))
    
    # Update inventory
    inventory.current_units -= units
    
    # Open package if sealed
    if inventory.status == 'sealed':
        inventory.open_package()
    
    # Mark as consumed if empty
    if inventory.current_units == 0:
        inventory.consume_package()
        inventory.scanned_item.status = 'consumed'
    
    db.session.commit()
    
    flash(_('%(units)d units consumed', units=units), 'success')
    return redirect(url_for('scanner.package_details', id=id))


@bp.route('/package/<int:id>/expire', methods=['POST'])
def mark_expired(id):
    """Mark a package as expired."""
    scanned_item = ScannedItem.query.get_or_404(id)
    inventory = PackageInventory.query.filter_by(scanned_item_id=id).first()
    
    scanned_item.status = 'expired'
    if inventory:
        inventory.status = 'expired'
    
    db.session.commit()
    
    flash(_('Package marked as expired'), 'warning')
    return redirect(url_for('scanner.index'))


@bp.route('/validate', methods=['POST'])
def validate_code():
    """Validate a pharmaceutical code."""
    data = request.json
    code = data.get('code', '')
    code_type = data.get('type', 'auto')
    
    result = {'valid': False, 'type': None, 'formatted': None}
    
    if code_type == 'auto' or code_type == 'gtin':
        if validate_gtin(code):
            result['valid'] = True
            result['type'] = 'GTIN'
            result['formatted'] = code
    
    if not result['valid'] and (code_type == 'auto' or code_type == 'pzn'):
        if len(code) == 8 and validate_de_pzn(code):
            result['valid'] = True
            result['type'] = 'PZN'
            result['formatted'] = format_national_number_display(code, 'DE_PZN')
    
    return jsonify(result)