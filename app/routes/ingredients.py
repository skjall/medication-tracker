"""
Routes for active ingredient and product management.
"""

import logging
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    jsonify,
)
from urllib.parse import urlparse
from flask_babel import gettext as _

from models import (
    db,
    ActiveIngredient,
    MedicationProduct,
    ProductPackage,
)
from utils import to_local_timezone
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

ingredients_bp = Blueprint("ingredients", __name__, url_prefix="/ingredients")


def validate_strength(value):
    """Validate and clean strength value to ensure it's numeric.

    Args:
        value: The strength value to validate (can be string, number, etc.)

    Returns:
        float: Cleaned numeric value, or None if invalid/empty
    """
    if not value:
        return None

    # Convert to string and strip whitespace
    str_value = str(value).strip()

    if not str_value:
        return None

    # Replace comma with dot for decimal separator (German format)
    str_value = str_value.replace(",", ".")

    # Validate it's a proper number
    import re

    # Match optional minus, digits, optional decimal point and more digits
    if re.match(r"^-?\d+(\.\d+)?$", str_value):
        return float(str_value)

    # Try to extract just the numeric part (e.g., "400mg" -> "400")
    match = re.match(r"^(-?\d+(?:\.\d+)?)", str_value)
    if match:
        return float(match.group(1))

    return None


@ingredients_bp.route("/")
def index():
    """Display all active ingredients with their products."""
    ingredients = ActiveIngredient.query.order_by(ActiveIngredient.name).all()

    # Get counts for each ingredient and ensure defaults are set
    ingredient_stats = []
    needs_commit = False
    for ingredient in ingredients:
        products = MedicationProduct.query.filter_by(
            active_ingredient_id=ingredient.id
        ).all()

        # Auto-set default if products exist but no default is set
        if products and not ingredient.default_product_id:
            ingredient.default_product_id = products[0].id
            needs_commit = True

        total_inventory = sum(p.total_inventory_count for p in products)
        ingredient_stats.append(
            {
                "ingredient": ingredient,
                "product_count": len(products),
                "total_inventory": total_inventory,
                "products": products,
            }
        )

    # Commit any default product updates
    if needs_commit:
        db.session.commit()

    return render_template(
        "ingredients/index.html",
        ingredient_stats=ingredient_stats,
        local_time=to_local_timezone(datetime.now(timezone.utc)),
    )


@ingredients_bp.route("/<int:id>")
def show(id: int):
    """Show details for a specific active ingredient."""
    ingredient = ActiveIngredient.query.get_or_404(id)
    products = MedicationProduct.query.filter_by(active_ingredient_id=id).all()

    # Ensure default is set if products exist but no default
    if products and not ingredient.default_product_id:
        ingredient.default_product_id = products[0].id
        db.session.commit()

    # Calculate total inventory across all products
    total_inventory = sum(p.total_inventory_count for p in products)

    # Find substitutable products
    substitutable = []
    for product in products:
        if product.aut_idem:
            substitutable.append(product)

    return render_template(
        "ingredients/show.html",
        ingredient=ingredient,
        products=products,
        total_inventory=total_inventory,
        substitutable=substitutable,
        local_time=to_local_timezone(datetime.now(timezone.utc)),
    )


