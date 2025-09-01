"""
Migration scanner routes for transitioning from sum-based to package-based inventory.
"""

from datetime import datetime, timezone
from calendar import monthrange
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session, flash, current_app as app
from flask_babel import gettext as _

from models import (
    db,
    Medication,
    Inventory,
    InventoryLog,
    ActiveIngredient,
    MedicationProduct,
    ProductPackage,
    PackageInventory,
    ScannedItem
)

bp = Blueprint('migration_scanner', __name__, url_prefix='/migration')


def parse_expiry_date(expiry_str):
    """Parse expiry date string, handling day 00 as last day of month.
    
    Args:
        expiry_str: Date string in format YYYY-MM-DD or with day 00
        
    Returns:
        datetime object or None
    """
    if not expiry_str:
        return None
    
    try:
        # Check if day is 00 (last day of month)
        if expiry_str.endswith('-00'):
            # Extract year and month
            year_month = expiry_str[:-3]  # Remove '-00'
            year, month = year_month.split('-')
            year = int(year)
            month = int(month)
            
            # Get last day of the month
            last_day = monthrange(year, month)[1]
            
            # Create date with last day of month
            return datetime(year, month, last_day, tzinfo=timezone.utc)
        else:
            # Normal date parsing
            return datetime.fromisoformat(expiry_str).replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError) as e:
        app.logger.warning(f"Failed to parse expiry date '{expiry_str}': {e}")
        return None


@bp.route('/select')
def select_medication():
    """Show products eligible for migration (have old inventory via medications)."""
    
    # Get medications with old inventory > 0
    medications_with_inventory = Medication.query.join(Inventory).filter(
        Inventory.current_count > 0
    ).all()
    
    if not medications_with_inventory:
        flash(_('No medications need migration. All inventory is already package-based.'), 'info')
        return redirect(url_for('scanner.scan'))
    
    # Build a list of products to migrate
    products_to_migrate = []
    
    for medication in medications_with_inventory:
        product = None
        
        app.logger.info(f"Processing medication: {medication.name} (ID: {medication.id})")
        
        # First check if medication has a default product
        if medication.default_product_id:
            product = MedicationProduct.query.get(medication.default_product_id)
            app.logger.info(f"Found default product: {product.display_name if product else 'None'}")
        
        if not product:
            # Try to find product by exact medication name match
            product = MedicationProduct.query.filter_by(
                brand_name=medication.name
            ).first()
            if product:
                app.logger.info(f"Found product by exact name match: {product.display_name}")
        
        if not product:
            # Try to find product through ingredient
            ingredient = ActiveIngredient.query.filter_by(
                name=medication.name
            ).first()
            
            if ingredient:
                app.logger.info(f"Found ingredient: {ingredient.name} (ID: {ingredient.id})")
                # Get the first product for this ingredient
                product = MedicationProduct.query.filter_by(
                    active_ingredient_id=ingredient.id
                ).first()
                if product:
                    app.logger.info(f"Found product through ingredient: {product.display_name}")
            else:
                app.logger.info(f"No ingredient found for medication: {medication.name}")
        
        # Create a product data object for display
        product_data = {
            'medication_id': medication.id,
            'medication_name': medication.name,
            'product_name': product.display_name if product else medication.name,
            'product_id': product.id if product else None,
            'inventory_count': medication.inventory.current_count,
            'has_product': product is not None
        }
        
        products_to_migrate.append(product_data)
    
    # Sort by product name
    products_to_migrate.sort(key=lambda x: x['product_name'])
    
    return render_template(
        'migration/select.html',
        products=products_to_migrate
    )


