"""
Routes for managing medication packages with national pharmaceutical numbers and GTINs.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_babel import gettext as _

from models import db, Medication, MedicationPackage
from barcode_validator import identify_barcode_format
from scanner_parser import validate_gtin

bp = Blueprint('medication_packages', __name__, url_prefix='/medications/<int:medication_id>/packages')


@bp.route('/')
def index(medication_id):
    """Redirect to medication details page (packages are shown there now)."""
    return redirect(url_for('medications.show', id=medication_id))


@bp.route('/new')
def new(medication_id):
    """Show form to add a new package."""
    medication = Medication.query.get_or_404(medication_id)
    return render_template(
        'medication_packages/new.html',
        medication=medication
    )


@bp.route('/create', methods=['POST'])
def create(medication_id):
    """Create a new package."""
    medication = Medication.query.get_or_404(medication_id)
    
    package_size = request.form.get('package_size')
    quantity = request.form.get('quantity', type=int)
    national_number = request.form.get('national_number', '').strip()
    gtin = request.form.get('gtin', '').strip()
    
    # Validate inputs
    if not package_size or not quantity:
        flash(_('Package size and quantity are required'), 'error')
        return redirect(url_for('medication_packages.new', medication_id=medication_id))
    
    # Import the parser function
    from scanner_parser import extract_national_number
    
    # Process GTIN first - it can auto-populate national number
    national_number_type = None
    country_code = None
    
    # Validate GTIN if provided
    if gtin:
        if not validate_gtin(gtin):
            flash(_('Invalid GTIN'), 'error')
            return redirect(url_for('medication_packages.new', medication_id=medication_id))
        
        # Try to extract national number from GTIN if not manually provided
        if not national_number:
            national_info = extract_national_number(gtin)
            if national_info:
                national_number = national_info[0]
                national_number_type = national_info[1]
                # Extract country code from type (e.g., 'DE_PZN' -> 'DE')
                country_code = national_info[1].split('_')[0] if '_' in national_info[1] else None
                flash(_('National number automatically extracted from GTIN: %(num)s', num=national_number), 'info')
    
    # If national number was manually provided or not found in GTIN, validate it
    if national_number and not national_number_type:
        # Use the same identify function as the scanner
        barcode_info = identify_barcode_format(national_number)
        
        if barcode_info:
            # Valid recognized format
            validated_number, number_type = barcode_info
            national_number = validated_number  # Use the validated version
            national_number_type = number_type
            # Extract country code from type (e.g., 'DE_PZN' -> 'DE')
            country_code = number_type.split('_')[0] if '_' in number_type else 'UNKNOWN'
        else:
            # Unknown format, save as custom
            national_number_type = 'CUSTOM'
            country_code = 'UNKNOWN'
    
    # Check for duplicate
    existing = MedicationPackage.query.filter_by(
        medication_id=medication_id,
        package_size=package_size
    ).first()
    
    if existing:
        flash(_('Package size already exists for this medication'), 'error')
        return redirect(url_for('medication_packages.new', medication_id=medication_id))
    
    # Create package
    package = MedicationPackage(
        medication_id=medication_id,
        package_size=package_size,
        quantity=quantity,
        national_number=national_number if national_number else None,
        national_number_type=national_number_type,
        gtin=gtin if gtin else None,
        country_code=country_code
    )
    
    db.session.add(package)
    db.session.commit()
    
    flash(_('Package added successfully'), 'success')
    return redirect(url_for('medications.show', id=medication_id))


@bp.route('/<int:package_id>/edit')
def edit(medication_id, package_id):
    """Show form to edit a package."""
    medication = Medication.query.get_or_404(medication_id)
    package = MedicationPackage.query.get_or_404(package_id)
    
    if package.medication_id != medication_id:
        flash(_('Package does not belong to this medication'), 'error')
        return redirect(url_for('medication_packages.index', medication_id=medication_id))
    
    return render_template(
        'medication_packages/edit.html',
        medication=medication,
        package=package
    )


@bp.route('/<int:package_id>/update', methods=['POST'])
def update(medication_id, package_id):
    """Update a package."""
    medication = Medication.query.get_or_404(medication_id)
    package = MedicationPackage.query.get_or_404(package_id)
    
    if package.medication_id != medication_id:
        flash(_('Package does not belong to this medication'), 'error')
        return redirect(url_for('medication_packages.index', medication_id=medication_id))
    
    package.quantity = request.form.get('quantity', type=int)
    national_number = request.form.get('national_number', '').strip()
    gtin = request.form.get('gtin', '').strip()
    
    # Import the parser function
    from scanner_parser import extract_national_number
    
    # Process GTIN first - it can auto-populate national number
    # Validate and update GTIN
    if gtin:
        if not validate_gtin(gtin):
            flash(_('Invalid GTIN'), 'error')
            return redirect(url_for('medication_packages.edit', 
                                  medication_id=medication_id, 
                                  package_id=package_id))
        package.gtin = gtin
        
        # Try to extract national number from GTIN if not manually provided
        if not national_number:
            national_info = extract_national_number(gtin)
            if national_info:
                national_number = national_info[0]
                package.national_number = national_number
                package.national_number_type = national_info[1]
                # Extract country code from type (e.g., 'DE_PZN' -> 'DE')
                package.country_code = national_info[1].split('_')[0] if '_' in national_info[1] else None
                flash(_('National number automatically extracted from GTIN: %(num)s', num=national_number), 'info')
    else:
        package.gtin = None
    
    # If national number was manually provided, validate and save it
    if national_number:
        # Only detect type if not already set from GTIN
        if not package.national_number_type or package.gtin != gtin:
            # Use the same identify function as the scanner
            barcode_info = identify_barcode_format(national_number)
            
            if barcode_info:
                # Valid recognized format
                validated_number, number_type = barcode_info
                package.national_number = validated_number
                package.national_number_type = number_type
                package.country_code = number_type.split('_')[0] if '_' in number_type else 'UNKNOWN'
            elif len(national_number) == 7 and national_number.isdigit():
                # Could be Belgian CNK or other 7-digit codes
                package.national_number_type = 'UNKNOWN_7'
                package.country_code = 'UNKNOWN'
            else:
                # Unknown format, save as is
                package.national_number_type = 'CUSTOM'
                package.country_code = 'UNKNOWN'
        package.national_number = national_number
    elif not gtin:
        # Only clear if both are empty
        package.national_number = None
        package.national_number_type = None
        package.country_code = None
    
    db.session.commit()
    
    flash(_('Package updated successfully'), 'success')
    return redirect(url_for('medications.show', id=medication_id))


@bp.route('/<int:package_id>/delete', methods=['POST'])
def delete(medication_id, package_id):
    """Delete a package."""
    package = MedicationPackage.query.get_or_404(package_id)
    
    if package.medication_id != medication_id:
        flash(_('Package does not belong to this medication'), 'error')
        return redirect(url_for('medication_packages.index', medication_id=medication_id))
    
    # Check if there are scanned items using this package
    if package.scanned_items:
        flash(_('Cannot delete package with scanned items'), 'error')
        return redirect(url_for('medication_packages.index', medication_id=medication_id))
    
    db.session.delete(package)
    db.session.commit()
    
    flash(_('Package deleted successfully'), 'success')
    return redirect(url_for('medications.show', id=medication_id))