@ingredients_bp.route("/products/<int:id>")
def show_product(id: int):
    """Show details for a specific medication product."""
    product = MedicationProduct.query.get_or_404(id)

    # Get substitutes
    substitutes = product.find_substitutes() if product.can_substitute else []

    # Get package inventory for this product
    from models import PackageInventory, ScannedItem, ProductPackage, InventoryLog
    from sqlalchemy import or_, and_, desc
    
    # Get all packages for this product
    packages = ProductPackage.query.filter_by(product_id=product.id).all()
    package_gtins = [p.gtin for p in packages if p.gtin]
    package_numbers = [(p.national_number, p.national_number_type) 
                      for p in packages if p.national_number]
    
    from flask import current_app
    current_app.logger.info(f"Product {product.id} packages: GTINs={package_gtins}, Numbers={package_numbers}")
    for pkg in packages:
        current_app.logger.info(f"Package {pkg.id}: size={pkg.package_size}, gtin={pkg.gtin}, nat_num={pkg.national_number}, nat_type={pkg.national_number_type}")
    
    package_inventory = []
    if package_gtins or package_numbers:
        # Build query for inventory packages
        query = (
            db.session.query(PackageInventory, ScannedItem, ProductPackage)
            .join(ScannedItem, PackageInventory.scanned_item_id == ScannedItem.id)
            .outerjoin(ProductPackage, 
                      or_(
                          (ProductPackage.gtin == ScannedItem.gtin),
                          ((ProductPackage.national_number == ScannedItem.national_number) & 
                           (ProductPackage.national_number_type == ScannedItem.national_number_type))
                      ))
            .filter(PackageInventory.status.in_(["sealed", "opened"]))
        )
        
        # Build OR conditions for GTIN and national numbers
        conditions = []
        if package_gtins:
            conditions.append(ScannedItem.gtin.in_(package_gtins))
        if package_numbers:
            for nat_num, nat_type in package_numbers:
                current_app.logger.info(f"Adding condition: national_number={nat_num}, type={nat_type}")
                if nat_type:
                    conditions.append((ScannedItem.national_number == nat_num) & 
                                    (ScannedItem.national_number_type == nat_type))
                else:
                    conditions.append(ScannedItem.national_number == nat_num)
        
        if conditions:
            current_app.logger.info(f"Filtering with {len(conditions)} conditions")
            query = query.filter(or_(*conditions))
            package_inventory = query.order_by(ScannedItem.expiry_date.asc()).all()
            current_app.logger.info(f"Found {len(package_inventory)} inventory items")
            for inv, item, pkg in package_inventory:
                current_app.logger.info(f"Inventory: id={inv.id}, current={inv.current_units}, original={inv.original_units}, status={inv.status}")
                current_app.logger.info(f"  ScannedItem: id={item.id}, gtin={item.gtin}, nat_num={item.national_number}, nat_type={item.national_number_type}")

    # Get inventory change logs for ALL packages (including consumed ones)
    from models import ProductPackage
    
    # Get ALL package inventory IDs for this product (regardless of status)
    all_package_inv_query = (
        db.session.query(PackageInventory, ScannedItem, ProductPackage)
        .join(ScannedItem, PackageInventory.scanned_item_id == ScannedItem.id)
        .join(ProductPackage, or_(
            ScannedItem.gtin == ProductPackage.gtin,
            and_(
                ScannedItem.national_number == ProductPackage.national_number,
                ScannedItem.national_number_type == ProductPackage.national_number_type
            )
        ))
        .filter(ProductPackage.product_id == product.id)
    )
    
    all_package_inventory = all_package_inv_query.all()
    inventory_logs = []
    
    if all_package_inventory:
        # Get ALL package inventory IDs (including consumed packages)
        all_package_inv_ids = [inv[0].id for inv in all_package_inventory]
        
        # Query inventory logs for ALL these packages
        inventory_logs = (
            InventoryLog.query
            .filter(InventoryLog.package_inventory_id.in_(all_package_inv_ids))
            .order_by(desc(InventoryLog.changed_at))
            .limit(50)  # Show last 50 changes
            .all()
        )

    return render_template(
        "ingredients/show_product.html",
        product=product,
        substitutes=substitutes,
        package_inventory=package_inventory,
        inventory_logs=inventory_logs,
        local_time=to_local_timezone(datetime.now(timezone.utc)),
    )