@bp.route('/scanner/<int:medication_id>')
def migration_scanner(medication_id):
    """Main migration scanner view for a specific medication."""
    
    medication = Medication.query.get_or_404(medication_id)
    
    # Check if medication has old inventory
    if not medication.inventory:
        flash(_('This medication has no inventory to migrate'), 'info')
        return redirect(url_for('migration_scanner.select_medication'))
    
    # Log for debugging
    app.logger.info(f"Migration scanner: Medication {medication.name} (ID: {medication_id})")
    app.logger.info(f"Inventory count: {medication.inventory.current_count if medication.inventory else 'No inventory'}")
    
    # Get the product associated with this medication
    product = None
    if medication.default_product_id:
        product = MedicationProduct.query.get(medication.default_product_id)
    
    # Get any existing packages for this medication's product or ingredient
    known_packages = []
    if product:
        # Get packages for the specific product
        known_packages.extend(product.packages)
    else:
        # Fallback: Try to find packages through the ingredient
        ingredient = ActiveIngredient.query.filter_by(
            name=medication.name
        ).first()
        if ingredient:
            for prod in ingredient.products:
                known_packages.extend(prod.packages)
    
    # Get scanned packages from session
    session_key = f'migration_{medication_id}_packages'
    scanned_packages = session.get(session_key, [])
    
    # Calculate remaining units
    total_scanned = sum(pkg.get('units', 0) for pkg in scanned_packages)
    remaining_units = max(0, medication.inventory.current_count - total_scanned)
    
    app.logger.info(f"Scanned packages: {len(scanned_packages)}, Total scanned units: {total_scanned}")
    app.logger.info(f"Remaining units: {remaining_units} (from {medication.inventory.current_count} - {total_scanned})")
    
    return render_template(
        'migration/scanner.html',
        medication=medication,
        product=product,
        remaining_units=remaining_units,
        scanned_packages=scanned_packages,
        known_packages=known_packages
    )


@bp.route('/scan', methods=['POST'])
def scan_package():
    """Process a scanned package during migration."""
    
    data = request.get_json()
    medication_id = data.get('medication_id')
    barcode_data = data.get('barcode_data', {})
    
    medication = Medication.query.get_or_404(medication_id)
    
    # Check if this is merged data from frontend (two-step scanning)
    if barcode_data.get('merged'):
        app.logger.info("Using pre-merged scan data from two-step scanning")
        # Data was already merged in frontend, use it directly
        gtin = barcode_data.get('gtin')
        serial = barcode_data.get('serial')
        batch = barcode_data.get('batch')
        expiry = barcode_data.get('expiry')
        national_number = barcode_data.get('national_number')
        national_number_type = barcode_data.get('national_number_type')
    else:
        # Parse barcode data normally
        gtin = barcode_data.get('gtin')
        serial = barcode_data.get('serial')
        batch = barcode_data.get('batch')
        expiry = barcode_data.get('expiry')
        national_number = barcode_data.get('national_number')
        national_number_type = barcode_data.get('national_number_type')
    
    app.logger.info(f"Migration scan received: gtin={gtin}, national_number={national_number}, "
                   f"national_number_type={national_number_type}, serial={serial[:20] if serial else None}")
    
    # Check for duplicate serial with time window
    session_key = f'migration_{medication_id}_serials_with_time'
    scanned_serials_dict = session.get(session_key, {})
    
    if serial and serial in scanned_serials_dict:
        last_scan_time = scanned_serials_dict[serial]
        current_time = datetime.now(timezone.utc).timestamp()
        
        if current_time - last_scan_time < 20:
            # Within 20 seconds - silently ignore (user hasn't moved package away yet)
            return jsonify({
                'success': False,
                'silent': True  # Don't show error message
            })
        else:
            # After 20 seconds - this is a real duplicate
            return jsonify({
                'error': _('Package already scanned'),
                'duplicate': True
            }), 400
    
    # Try to find existing package definition
    package = None
    if gtin:
        package = ProductPackage.query.filter_by(gtin=gtin).first()
    elif national_number:
        package = ProductPackage.query.filter_by(
            national_number=national_number
        ).first()
    
    if package:
        # Get current packages and calculate total
        session_key = f'migration_{medication_id}_packages'
        packages = session.get(session_key, [])
        current_total = sum(p['units'] for p in packages)
        original_inventory = medication.inventory.current_count
        remaining_units = max(0, original_inventory - current_total)
        
        # Check if this package would exceed the original inventory
        if current_total >= original_inventory:
            # Already at or over limit - reject
            app.logger.info(f"Migration limit reached: {current_total} >= {original_inventory}")
            return jsonify({
                'error': _('Migration complete. All %(count)s units have been accounted for.', count=original_inventory),
                'limit_reached': True,
                'remaining_units': 0
            }), 400
        
        # Determine if this should be an open package
        package_units = package.quantity
        if current_total + package_units > original_inventory:
            # This package would exceed - make it an open package with only remaining units
            package_units = remaining_units
            package_status = 'opened'
            app.logger.info(f"Auto-adjusting package to open with {package_units} units (remaining)")
        else:
            package_status = 'full'
        
        # Package is known, add to migration
        package_data = {
            'serial': serial,
            'gtin': gtin,
            'batch': batch,
            'expiry': expiry,
            'national_number': national_number,
            'national_number_type': national_number_type,
            'package_id': package.id,
            'package_size': package.package_size,
            'units': package_units,
            'product_name': package.product.display_name,
            'status': package_status
        }
        
        # Add to session
        packages.append(package_data)
        session[session_key] = packages
        
        # Add serial with timestamp
        if serial:
            serial_key = f'migration_{medication_id}_serials_with_time'
            serials_dict = session.get(serial_key, {})
            serials_dict[serial] = datetime.now(timezone.utc).timestamp()
            session[serial_key] = serials_dict
        
        # Force session save
        session.permanent = True
        session.modified = True
        
        # Calculate remaining
        total_migrated = sum(p['units'] for p in packages)
        remaining = max(0, medication.inventory.current_count - total_migrated)
        
        app.logger.info(f"Migration scan: Added package for medication {medication.name}")
        app.logger.info(f"Total migrated: {total_migrated}, Remaining: {remaining}")
        app.logger.info(f"Package status: {package_status}, units: {package_units}")
        
        return jsonify({
            'success': True,
            'package': package_data,
            'remaining_units': remaining,
            'total_scanned': len(packages)
        })
    
    else:
        # Unknown package - need onboarding
        return jsonify({
            'unknown_package': True,
            'gtin': gtin,
            'national_number': national_number,
            'national_number_type': national_number_type,
            'batch': batch,
            'expiry': expiry,
            'serial': serial
        })


