"""
This module defines the medication-related database models.
"""

# Standard library imports
from datetime import datetime, timedelta, timezone
import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

# Third-party imports
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Local application imports
from .base import db, utcnow

if TYPE_CHECKING:
    from .inventory import Inventory
    from .visit import OrderItem
    from .schedule import MedicationSchedule
    from .physician import Physician
    from .scanner import MedicationPackage
    from .medication_product import MedicationProduct

# Create a logger for this module
logger = logging.getLogger(__name__)


class Medication(db.Model):
    """
    Model representing a medication with dosage information and package size options.
    Extended to support detailed scheduling and automatic inventory deduction.
    """

    __tablename__ = "medications"
    
    def __init__(self, **kwargs):
        """Initialize medication and set auto_deduction_enabled_at if needed."""
        super().__init__(**kwargs)
        
        # If auto_deduction is enabled on creation, set the enabled_at timestamp
        # This prevents retroactive deductions for periods before the medication was added
        if self.auto_deduction_enabled and self.auto_deduction_enabled_at is None:
            from .base import utcnow
            self.auto_deduction_enabled_at = utcnow()

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Physician relationship and OTC flag
    physician_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("physicians.id"), nullable=True
    )
    is_otc: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="True if medication is over-the-counter"
    )
    
    # Aut idem flag - allows generic substitution by pharmacist
    aut_idem: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="True if generic substitution is allowed"
    )

    # Legacy fields - marked as deprecated but kept for database compatibility
    # These are no longer used for calculations
    dosage: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="DEPRECATED: No longer used for calculations, use schedules instead.",
    )
    frequency: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="DEPRECATED: No longer used for calculations, use schedules instead.",
    )

    active_ingredient: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    form: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Package sizes
    package_size_n1: Mapped[int] = mapped_column(Integer, nullable=True)
    package_size_n2: Mapped[int] = mapped_column(Integer, nullable=True)
    package_size_n3: Mapped[int] = mapped_column(Integer, nullable=True)

    # Inventory management
    min_threshold: Mapped[int] = mapped_column(
        Integer, default=0, comment="Minimum inventory level before warning"
    )
    safety_margin_days: Mapped[int] = mapped_column(
        Integer, default=30, comment="Extra days to add when calculating needs"
    )

    # Auto deduction enabled flag
    auto_deduction_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Track when auto deduction was enabled to prevent retroactive deductions before that date
    auto_deduction_enabled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        nullable=True,
        comment="UTC timestamp when auto-deduction was last enabled"
    )
    
    # Inventory mode for hybrid system
    inventory_mode: Mapped[Optional[str]] = mapped_column(
        String(20), 
        default='legacy',
        nullable=True,
        comment="legacy, packages, or hybrid"
    )
    
    # Default product for ordering (when multiple products exist for this medication)
    default_product_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("medication_products.id"),
        nullable=True,
        comment="Default product to use for ordering packages"
    )

    # Relationships
    physician: Mapped[Optional["Physician"]] = relationship(
        "Physician", back_populates="medications"
    )
    inventory: Mapped[Optional["Inventory"]] = relationship(
        "Inventory",
        back_populates="medication",
        uselist=False,
        cascade="all, delete-orphan",
    )
    # Removed order_items relationship - orders now use ActiveIngredient

    # New relationship for medication schedules
    schedules: Mapped[List["MedicationSchedule"]] = relationship(
        "MedicationSchedule", back_populates="medication", cascade="all, delete-orphan"
    )
    
    # Scanner system relationship
    packages: Mapped[List["MedicationPackage"]] = relationship(
        "MedicationPackage", back_populates="medication", cascade="all, delete-orphan"
    )
    
    # Default product relationship
    default_product: Mapped[Optional["MedicationProduct"]] = relationship(
        "MedicationProduct",
        foreign_keys=[default_product_id],
        post_update=True  # Avoid circular dependency issues
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self) -> str:
        return f"<Medication {self.name}>"

    @property
    def daily_usage(self) -> float:
        """Calculate daily usage based on schedules."""
        if not self.schedules:
            # Return 0 if no schedules are defined
            return 0.0
        return sum(schedule.calculate_daily_usage() for schedule in self.schedules)

    @property
    def total_inventory_count(self) -> float:
        """Get total inventory including both legacy and package-based inventory."""
        total = 0
        
        # Add legacy inventory
        if self.inventory:
            total += self.inventory.current_count
        
        # Add package inventory linked directly to this medication
        from models import PackageInventory
        package_units = PackageInventory.query.filter(
            PackageInventory.medication_id == self.id,
            PackageInventory.status.in_(['sealed', 'open'])
        ).with_entities(db.func.sum(PackageInventory.current_units)).scalar()
        
        if package_units:
            total += package_units
        
        # Also add inventory from packages linked through the new product system
        if self.default_product:
            # Use the product's total inventory count (which includes new packages)
            # But subtract what we've already counted above to avoid double counting
            product_total = self.default_product.total_inventory_count
            # The product count includes legacy packages we already counted, so we need the difference
            # This gets us only the NEW packages not linked to medication_id
            from models import ScannedItem, ProductPackage
            from sqlalchemy import or_
            
            # Get packages linked through product but without medication_id
            packages = ProductPackage.query.filter_by(product_id=self.default_product_id).all()
            package_gtins = [p.gtin for p in packages if p.gtin]
            package_numbers = [(p.national_number, p.national_number_type) 
                              for p in packages if p.national_number]
            
            if package_gtins or package_numbers:
                query = (
                    db.session.query(db.func.sum(PackageInventory.current_units))
                    .join(ScannedItem, PackageInventory.scanned_item_id == ScannedItem.id)
                    .filter(
                        PackageInventory.status.in_(['sealed', 'open']),
                        PackageInventory.medication_id.is_(None)  # Only new packages
                    )
                )
                
                conditions = []
                if package_gtins:
                    conditions.append(ScannedItem.gtin.in_(package_gtins))
                for nat_num, nat_type in package_numbers:
                    conditions.append(
                        (ScannedItem.national_number == nat_num) & 
                        (ScannedItem.national_number_type == nat_type)
                    )
                
                if conditions:
                    query = query.filter(or_(*conditions))
                    new_package_units = query.scalar()
                    if new_package_units:
                        total += new_package_units
            
        return total

    @property
    def days_remaining(self) -> Optional[float]:
        """Calculate how many days of medication remain based on current inventory."""
        if self.daily_usage == 0:
            return None
        total_count = self.total_inventory_count
        if total_count == 0:
            return None
        return total_count / self.daily_usage

    @property
    def depletion_date(self) -> Optional[datetime]:
        """Calculate the date when medication will run out."""
        if self.days_remaining is None:
            return None
        return utcnow() + timedelta(days=self.days_remaining)
    
    @property
    def has_package_inventory(self) -> bool:
        """Check if medication has any packages with units available."""
        from models import PackageInventory
        return db.session.query(
            PackageInventory.query.filter_by(medication_id=self.id)
            .filter(PackageInventory.current_units > 0)
            .exists()
        ).scalar()
    
    @property
    def has_any_packages(self) -> bool:
        """Check if medication has ANY packages (including empty ones)."""
        from models import PackageInventory
        return db.session.query(
            PackageInventory.query.filter_by(medication_id=self.id).exists()
        ).scalar()
    
    @property
    def uses_package_system(self) -> bool:
        """
        Determine if this medication should use package-based inventory.
        True when legacy inventory is empty (or doesn't exist) and ANY packages exist (even empty).
        Once packages are registered, we stay in package mode.
        """
        has_legacy = self.inventory and self.inventory.current_count > 0
        # Use package system if no legacy AND any packages exist (even empty ones)
        return not has_legacy and self.has_any_packages
    
    @property
    def active_package_count(self) -> int:
        """Count of packages with units available."""
        from models import PackageInventory
        return PackageInventory.query.filter_by(medication_id=self.id)\
            .filter(PackageInventory.current_units > 0).count()

    def get_next_package_for_deduction(self):
        """
        Get the next package to deduct from using FIFO principle.
        Priority: 1. Open packages (by expiry, then opened date)
                  2. Sealed packages (by expiry, then scan date)
        """
        from models import PackageInventory, ScannedItem
        from sqlalchemy import case
        
        return PackageInventory.query.join(ScannedItem)\
            .filter(
                PackageInventory.medication_id == self.id,
                PackageInventory.status.in_(['open', 'sealed']),
                PackageInventory.current_units > 0
            ).order_by(
                # Open packages first
                case((PackageInventory.status == 'open', 0), else_=1),
                # Then by expiry date (nulls last)
                ScannedItem.expiry_date.asc().nullslast(),
                # Then by opened date for open packages
                PackageInventory.opened_at.asc().nullslast(),
                # Finally by scan date
                ScannedItem.scanned_at.asc()
            ).first()
    
    def deduct_units(self, amount: int, reason: str = None) -> Dict:
        """
        Intelligent deduction that handles both legacy and package inventory.
        Deducts from legacy first, then from packages using FIFO.
        
        Returns:
            Dict with deduction details including success status and what was deducted from
        """
        from models import PackageInventory
        result = {
            'success': False,
            'total_deducted': 0,
            'legacy_deducted': 0,
            'packages_deducted': [],
            'insufficient': False,
            'notes': []
        }
        
        remaining = amount
        
        # Capture the original total inventory count before any modifications
        original_total_count = self.total_inventory_count
        
        # Step 1: Try to deduct from legacy inventory first
        if self.inventory and self.inventory.current_count > 0:
            legacy_deduction = min(remaining, self.inventory.current_count)
            # Only update legacy inventory, don't log yet - we'll log the total at the end
            self.inventory.current_count -= legacy_deduction
            self.inventory.last_updated = utcnow()
            remaining -= legacy_deduction
            result['legacy_deducted'] = legacy_deduction
            result['total_deducted'] += legacy_deduction
            
            if legacy_deduction > 0:
                result['notes'].append(f"Deducted {legacy_deduction} from legacy inventory")
        
        # Step 2: If still need more, deduct from packages
        while remaining > 0:
            package = self.get_next_package_for_deduction()
            if not package:
                # No more packages available
                result['insufficient'] = True
                result['notes'].append(f"Insufficient inventory: needed {remaining} more units")
                break
            
            # If package is sealed, open it
            if package.status == 'sealed':
                package.status = 'open'
                package.opened_at = utcnow()
                result['notes'].append(f"Opened package {package.scanned_item.serial_number}")
            
            # Deduct what we can from this package
            package_deduction = min(remaining, package.current_units)
            package.current_units -= package_deduction
            remaining -= package_deduction
            
            # Mark as empty if depleted
            if package.current_units == 0:
                package.status = 'empty'
                package.consumed_at = utcnow()
            
            result['packages_deducted'].append({
                'package_id': package.id,
                'serial': package.scanned_item.serial_number if package.scanned_item else f"Package #{package.id}",
                'amount': package_deduction,
                'remaining': package.current_units
            })
            result['total_deducted'] += package_deduction
        
        # Create a single inventory log entry for the entire deduction
        if self.inventory and result['total_deducted'] > 0:
            from models import InventoryLog
            
            # Build detailed reason string
            reason_parts = []
            if result['legacy_deducted'] > 0:
                reason_parts.append(f"Legacy: {result['legacy_deducted']} units")
            for pkg in result['packages_deducted']:
                reason_parts.append(f"Package {pkg['serial']}: {pkg['amount']} units")
            
            detailed_reason = f"{reason or 'Automatic deduction'}"
            if len(reason_parts) > 0:
                detailed_reason += f" ({', '.join(reason_parts)})"
            
            # Create log entry with the correct total counts
            log = InventoryLog(
                inventory_id=self.inventory.id,
                previous_count=original_total_count,
                adjustment=-result['total_deducted'],
                new_count=original_total_count - result['total_deducted'],
                notes=detailed_reason,
            )
            db.session.add(log)
        
        result['success'] = remaining == 0
        return result

    def check_and_deduct_inventory(self, current_time: datetime) -> Tuple[bool, float]:
        """
        Check schedules and deduct from inventory if medication is due.

        Args:
            current_time: The current datetime to check against

        Returns:
            Tuple of (deduction_made, amount_deducted)
        """
        # Ensure current_time is timezone-aware
        from utils import ensure_timezone_utc
        current_time = ensure_timezone_utc(current_time)

        if not self.auto_deduction_enabled:
            return False, 0

        total_deducted = 0.0
        deduction_made = False

        for schedule in self.schedules:
            if schedule.is_due_now(current_time):
                # Deduct the scheduled amount using new intelligent deduction
                amount = schedule.units_per_dose
                if amount > 0 and self.total_inventory_count >= amount:
                    result = self.deduct_units(
                        amount, 
                        f"Scheduled deduction for {current_time.strftime('%Y-%m-%d %H:%M')}"
                    )
                    if result['success']:
                        total_deducted += result['total_deducted']
                        deduction_made = True
                        schedule.last_deduction = current_time
                        
                        # Log the deduction details
                        logger.debug(f"Deduction for {self.name}: {result['notes']}")
                    else:
                        logger.warning(f"Failed to deduct {amount} units from {self.name}: insufficient inventory")

        return deduction_made, total_deducted

    def calculate_needed_until_visit(
        self,
        visit_date: datetime,
        include_safety_margin: bool = True,
        consider_next_but_one: bool = None,
    ) -> int:
        """
        Calculate how many units of medication are needed until the next physician visit.

        Args:
            visit_date: The date of the next physician visit
            include_safety_margin: Whether to include the safety margin days in the calculation
            consider_next_but_one: Override to consider next-but-one visit (uses default from settings if None)

        Returns:
            The number of units needed
        """
        # Ensure visit_date is timezone-aware
        from models import Settings
        from utils import ensure_timezone_utc

        visit_date = ensure_timezone_utc(visit_date)
        now = datetime.now(timezone.utc)

        logger.debug(f"Visit date: {visit_date}, Current time: {now}")

        days_until_visit = (visit_date - now).days
        if days_until_visit < 0:
            days_until_visit = 0

        logger.info(
            f"Calculating units needed until visit on {visit_date.strftime('%d.%m.%Y')}: {days_until_visit} days"
        )

        # Get next-but-one setting if not explicitly provided
        if consider_next_but_one is None:
            # Check if the visit has a specific setting
            from models import PhysicianVisit

            visit = PhysicianVisit.query.filter_by(visit_date=visit_date).first()
            if visit and visit.order_for_next_but_one:
                consider_next_but_one = True
            else:
                # Fall back to global setting
                settings = Settings.get_settings()
                consider_next_but_one = settings.default_order_for_next_but_one

        # If next-but-one is enabled, double the visit interval
        if consider_next_but_one:
            # Get the default interval between visits
            settings = Settings.get_settings()
            # Add another visit interval to the calculation
            days_until_visit += settings.default_visit_interval

        total_days = days_until_visit
        if include_safety_margin:
            total_days += self.safety_margin_days

        return int(total_days * self.daily_usage)

    def calculate_needed_for_two_visit_intervals(self, days_between_visits: int) -> int:
        """
        Calculate how many units are needed to last until the next-but-one visit.

        Args:
            days_between_visits: Typical number of days between physician visits

        Returns:
            The number of units needed
        """
        # For next-but-one visit, we need medication for two visit intervals
        total_days = days_between_visits * 2

        # Add safety margin
        total_days += self.safety_margin_days

        return int(total_days * self.daily_usage)

    def calculate_needed_for_period(self, start_date: datetime, end_date: datetime, include_safety_margin: bool = True) -> int:
        """
        Calculate how many units of medication are needed for a specific period.

        Args:
            start_date: The start date of the period
            end_date: The end date of the period
            include_safety_margin: Whether to include the safety margin days

        Returns:
            The number of units needed
        """
        # Ensure dates are timezone-aware
        from utils import ensure_timezone_utc
        start_date = ensure_timezone_utc(start_date)
        end_date = ensure_timezone_utc(end_date)
        # Calculate days in period
        period_days = (end_date - start_date).days
        if period_days < 0:
            period_days = 0
        # Add safety margin if requested
        total_days = period_days
        if include_safety_margin:
            total_days += self.safety_margin_days
        return int(total_days * self.daily_usage)

    def calculate_packages_needed(self, units_needed: int) -> Dict[str, int]:
        """
        Convert required units into package quantities, using only a single package type.
        Chooses the package type that minimizes overage, with preference for larger packages.
        
        Uses default product's ProductPackage configurations if set,
        otherwise falls back to legacy N1/N2/N3 system.

        Args:
            units_needed: Total number of units/pills needed

        Returns:
            Dictionary with package names as keys and counts as values
            For default product: Uses actual package names from ProductPackage
            For legacy: Uses 'N1', 'N2', 'N3' keys
        """
        # First check if we have a default product set
        if self.default_product and self.default_product.packages:
            return self._calculate_packages_from_product(self.default_product, units_needed)
        
        # Otherwise check if this medication has been migrated to the new product system
        # and use the first migrated product as fallback
        if self.migrated_product and len(self.migrated_product) > 0:
            product = self.migrated_product[0]
            if product.packages and len(product.packages) > 0:
                # Use new ProductPackage system
                return self._calculate_packages_from_product(product, units_needed)
        
        # Fall back to legacy N1/N2/N3 system
        packages = {"N1": 0, "N2": 0, "N3": 0}

        # If no units needed, return empty packages
        if units_needed <= 0:
            return packages

        # Store available package sizes and their identifiers
        available_packages = []
        if self.package_size_n3 and self.package_size_n3 > 0:
            available_packages.append(("N3", self.package_size_n3))
        if self.package_size_n2 and self.package_size_n2 > 0:
            available_packages.append(("N2", self.package_size_n2))
        if self.package_size_n1 and self.package_size_n1 > 0:
            available_packages.append(("N1", self.package_size_n1))

        # Sort by package size in descending order (largest first)
        available_packages.sort(key=lambda x: x[1], reverse=True)

        # If no package sizes defined, return empty
        if not available_packages:
            return packages

        best_package = None
        min_overage = float("inf")

        for package_key, package_size in available_packages:
            # Calculate how many packages we need and the resulting overage
            count = (
                units_needed + package_size - 1
            ) // package_size  # Ceiling division
            total_units = count * package_size
            overage = total_units - units_needed

            # If this has less overage or same overage but larger package (earlier in list)
            if overage < min_overage or (
                overage == min_overage and best_package is None
            ):
                min_overage = overage
                best_package = (package_key, count)

        # Set the count for the best package type
        if best_package:
            packages[best_package[0]] = best_package[1]

        return packages
    
    def _calculate_packages_from_product(self, product, units_needed: int) -> Dict[str, int]:
        """
        Calculate optimal package combination using ProductPackage configurations.
        
        Args:
            product: MedicationProduct with ProductPackage configurations
            units_needed: Total units required
            
        Returns:
            Dictionary with package_size names as keys and counts as values
        """
        packages = {}
        
        # If no units needed, return empty
        if units_needed <= 0:
            return packages
        
        # Build list of available packages from ProductPackage
        available_packages = []
        for pkg in product.packages:
            if pkg.quantity and pkg.quantity > 0:
                # Initialize the package count to 0
                packages[pkg.package_size] = 0
                available_packages.append((pkg.package_size, pkg.quantity))
        
        # Sort by package size in descending order (largest first)
        available_packages.sort(key=lambda x: x[1], reverse=True)
        
        # If no packages defined, fall back to legacy system
        if not available_packages:
            # Fall back to legacy if product has no packages configured
            legacy_packages = {"N1": 0, "N2": 0, "N3": 0}
            if self.package_size_n1:
                legacy_packages["N1"] = (units_needed + self.package_size_n1 - 1) // self.package_size_n1
            return legacy_packages
        
        best_package = None
        min_overage = float("inf")
        
        # Find the optimal package with minimum overage
        for package_name, package_size in available_packages:
            # Calculate how many packages we need and the resulting overage
            count = (units_needed + package_size - 1) // package_size  # Ceiling division
            total_units = count * package_size
            overage = total_units - units_needed
            
            # Choose package with minimum overage
            # If same overage, prefer larger packages (they come first in sorted list)
            if overage < min_overage:
                min_overage = overage
                best_package = (package_name, count)
        
        # Set the count for the best package
        if best_package:
            packages[best_package[0]] = best_package[1]
        
        return packages