@ingredients_bp.route("/<int:id>/edit", methods=["GET", "POST"])
def edit(id: int):
    """Edit an active ingredient."""
    ingredient = ActiveIngredient.query.get_or_404(id)
    
    # Get return URL from query params or form
    return_url = request.args.get('return_url') or request.form.get('return_url')

    if request.method == "POST":
        ingredient.name = request.form.get("name", "").strip()

        ingredient.form = request.form.get("form", "").strip() or None
        ingredient.atc_code = request.form.get("atc_code", "").strip() or None
        ingredient.notes = request.form.get("notes", "").strip() or None
        
        # Handle components
        from models import IngredientComponent
        
        # Clear existing components
        IngredientComponent.query.filter_by(active_ingredient_id=ingredient.id).delete()
        
        # Process components from the complex form names
        components_data = {}
        for key in request.form:
            if key.startswith('components[') and '][' in key:
                # Parse component[index][field] format
                import re
                match = re.match(r'components\[(\d+)\]\[(\w+)\]', key)
                if match:
                    index, field = match.groups()
                    index = int(index)
                    if index not in components_data:
                        components_data[index] = {}
                    components_data[index][field] = request.form[key].strip()
        
        # Create new components
        for index in sorted(components_data.keys()):
            comp_data = components_data[index]
            if comp_data.get('component_name') and comp_data.get('strength') and comp_data.get('strength_unit'):
                # Validate strength
                raw_strength = comp_data['strength']
                validated_strength = validate_strength(raw_strength)
                if not validated_strength:
                    flash(
                        _("Invalid strength value in component %(name)s: %(value)s", 
                          name=comp_data['component_name'], 
                          value=raw_strength),
                        "error"
                    )
                    return render_template(
                        "ingredients/edit.html",
                        ingredient=ingredient,
                        return_url=return_url,
                        local_time=to_local_timezone(datetime.now(timezone.utc)),
                    )
                
                component = IngredientComponent(
                    active_ingredient_id=ingredient.id,
                    component_name=comp_data['component_name'],
                    strength=validated_strength,
                    strength_unit=comp_data['strength_unit'],
                    sort_order=int(comp_data.get('sort_order', index + 1))
                )
                db.session.add(component)

        db.session.commit()
        flash(_("Active ingredient updated successfully"), "success")
        
        # Redirect to return_url if provided, otherwise to ingredient show page
        if return_url:
            # Validate return_url to avoid open redirect vulnerabilities
            sanitized_url = return_url.replace("\\", "")
            parsed = urlparse(sanitized_url)
            # Only allow relative URLs (no scheme and no netloc)
            if not parsed.scheme and not parsed.netloc:
                return redirect(sanitized_url)
        return redirect(url_for("ingredients.show", id=ingredient.id))

    return render_template(
        "ingredients/edit.html",
        ingredient=ingredient,
        return_url=return_url,
        local_time=to_local_timezone(datetime.now(timezone.utc)),
    )


@ingredients_bp.route("/<int:id>/delete", methods=["POST"])
def delete(id: int):
    """Delete an active ingredient."""
    ingredient = ActiveIngredient.query.get_or_404(id)

    # Check if there are products using this ingredient
    product_count = MedicationProduct.query.filter_by(
        active_ingredient_id=id
    ).count()
    if product_count > 0:
        flash(
            _(
                "Cannot delete active ingredient with existing products. Please delete all products first."
            ),
            "error",
        )
        return redirect(url_for("ingredients.show", id=id))

    db.session.delete(ingredient)
    db.session.commit()

    flash(_("Active ingredient deleted successfully"), "success")
    return redirect(url_for("ingredients.index"))