@bp.route('/onboard-package', methods=['POST'])
def onboard_migration_package():
    """Quick onboard a package during migration."""
    
    data = request.get_json()
    medication_id = data.get('medication_id')
    serial = data.get('serial')
    
    app.logger.info(f"Onboard package received: gtin={data.get('gtin')}, "
                   f"national_number={data.get('national_number')}, "
                   f"national_number_type={data.get('national_number_type')}")
    
    medication = Medication.query.get_or_404(medication_id)
    
    # Check current migration status first
    session_key = f'migration_{medication_id}_packages'
    packages = session.get(session_key, [])
    current_total = sum(p['units'] for p in packages)
    original_inventory = medication.inventory.current_count
    remaining_units = max(0, original_inventory - current_total)
    
    # If already at limit, reject
    if current_total >= original_inventory:
        app.logger.info(f"Migration limit reached during onboarding: {current_total} >= {original_inventory}")
        return jsonify({
            'error': _('Migration complete. All %(count)s units have been accounted for.', count=original_inventory),
            'limit_reached': True,
            'remaining_units': 0
        }), 400
    
    # IMPORTANT: During migration, we must use the existing product linked to the medication
    # The old inventory is tied to medications, which should already have an associated product
    product = None
    
    # First, check if the medication already has a default product
    if medication.default_product_id:
        product = MedicationProduct.query.get(medication.default_product_id)
        app.logger.info(f"Using medication's default product: {product.id} - {product.brand_name}")
    
    if not product:
        # Try to find product by exact medication name match
        product = MedicationProduct.query.filter_by(
            brand_name=medication.name
        ).first()
        
        if product:
            app.logger.info(f"Found product by exact name match: {product.display_name}")
            # Link this product to the medication for future use
            medication.default_product_id = product.id
            db.session.flush()
    
    if not product:
        # Find the EXISTING ingredient - don't create new ones during migration
        # First try exact match
        ingredient = ActiveIngredient.query.filter_by(
            name=medication.name
        ).first()
        
        if not ingredient:
            # Try partial match (medication might be "MucoClear 6% 4ml" but ingredient is "MucoClear")
            ingredient = ActiveIngredient.query.filter(
                ActiveIngredient.name.like(f"%{medication.name.split()[0]}%")
            ).first()
        
        if not ingredient:
            # During migration, we should NOT create new ingredients
            # This is a data issue that needs to be resolved
            app.logger.error(f"No ingredient found for medication {medication.name} during migration")
            return jsonify({
                'error': _('Product configuration error. Please ensure the medication has an associated product.'),
                'unknown_package': False
            }), 400
        
        # Try to find an existing product for this ingredient
        # Get ANY product for this ingredient (during migration we use existing products)
        product = MedicationProduct.query.filter_by(
            active_ingredient_id=ingredient.id
        ).first()
        
        if not product:
            app.logger.error(f"No product found for ingredient {ingredient.name} during migration")
            return jsonify({
                'error': _('No product found for this medication. Please configure the product first.'),
                'unknown_package': False
            }), 400
        
        app.logger.info(f"Using product: {product.id} - {product.brand_name} for ingredient: {ingredient.name}")
        
        # Set this as the default product for the medication
        if not medication.default_product_id:
            medication.default_product_id = product.id
            db.session.flush()
    
    # Check if a package with this size already exists for the product
    package_size = data.get('package_size')
    existing_package = ProductPackage.query.filter_by(
        product_id=product.id,
        package_size=package_size
    ).first()
    
    if existing_package:
        # Update existing package
        app.logger.info(f"Updating existing package {existing_package.id}: "
                       f"gtin={data.get('gtin')}, national_number={data.get('national_number')}, "
                       f"national_number_type={data.get('national_number_type')}")
        
        existing_package.quantity = data.get('units')
        existing_package.gtin = data.get('gtin') or existing_package.gtin
        existing_package.national_number = data.get('national_number') or existing_package.national_number
        existing_package.national_number_type = data.get('national_number_type') or existing_package.national_number_type
        existing_package.manufacturer = data.get('manufacturer', '') or existing_package.manufacturer
        existing_package.is_active = True
        package = existing_package
        
        app.logger.info(f"Updated package {package.id}: gtin={package.gtin}, "
                       f"national_number={package.national_number}, "
                       f"national_number_type={package.national_number_type}")
    else:
        # Create new package
        package = ProductPackage(
            product_id=product.id,
            package_size=package_size,
            quantity=data.get('units'),
            gtin=data.get('gtin'),
            national_number=data.get('national_number'),
            national_number_type=data.get('national_number_type'),
            manufacturer=data.get('manufacturer', ''),
            is_active=True
        )
        db.session.add(package)
        app.logger.info(f"Created new package for size {package_size}")
    
    db.session.commit()
    
    # Now add to migration session
    # Ensure we always have a serial number
    if not serial:
        serial = f'ONBOARD_{medication_id}_{datetime.now(timezone.utc).timestamp()}'
    
    # Determine actual units to add
    requested_units = data.get('actual_units', package.quantity)
    if data.get('is_open'):
        # User explicitly marked as open - use their value
        actual_units = min(requested_units, remaining_units)
        package_status = 'opened'
    elif current_total + requested_units > original_inventory:
        # Would exceed limit - auto-adjust to open package
        actual_units = remaining_units
        package_status = 'opened'
        app.logger.info(f"Auto-adjusting onboarded package to open with {actual_units} units")
    else:
        actual_units = requested_units
        package_status = 'full'
    
    package_data = {
        'serial': serial,
        'gtin': data.get('gtin'),
        'batch': data.get('batch'),
        'expiry': data.get('expiry'),
        'national_number': data.get('national_number'),
        'national_number_type': data.get('national_number_type'),
        'package_id': package.id,
        'package_size': package.package_size,
        'units': actual_units,
        'product_name': product.display_name,
        'status': package_status
    }
    
    # Add to session (packages list already retrieved above)
    packages.append(package_data)
    session[session_key] = packages
    
    # Add serial with timestamp
    if package_data['serial']:
        serial_key = f'migration_{medication_id}_serials_with_time'
        serials_dict = session.get(serial_key, {})
        serials_dict[package_data['serial']] = datetime.now(timezone.utc).timestamp()
        session[serial_key] = serials_dict
    
    # Force session save
    session.permanent = True
    session.modified = True
    
    # Calculate remaining
    total_migrated = sum(p['units'] for p in packages)
    remaining = max(0, medication.inventory.current_count - total_migrated)
    
    # Log for debugging
    app.logger.info(f"Migration onboard: Added package {package.id} for medication {medication.name}")
    app.logger.info(f"Total migrated: {total_migrated}, Remaining: {remaining}")
    
    return jsonify({
        'success': True,
        'package': package_data,
        'remaining_units': remaining,
        'total_scanned': len(packages)
    })


