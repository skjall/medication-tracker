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
from utils import ensure_timezone_utc

if TYPE_CHECKING:
    from .inventory import Inventory
    from .visit import OrderItem
    from .schedule import MedicationSchedule
    from .physician import Physician

# Create a logger for this module
logger = logging.getLogger(__name__)


class Medication(db.Model):
    """
    Model representing a medication with dosage information and package size options.
    Extended to support detailed scheduling and automatic inventory deduction.
    """

    __tablename__ = "medications"

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
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem", back_populates="medication", cascade="save-update"
    )

    # New relationship for medication schedules
    schedules: Mapped[List["MedicationSchedule"]] = relationship(
        "MedicationSchedule", back_populates="medication", cascade="all, delete-orphan"
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
    def days_remaining(self) -> Optional[float]:
        """Calculate how many days of medication remain based on current inventory."""
        if not self.inventory or self.daily_usage == 0:
            return None
        return self.inventory.current_count / self.daily_usage

    @property
    def depletion_date(self) -> Optional[datetime]:
        """Calculate the date when medication will run out."""
        if self.days_remaining is None:
            return None
        return utcnow() + timedelta(days=self.days_remaining)

    def check_and_deduct_inventory(self, current_time: datetime) -> Tuple[bool, float]:
        """
        Check schedules and deduct from inventory if medication is due.

        Args:
            current_time: The current datetime to check against

        Returns:
            Tuple of (deduction_made, amount_deducted)
        """
        # Ensure current_time is timezone-aware
        current_time = ensure_timezone_utc(current_time)

        if not self.auto_deduction_enabled or not self.inventory:
            return False, 0

        total_deducted = 0.0
        deduction_made = False

        for schedule in self.schedules:
            if schedule.is_due_now(current_time):
                # Deduct the scheduled amount
                amount = schedule.units_per_dose
                if amount > 0 and self.inventory.current_count >= amount:
                    self.inventory.update_count(
                        -amount,
                        f"Automatic deduction: {amount} units at {current_time.strftime('%d.%m.%Y %H:%M')}",
                    )
                    total_deducted += amount
                    deduction_made = True

                    # Update last deduction time
                    schedule.last_deduction = current_time

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

        Args:
            units_needed: Total number of units/pills needed

        Returns:
            Dictionary with keys 'N1', 'N2', 'N3' and corresponding package counts
        """
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