@ingredients_bp.route("/products/<int:id>/edit", methods=["GET", "POST"])
def edit_product(id: int):
    """Edit a medication product."""
    product = MedicationProduct.query.get_or_404(id)

    if request.method == "POST":
        # Update product details
        product.brand_name = request.form.get("brand_name", product.brand_name)
        product.manufacturer = request.form.get(
            "manufacturer", product.manufacturer
        )
        product.aut_idem = request.form.get("aut_idem") == "on"
        product.notes = request.form.get("notes", "").strip() or None

        # Update order settings
        product.is_otc = request.form.get("is_otc") == "on"
        physician_id = request.form.get("physician_id")
        if physician_id:
            product.physician_id = int(physician_id)
        else:
            product.physician_id = None

        db.session.commit()
        flash(_("Product updated successfully"), "success")
        return redirect(url_for("ingredients.show_product", id=product.id))

    # GET request - load physicians for the form
    from models import Physician

    physicians = Physician.query.order_by(Physician.name).all()

    return render_template(
        "ingredients/edit_product.html",
        product=product,
        physicians=physicians,
        local_time=to_local_timezone(datetime.now(timezone.utc)),
    )


@ingredients_bp.route("/products/<int:id>/delete", methods=["POST"])
def delete_product(id: int):
    """Delete a medication product."""
    product = MedicationProduct.query.get_or_404(id)
    ingredient_id = product.active_ingredient_id
    ingredient = ActiveIngredient.query.get(ingredient_id)


    # Check if this is the default product
    was_default = ingredient.default_product_id == id

    db.session.delete(product)
    db.session.flush()

    # If this was the default, set a new default
    if was_default:
        remaining_products = MedicationProduct.query.filter_by(
            active_ingredient_id=ingredient_id
        ).first()
        if remaining_products:
            ingredient.default_product_id = remaining_products.id
            flash(
                _(
                    "Default product updated to %(name)s",
                    name=remaining_products.brand_name,
                ),
                "info",
            )
        else:
            ingredient.default_product_id = None

    db.session.commit()

    flash(_("Product deleted successfully"), "success")
    return redirect(url_for("ingredients.show", id=ingredient_id))


@ingredients_bp.route("/products/new", methods=["GET", "POST"])
def new_product():
    """Create a new medication product."""
    # Get the referring ingredient ID if provided
    from_ingredient_id = request.args.get("ingredient_id", type=int)

    if request.method == "POST":
        # Get or create active ingredient
        ingredient_name = request.form.get("ingredient_name", "").strip()
        ingredient_id = request.form.get("ingredient_id", "").strip()

        # Check if it's a new ingredient (starts with "new:")
        if ingredient_id.startswith("new:"):
            # Extract the ingredient name from the tag
            ingredient_name = ingredient_id[4:]  # Remove "new:" prefix

            # Validate and clean strength value
            raw_strength = request.form.get("strength", "").strip()
            strength = validate_strength(raw_strength)
            if raw_strength and not strength:
                flash(
                    _(
                        "Invalid strength value. Please enter a valid number (e.g., 500 or 1.25)"
                    ),
                    "error",
                )
                return redirect(url_for("ingredients.new_product"))

            strength_unit = (
                request.form.get("strength_unit", "").strip() or None
            )
            form = request.form.get("form", "").strip() or None

            # Check if it already exists with same name, strength, and form
            existing_query = ActiveIngredient.query.filter_by(
                name=ingredient_name
            )
            if strength:
                existing_query = existing_query.filter_by(
                    strength=strength, strength_unit=strength_unit
                )
            if form:
                existing_query = existing_query.filter_by(form=form)

            ingredient = existing_query.first()
            if not ingredient:
                ingredient = ActiveIngredient(
                    name=ingredient_name,
                    strength=strength,
                    strength_unit=strength_unit,
                    form=form,
                )
                db.session.add(ingredient)
                db.session.flush()
        elif ingredient_id:
            # Existing ingredient selected
            ingredient = ActiveIngredient.query.get(ingredient_id)
        elif ingredient_name:
            # New ingredient name provided directly (fallback)
            raw_strength = request.form.get("strength", "").strip()
            strength = validate_strength(raw_strength)
            if raw_strength and not strength:
                flash(
                    _(
                        "Invalid strength value. Please enter a valid number (e.g., 500 or 1.25)"
                    ),
                    "error",
                )
                return redirect(url_for("ingredients.new_product"))

            ingredient = ActiveIngredient(
                name=ingredient_name,
                strength=strength,
                strength_unit=request.form.get("strength_unit", "").strip()
                or None,
                form=request.form.get("form", "").strip() or None,
            )
            db.session.add(ingredient)
            db.session.flush()
        else:
            flash(_("Please select or enter an active ingredient"), "error")
            return redirect(url_for("ingredients.new_product"))

        # Create product
        product = MedicationProduct(
            active_ingredient_id=ingredient.id,
            brand_name=request.form.get("brand_name"),
            manufacturer=request.form.get("manufacturer", "").strip()
            or "Unknown",
            aut_idem=request.form.get("aut_idem") == "on",
            notes=request.form.get("notes", "").strip() or None,
        )

        # Set physician if specified
        physician_id = request.form.get("physician_id")
        if physician_id:
            product.physician_id = int(physician_id)

        product.is_otc = request.form.get("is_otc") == "on"

        db.session.add(product)
        db.session.flush()  # Get the product ID

        # If this is the first product for the ingredient, set it as default
        if not ingredient.default_product_id:
            ingredient.default_product_id = product.id

        db.session.commit()

        flash(_("Product created successfully"), "success")

        # Return to the ingredient page if we came from there
        return_to_ingredient = request.form.get("return_to_ingredient")
        if return_to_ingredient:
            return redirect(
                url_for("ingredients.show", id=return_to_ingredient)
            )
        return redirect(url_for("ingredients.show_product", id=product.id))

    # GET request
    from models import Physician

    physicians = Physician.query.order_by(Physician.name).all()
    ingredients = ActiveIngredient.query.order_by(ActiveIngredient.name).all()

    # Pre-select ingredient if coming from ingredient page
    selected_ingredient = None
    if from_ingredient_id:
        selected_ingredient = ActiveIngredient.query.get(from_ingredient_id)

    return render_template(
        "ingredients/new_product.html",
        physicians=physicians,
        ingredients=ingredients,
        selected_ingredient=selected_ingredient,
        from_ingredient_id=from_ingredient_id,
        local_time=to_local_timezone(datetime.now(timezone.utc)),
    )