@bp.route('/add-open-package', methods=['POST'])
def add_open_package():
    """Manually add an open package without scanning."""
    
    data = request.get_json()
    medication_id = data.get('medication_id')
    units = data.get('units')
    package_size = data.get('package_size')
    
    medication = Medication.query.get_or_404(medication_id)
    
    # Create a virtual package entry
    package_data = {
        'serial': f'OPEN_{medication_id}_{datetime.now(timezone.utc).timestamp()}',
        'gtin': None,
        'batch': 'UNKNOWN',
        'expiry': None,
        'package_id': None,
        'package_size': package_size,
        'units': units,
        'product_name': medication.name,
        'status': 'opened'
    }
    
    # Add to session
    session_key = f'migration_{medication_id}_packages'
    packages = session.get(session_key, [])
    packages.append(package_data)
    session[session_key] = packages
    
    # Calculate remaining
    total_migrated = sum(p['units'] for p in packages)
    remaining = max(0, medication.inventory.current_count - total_migrated)
    
    return jsonify({
        'success': True,
        'package': package_data,
        'remaining_units': remaining,
        'total_scanned': len(packages)
    })


@bp.route('/edit-package', methods=['POST'])
def edit_package():
    """Edit a scanned package during migration."""
    
    data = request.get_json()
    medication_id = data.get('medication_id')
    serial = data.get('serial')
    package_size = data.get('package_size')
    original_units = data.get('original_units')
    actual_units = data.get('actual_units')
    is_open = data.get('is_open', False)
    
    medication = Medication.query.get_or_404(medication_id)
    
    # Get packages from session
    session_key = f'migration_{medication_id}_packages'
    packages = session.get(session_key, [])
    
    # Find and update the package
    package_found = False
    updated_package = None
    for package in packages:
        if package.get('serial') == serial:
            package['package_size'] = package_size
            package['units'] = actual_units
            package['status'] = 'opened' if is_open else 'full'
            # Update original units if it's a known package
            if package.get('package_id') and original_units:
                # This is just for display, actual DB update would happen on completion
                pass
            updated_package = package.copy()
            package_found = True
            break
    
    if not package_found:
        return jsonify({'error': _('Package not found')}), 404
    
    # Save session
    session[session_key] = packages
    session.permanent = True
    session.modified = True
    
    # Calculate remaining
    total_migrated = sum(p['units'] for p in packages)
    remaining = max(0, medication.inventory.current_count - total_migrated)
    
    app.logger.info(f"Migration edit: Updated package {serial} for medication {medication.name}")
    app.logger.info(f"Total migrated: {total_migrated}, Remaining: {remaining}")
    
    return jsonify({
        'success': True,
        'package': updated_package,
        'remaining_units': remaining,
        'total_scanned': len(packages)
    })


