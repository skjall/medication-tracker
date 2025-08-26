"""
Package onboarding routes for unknown scanned packages.
"""

from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_babel import gettext as _

from models import (
    db, 
    ActiveIngredient, 
    MedicationProduct, 
    ProductPackage,
    Physician,
    ScannedItem,
    PackageInventory
)

bp = Blueprint('package_onboarding', __name__, url_prefix='/onboarding')


@bp.route('/package', methods=['GET', 'POST'])
def onboard_package():
    """Onboard an unknown package by creating ingredient, product, and package."""
    
    # Get scanned data from session or query params
    scanned_data = {
        'gtin': request.args.get('gtin') or session.get('scanned_gtin'),
        'national_number': request.args.get('national_number') or session.get('scanned_national_number'),
        'national_number_type': request.args.get('national_number_type') or session.get('scanned_national_number_type'),
        'batch': request.args.get('batch') or session.get('scanned_batch'),
        'expiry': request.args.get('expiry') or session.get('scanned_expiry'),
        'serial': request.args.get('serial') or session.get('scanned_serial'),
    }
    
    # Store in session for form resubmission
    for key, value in scanned_data.items():
        if value:
            session[f'scanned_{key}'] = value
    
    if request.method == 'POST':
        # Process form submission
        step = request.form.get('step', '1')
        
        if step == '1':
            # Step 1: Active Ingredient
            ingredient_option = request.form.get('ingredient_option')  # 'existing' or 'new'
            
            if ingredient_option == 'existing':
                ingredient_id = request.form.get('ingredient_id')
                if not ingredient_id:
                    flash(_('Please select an active ingredient'), 'error')
                    return redirect(url_for('package_onboarding.onboard_package'))
                ingredient = ActiveIngredient.query.get_or_404(ingredient_id)
            else:
                # Create new ingredient
                ingredient_name = request.form.get('ingredient_name', '').strip()
                if not ingredient_name:
                    flash(_('Please enter an active ingredient name'), 'error')
                    return redirect(url_for('package_onboarding.onboard_package'))
                
                # Check if ingredient already exists
                existing = ActiveIngredient.query.filter_by(name=ingredient_name).first()
                if existing:
                    ingredient = existing
                    flash(_('Active ingredient already exists, using existing one'), 'info')
                else:
                    ingredient = ActiveIngredient(
                        name=ingredient_name,
                        strength=request.form.get('ingredient_strength'),
                        unit=request.form.get('ingredient_unit')
                    )
                    db.session.add(ingredient)
                    db.session.flush()
            
            # Store ingredient ID in session
            session['onboarding_ingredient_id'] = ingredient.id
            
        # Step 2: Product
        product_option = request.form.get('product_option')  # 'existing' or 'new'
        ingredient_id = session.get('onboarding_ingredient_id')
        
        if not ingredient_id:
            flash(_('Please complete step 1 first'), 'error')
            return redirect(url_for('package_onboarding.onboard_package'))
        
        ingredient = ActiveIngredient.query.get_or_404(ingredient_id)
        
        if product_option == 'existing':
            product_id = request.form.get('product_id')
            if not product_id:
                flash(_('Please select a product'), 'error')
                return redirect(url_for('package_onboarding.onboard_package'))
            product = MedicationProduct.query.get_or_404(product_id)
        else:
            # Create new product
            brand_name = request.form.get('brand_name', '').strip()
            if not brand_name:
                flash(_('Please enter a product name'), 'error')
                return redirect(url_for('package_onboarding.onboard_package'))
            
            # Check if product already exists for this ingredient
            existing = MedicationProduct.query.filter_by(
                active_ingredient_id=ingredient.id,
                brand_name=brand_name
            ).first()
            
            if existing:
                product = existing
                flash(_('Product already exists, using existing one'), 'info')
            else:
                # Handle order settings
                is_otc = request.form.get('is_otc') == 'on'
                physician_id = None if is_otc else request.form.get('physician_id')
                
                product = MedicationProduct(
                    active_ingredient_id=ingredient.id,
                    brand_name=brand_name,
                    manufacturer=request.form.get('manufacturer'),
                    is_otc=is_otc,
                    physician_id=physician_id,
                    aut_idem=request.form.get('aut_idem') == 'on'
                )
                db.session.add(product)
                db.session.flush()
                
                # Set as default if it's the first product for this ingredient
                if not ingredient.default_product_id:
                    ingredient.default_product_id = product.id
                    db.session.flush()
        
        # Step 3: Package
        package_size = request.form.get('package_size', '').strip()
        quantity = request.form.get('quantity', type=int)
        
        if not package_size or not quantity:
            flash(_('Please enter package size and quantity'), 'error')
            return redirect(url_for('package_onboarding.onboard_package'))
        
        # Check if package already exists
        existing_package = ProductPackage.query.filter_by(
            product_id=product.id,
            package_size=package_size
        ).first()
        
        if existing_package:
            # Update existing package with scanned data
            package = existing_package
            if scanned_data['gtin'] and not package.gtin:
                package.gtin = scanned_data['gtin']
            if scanned_data['national_number'] and not package.national_number:
                package.national_number = scanned_data['national_number']
                package.national_number_type = scanned_data['national_number_type']
            flash(_('Package configuration updated'), 'info')
        else:
            # Create new package
            package = ProductPackage(
                product_id=product.id,
                package_size=package_size,
                quantity=quantity,
                gtin=scanned_data['gtin'],
                national_number=scanned_data['national_number'],
                national_number_type=scanned_data['national_number_type'],
                manufacturer=request.form.get('package_manufacturer'),
                list_price=request.form.get('list_price', type=float),
                is_active=True
            )
            db.session.add(package)
            db.session.flush()  # Need package ID for inventory
        
        # Step 4: Add to inventory
        add_to_inventory = request.form.get('add_to_inventory') == 'on'
        if add_to_inventory:
            # Create or update ScannedItem for this package
            scanned_item = ScannedItem.query.filter_by(
                serial_number=scanned_data.get('serial', f"{scanned_data['gtin']}_{scanned_data['batch']}_{datetime.now(timezone.utc).timestamp()}")
            ).first()
            
            if not scanned_item:
                scanned_item = ScannedItem(
                    serial_number=scanned_data.get('serial') or f"{scanned_data['gtin']}_{scanned_data['batch']}_{datetime.now(timezone.utc).timestamp()}",
                    gtin=scanned_data['gtin'],
                    batch_number=scanned_data['batch'],
                    expiry_date=datetime.fromisoformat(scanned_data['expiry']) if scanned_data.get('expiry') else None,
                    national_number=scanned_data['national_number'],
                    national_number_type=scanned_data['national_number_type'],
                    # Note: medication_package_id is for old system, leaving null for new ProductPackage
                    scanned_at=datetime.now(timezone.utc),
                    status='active'
                )
                db.session.add(scanned_item)
                db.session.flush()
            
            # Create PackageInventory entry for the new package
            inventory_item = PackageInventory(
                scanned_item_id=scanned_item.id,
                current_units=package.quantity,
                original_units=package.quantity,
                status='sealed'
            )
            db.session.add(inventory_item)
        
        db.session.commit()
        
        # Clear session data
        for key in list(session.keys()):
            if key.startswith('scanned_') or key.startswith('onboarding_'):
                session.pop(key)
        
        flash(_('Package successfully onboarded!'), 'success')
        
        # Return to scanner
        return redirect(url_for('scanner.scan', success=1, package_id=package.id))
    
    # GET request - show form
    # Get all active ingredients for dropdown
    ingredients = ActiveIngredient.query.order_by(ActiveIngredient.name).all()
    
    # Get all physicians for order settings
    physicians = Physician.query.order_by(Physician.name).all()
    
    # If we have an ingredient selected in session, get its products
    products = []
    selected_ingredient_id = session.get('onboarding_ingredient_id')
    if selected_ingredient_id:
        selected_ingredient = ActiveIngredient.query.get(selected_ingredient_id)
        if selected_ingredient:
            products = selected_ingredient.products
    
    return render_template(
        'package_onboarding/onboard.html',
        scanned_data=scanned_data,
        ingredients=ingredients,
        products=products,
        physicians=physicians,
        selected_ingredient_id=selected_ingredient_id
    )


@bp.route('/api/ingredient/<int:ingredient_id>/products')
def get_ingredient_products(ingredient_id):
    """API endpoint to get products for a selected ingredient."""
    ingredient = ActiveIngredient.query.get_or_404(ingredient_id)
    products = []
    
    for product in ingredient.products:
        products.append({
            'id': product.id,
            'name': product.display_name,
            'manufacturer': product.manufacturer,
            'is_default': product.id == ingredient.default_product_id
        })
    
    return jsonify({'products': products})


@bp.route('/api/search/ingredients')
def search_ingredients():
    """API endpoint to search for ingredients."""
    query = request.args.get('q', '').strip()
    if not query or len(query) < 2:
        return jsonify({'ingredients': []})
    
    ingredients = ActiveIngredient.query.filter(
        ActiveIngredient.name.ilike(f'%{query}%')
    ).limit(10).all()
    
    results = []
    for ing in ingredients:
        results.append({
            'id': ing.id,
            'name': ing.name,
            'strength': ing.strength,
            'unit': ing.strength_unit,
            'display': f"{ing.name} {ing.strength}{ing.strength_unit}" if ing.strength else ing.name
        })
    
    return jsonify({'ingredients': results})