@ingredients_bp.route("/api/search")
def api_search():
    """API endpoint to search for ingredients."""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify([])

    ingredients = (
        ActiveIngredient.query.filter(
            ActiveIngredient.name.ilike(f"%{query}%")
        )
        .limit(10)
        .all()
    )

    results = []
    for ingredient in ingredients:
        results.append(
            {
                "id": ingredient.id,
                "name": ingredient.name,
                "form": ingredient.form,
                "full_name": ingredient.full_name,
            }
        )

    return jsonify(results)


@ingredients_bp.route("/products/<int:id>/packages")
def product_packages(id: int):
    """List all packages for a product."""
    product = MedicationProduct.query.get_or_404(id)
    packages = (
        ProductPackage.query.filter_by(product_id=id)
        .order_by(ProductPackage.package_size)
        .all()
    )

    return render_template(
        "ingredients/packages.html",
        product=product,
        packages=packages,
        local_time=to_local_timezone(datetime.now(timezone.utc)),
    )


@ingredients_bp.route(
    "/products/<int:id>/packages/new", methods=["GET", "POST"]
)
def new_package(id: int):
    """Add a new package to a product."""
    product = MedicationProduct.query.get_or_404(id)

    if request.method == "POST":
        package = ProductPackage(
            product_id=id,
            package_size=request.form.get("package_size", "").strip(),
            quantity=int(request.form.get("quantity", 0)),
            gtin=request.form.get("gtin", "").strip() or None,
            national_number=request.form.get("national_number", "").strip()
            or None,
            national_number_type=request.form.get(
                "national_number_type", ""
            ).strip()
            or None,
            manufacturer=request.form.get("manufacturer", "").strip() or None,
            list_price=float(request.form.get("list_price") or 0) or None,
            exclude_from_ordering="exclude_from_ordering" in request.form,
        )

        db.session.add(package)
        db.session.commit()

        flash(_("Package added successfully"), "success")
        return redirect(url_for("ingredients.show_product", id=product.id))

    return render_template(
        "ingredients/new_package.html",
        product=product,
        local_time=to_local_timezone(datetime.now(timezone.utc)),
    )