@bp.route('/save-progress/<int:medication_id>', methods=['POST'])
def save_migration_progress(medication_id):
    """Save migration progress without clearing old inventory."""
    
    medication = Medication.query.get_or_404(medication_id)
    
    # Get scanned packages from session
    session_key = f'migration_{medication_id}_packages'
    scanned_packages = session.get(session_key, [])
    
    if not scanned_packages:
        return jsonify({'error': _('No packages scanned')}), 400
    
    # Create PackageInventory entries for each scanned package
    for pkg_data in scanned_packages:
        # Create or find ScannedItem
        scanned_item = ScannedItem(
            serial_number=pkg_data['serial'] or f'MIGRATION_{datetime.now(timezone.utc).timestamp()}',
            gtin=pkg_data.get('gtin'),
            batch_number=pkg_data.get('batch'),
            expiry_date=parse_expiry_date(pkg_data.get('expiry')),
            national_number=pkg_data.get('national_number'),
            national_number_type=pkg_data.get('national_number_type'),
            scanned_at=datetime.now(timezone.utc),
            status='active'
        )
        db.session.add(scanned_item)
        db.session.flush()
        
        # Create PackageInventory
        inventory_item = PackageInventory(
            scanned_item_id=scanned_item.id,
            current_units=pkg_data['units'],
            original_units=pkg_data.get('package_id') and ProductPackage.query.get(pkg_data['package_id']).quantity or pkg_data['units'],
            status='opened' if pkg_data['status'] == 'opened' else 'sealed',
            medication_id=medication.id  # Link to old medication for reference
        )
        db.session.add(inventory_item)
    
    # Update old inventory to reduce by scanned amount (but don't set to 0)
    if medication.inventory:
        total_migrated = sum(p['units'] for p in scanned_packages)
        
        # Log the partial migration
        log_entry = InventoryLog(
            inventory_id=medication.inventory.id,
            previous_count=medication.inventory.current_count,
            adjustment=-total_migrated,
            new_count=max(0, medication.inventory.current_count - total_migrated),
            notes=_('Partial migration to package-based inventory: %(count)s packages', count=len(scanned_packages))
        )
        db.session.add(log_entry)
        
        # Reduce inventory by migrated amount
        medication.inventory.current_count = max(0, medication.inventory.current_count - total_migrated)
        medication.inventory.last_updated = datetime.now(timezone.utc)
    
    db.session.commit()
    
    # Clear session data
    session.pop(session_key, None)
    session.pop(f'migration_{medication_id}_serials_with_time', None)
    
    flash(_('Progress saved! %(count)s packages migrated.', count=len(scanned_packages)), 'success')
    
    return jsonify({
        'success': True,
        'redirect': url_for('migration_scanner.select_medication')
    })


@bp.route('/complete/<int:medication_id>', methods=['POST'])
def complete_migration(medication_id):
    """Complete the migration for a medication."""
    
    medication = Medication.query.get_or_404(medication_id)
    
    # Get scanned packages from session
    session_key = f'migration_{medication_id}_packages'
    scanned_packages = session.get(session_key, [])
    
    if not scanned_packages:
        return jsonify({'error': _('No packages scanned')}), 400
    
    # Create PackageInventory entries for each scanned package
    app.logger.info(f"Complete migration: Creating {len(scanned_packages)} package inventory entries for {medication.name}")
    
    for pkg_data in scanned_packages:
        app.logger.info(f"Processing package: serial={pkg_data.get('serial')}, gtin={pkg_data.get('gtin')}, "
                       f"national_number={pkg_data.get('national_number')}, units={pkg_data.get('units')}")
        # Create or find ScannedItem
        scanned_item = ScannedItem(
            serial_number=pkg_data['serial'] or f'MIGRATION_{datetime.now(timezone.utc).timestamp()}',
            gtin=pkg_data.get('gtin'),
            batch_number=pkg_data.get('batch'),
            expiry_date=parse_expiry_date(pkg_data.get('expiry')),
            national_number=pkg_data.get('national_number'),
            national_number_type=pkg_data.get('national_number_type'),
            scanned_at=datetime.now(timezone.utc),
            status='active'
        )
        db.session.add(scanned_item)
        db.session.flush()
        
        app.logger.info(f"Created ScannedItem id={scanned_item.id}")
        
        # Create PackageInventory
        inventory_item = PackageInventory(
            scanned_item_id=scanned_item.id,
            current_units=pkg_data['units'],
            original_units=pkg_data.get('package_id') and ProductPackage.query.get(pkg_data['package_id']).quantity or pkg_data['units'],
            status='opened' if pkg_data['status'] == 'opened' else 'sealed',
            medication_id=medication.id  # Link to old medication for reference
        )
        db.session.add(inventory_item)
        db.session.flush()
        
        app.logger.info(f"Created PackageInventory id={inventory_item.id}, units={inventory_item.current_units}")
    
    # Clear old inventory
    if medication.inventory:
        # Log the migration
        log_entry = InventoryLog(
            inventory_id=medication.inventory.id,
            previous_count=medication.inventory.current_count,
            adjustment=-medication.inventory.current_count,
            new_count=0,
            notes=_('Migrated to package-based inventory: %(count)s packages', count=len(scanned_packages))
        )
        db.session.add(log_entry)
        
        # Set inventory to 0
        medication.inventory.current_count = 0
        medication.inventory.last_updated = datetime.now(timezone.utc)
    
    db.session.commit()
    
    # Clear session data
    session.pop(session_key, None)
    session.pop(f'migration_{medication_id}_serials_with_time', None)
    
    flash(_('Successfully migrated %(name)s to package-based inventory!', name=medication.name), 'success')
    
    return jsonify({
        'success': True,
        'redirect': url_for('migration_scanner.select_medication')
    })