@ingredients_bp.route("/packages/<int:id>/edit", methods=["GET", "POST"])
def edit_package(id: int):
    """Edit a product package."""
    package = ProductPackage.query.get_or_404(id)

    if request.method == "POST":
        package.package_size = request.form.get("package_size", "").strip()
        package.quantity = int(request.form.get("quantity", 0))
        package.gtin = request.form.get("gtin", "").strip() or None
        package.national_number = (
            request.form.get("national_number", "").strip() or None
        )
        package.national_number_type = (
            request.form.get("national_number_type", "").strip() or None
        )
        package.manufacturer = (
            request.form.get("manufacturer", "").strip() or None
        )
        package.list_price = float(request.form.get("list_price") or 0) or None
        package.exclude_from_ordering = "exclude_from_ordering" in request.form

        db.session.commit()
        flash(_("Package updated successfully"), "success")
        return redirect(
            url_for("ingredients.show_product", id=package.product_id)
        )

    return render_template(
        "ingredients/edit_package.html",
        package=package,
        local_time=to_local_timezone(datetime.now(timezone.utc)),
    )


@ingredients_bp.route("/packages/<int:id>/delete", methods=["POST"])
def delete_package(id: int):
    """Delete a product package."""
    package = ProductPackage.query.get_or_404(id)
    product_id = package.product_id

    db.session.delete(package)
    db.session.commit()

    flash(_("Package deleted successfully"), "success")
    return redirect(url_for("ingredients.show_product", id=product_id))


@ingredients_bp.route("/inventory/<int:id>/edit", methods=["GET", "POST"])
def edit_package_inventory(id: int):
    """Edit package inventory details."""
    from models import PackageInventory, ScannedItem
    
    package_inventory = PackageInventory.query.get_or_404(id)
    scanned_item = package_inventory.scanned_item
    
    if request.method == "POST":
        # Update inventory details
        if "current_units" in request.form:
            new_units = int(request.form["current_units"])
            if 0 <= new_units <= package_inventory.original_units:
                package_inventory.current_units = new_units
        
        if "status" in request.form:
            package_inventory.status = request.form["status"]
        
        # Update scanned item details
        if "serial_number" in request.form:
            scanned_item.serial_number = request.form["serial_number"].strip()
        
        if "batch_number" in request.form:
            batch = request.form["batch_number"].strip()
            scanned_item.batch_number = batch if batch else None
        
        if "expiry_date" in request.form:
            expiry = request.form["expiry_date"].strip()
            if expiry:
                from datetime import datetime
                try:
                    scanned_item.expiry_date = datetime.strptime(expiry, '%Y-%m-%d').date()
                except ValueError:
                    scanned_item.expiry_date = None
            else:
                scanned_item.expiry_date = None
        
        db.session.commit()
        flash(_("Package inventory updated successfully"), "success")
        
        # Find product to redirect back to
        product = None
        if scanned_item.gtin:
            package_config = ProductPackage.query.filter_by(gtin=scanned_item.gtin).first()
            if package_config:
                product = package_config.product
        
        if product:
            return redirect(url_for("ingredients.show_product", id=product.id))
        else:
            return redirect(url_for("ingredients.index"))
    
    return render_template(
        "ingredients/edit_package_inventory.html",
        package_inventory=package_inventory,
        scanned_item=scanned_item
    )