@bp.route('/undo-package', methods=['POST'])
def undo_package():
    """Remove the last scanned package from migration."""
    
    data = request.get_json()
    medication_id = data.get('medication_id')
    serial = data.get('serial')
    
    app.logger.info(f"Undo package request - medication_id: {medication_id}, serial: {serial}")
    
    medication = Medication.query.get_or_404(medication_id)
    
    # Remove from packages
    session_key = f'migration_{medication_id}_packages'
    packages = session.get(session_key, [])
    
    app.logger.info(f"Before removal: {len(packages)} packages in session")
    app.logger.info(f"Looking for serial: {serial}")
    
    # Filter out the package with matching serial
    # Handle both real serials and temporary ones (TEMP_0, TEMP_1, etc)
    original_count = len(packages)
    new_packages = []
    
    if serial and serial.startswith('TEMP_'):
        # This is a temporary serial based on index
        try:
            index = int(serial.replace('TEMP_', ''))
            for i, p in enumerate(packages):
                if i != index:
                    new_packages.append(p)
                else:
                    app.logger.info(f"Removing package at index {i} with serial: {p.get('serial')}")
        except ValueError:
            app.logger.error(f"Invalid temporary serial format: {serial}")
            new_packages = packages
    else:
        # Regular serial matching
        for p in packages:
            if p.get('serial') != serial:
                new_packages.append(p)
            else:
                app.logger.info(f"Removing package with serial: {p.get('serial')}")
    
    removed_count = original_count - len(new_packages)
    app.logger.info(f"After removal: {len(new_packages)} packages, removed {removed_count}")
    
    # Delete old key and set new value
    if session_key in session:
        del session[session_key]
    session[session_key] = new_packages
    
    # Remove from serials with timestamp
    if serial:
        serial_key = f'migration_{medication_id}_serials_with_time'
        serials_dict = session.get(serial_key, {})
        if serial in serials_dict:
            del serials_dict[serial]
            session[serial_key] = serials_dict
    
    # Recalculate package statuses after removal
    # If we removed an open package and still have packages left, 
    # we may need to adjust the last package to be open
    original_inventory = medication.inventory.current_count
    total_migrated = sum(p['units'] for p in new_packages)
    
    if total_migrated < original_inventory and new_packages:
        # We have room for more units - check if last package needs adjustment
        remaining = original_inventory - total_migrated
        
        # Find if there's already an open package
        has_open = any(p.get('status') == 'opened' for p in new_packages)
        
        if not has_open:
            # No open package exists, but we have remaining units
            # This can happen if we deleted the open package
            # We should NOT automatically make another package open
            # as the user explicitly removed that package
            app.logger.info(f"No open package after removal, remaining: {remaining}")
    else:
        remaining = max(0, original_inventory - total_migrated)
    
    # Force session save
    session.permanent = True
    session.modified = True
    
    # Verify the session was updated
    verify_packages = session.get(session_key, [])
    app.logger.info(f"Verification - packages in session after save: {len(verify_packages)}")
    app.logger.info(f"Total after removal: {total_migrated}, Remaining: {remaining}")
    
    return jsonify({
        'success': True,
        'remaining_units': remaining,
        'total_scanned': len(new_packages),
        'packages': new_packages  # Return the updated packages list
    })