@ingredients_bp.route(
    "/<int:ingredient_id>/set-default-product/<int:product_id>",
    methods=["POST"],
)
def set_default_product(ingredient_id: int, product_id: int):
    """Set a product as the default for an ingredient."""
    ingredient = ActiveIngredient.query.get_or_404(ingredient_id)
    product = MedicationProduct.query.get_or_404(product_id)

    # Verify the product belongs to this ingredient
    if product.active_ingredient_id != ingredient_id:
        flash(_("Product does not belong to this ingredient"), "error")
        return redirect(url_for("ingredients.show", id=ingredient_id))

    # Set as default
    ingredient.default_product_id = product_id
    db.session.commit()

    flash(_("Default product set successfully"), "success")
    return redirect(url_for("ingredients.show", id=ingredient_id))


@ingredients_bp.route(
    "/<int:ingredient_id>/clear-default-product", methods=["POST"]
)
def clear_default_product(ingredient_id: int):
    """Clear the default product for an ingredient."""
    ingredient = ActiveIngredient.query.get_or_404(ingredient_id)

    ingredient.default_product_id = None
    db.session.commit()

    flash(_("Default product cleared"), "success")
    return redirect(url_for("ingredients.show", id=ingredient_id))


@ingredients_bp.route("/inventory/<int:id>/delete", methods=["POST"])
def delete_package_inventory(id: int):
    """Delete a package from inventory."""
    from models import PackageInventory, ScannedItem, ProductPackage, InventoryLog
    
    package_inventory = PackageInventory.query.get_or_404(id)
    scanned_item = package_inventory.scanned_item
    
    # Find the product for redirect
    product = None
    if scanned_item.gtin:
        package_config = ProductPackage.query.filter_by(gtin=scanned_item.gtin).first()
        if package_config:
            product = package_config.product
    
    if not product and scanned_item.national_number:
        package_config = ProductPackage.query.filter_by(
            national_number=scanned_item.national_number,
            national_number_type=scanned_item.national_number_type
        ).first()
        if package_config:
            product = package_config.product
    
    # Delete the package inventory and scanned item
    # Note: The cascade relationship will automatically delete related inventory_logs
    db.session.delete(package_inventory)
    db.session.delete(scanned_item)
    db.session.commit()
    
    flash(_("Package removed from inventory successfully"), "success")
    
    if product:
        return redirect(url_for("ingredients.show_product", id=product.id))
    else:
        return redirect(url_for("ingredients.index"))


@ingredients_bp.route("/<int:id>/calculate", methods=["POST"])
def calculate(id: int):
    """Calculate package quantities needed for an ingredient."""
    ingredient = ActiveIngredient.query.get_or_404(id)
    
    # Get the units needed from the request
    units_needed = request.form.get("units", type=int)
    calculation_type = request.form.get("calculation", "additional")  # 'additional' or 'total'
    
    if not units_needed:
        return {"error": "No units specified"}, 400
    
    # Get default product to determine package sizes
    product = ingredient.default_product or (ingredient.products[0] if ingredient.products else None)
    
    if not product:
        # Return default N1/N2/N3 calculation
        return {
            "packages": {
                "N1": 1 if units_needed > 0 else 0,
                "N2": 0,
                "N3": 0
            }
        }
    
    # Calculate packages based on product package sizes
    packages = {}
    
    if product.packages:
        # Use actual package definitions
        remaining = units_needed
        for package in sorted(product.packages, key=lambda p: p.quantity or 0, reverse=True):
            if package.quantity and package.quantity > 0:
                count = remaining // package.quantity
                if count > 0:
                    packages[package.package_size] = count
                    remaining -= count * package.quantity
        
        # Add one more of the smallest package if there's remainder
        if remaining > 0:
            smallest = min(product.packages, key=lambda p: p.quantity or float('inf'))
            if smallest.package_size in packages:
                packages[smallest.package_size] += 1
            else:
                packages[smallest.package_size] = 1
    else:
        # Fall back to N1/N2/N3 if no packages defined
        packages = {
            "N1": 1 if units_needed > 0 else 0,
            "N2": 0,
            "N3": 0
        }
    
    return {"packages": packages}
