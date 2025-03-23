"""
Database models for the Medication Tracker application.

This module defines SQLAlchemy ORM models for:
- Medications
- Inventory
- Hospital visits
- Orders and order items
- Hospital visit settings
"""

from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List, Tuple, Any
import os
import enum
import json

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    Text,
    Boolean,
    ForeignKey,
    func,
    JSON,
    Enum,
)

db = SQLAlchemy()


# Create a function to ensure all datetime objects are timezone-aware
def ensure_timezone_utc(dt: datetime) -> datetime:
    """Make sure datetime has timezone info, defaulting to UTC if none."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


# Function to return timezone-aware current time
def utcnow() -> datetime:
    """Return timezone-aware current datetime in UTC."""
    return datetime.now(timezone.utc)


class Medication(db.Model):
    """
    Model representing a medication with dosage information and package size options.
    Extended to support detailed scheduling and automatic inventory deduction.
    """

    __tablename__ = "medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dosage: Mapped[float] = mapped_column(Float, nullable=False)

    # Keeping frequency for backward compatibility, but will be calculated from schedules
    frequency: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Number of times per day (deprecated, use schedules)",
    )
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
        Integer, default=14, comment="Extra days to add when calculating needs"
    )

    # Auto deduction enabled flag
    auto_deduction_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    inventory: Mapped[Optional[Inventory]] = relationship(
        "Inventory",
        back_populates="medication",
        uselist=False,
        cascade="all, delete-orphan",
    )
    order_items: Mapped[List[OrderItem]] = relationship(
        "OrderItem", back_populates="medication"
    )

    # New relationship for medication schedules
    schedules: Mapped[List[MedicationSchedule]] = relationship(
        "MedicationSchedule", back_populates="medication", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self) -> str:
        return f"<Medication {self.name}, {self.dosage} units>"

    @property
    def daily_usage(self) -> float:
        """Calculate daily usage based on schedules or fallback to dosage*frequency."""
        if self.schedules:
            return sum(schedule.calculate_daily_usage() for schedule in self.schedules)
        # Fallback to old calculation method
        return self.dosage * self.frequency

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
                        f"Automatic deduction: {amount} units at {current_time.strftime('%Y-%m-%d %H:%M')}",
                    )
                    total_deducted += amount
                    deduction_made = True

                    # Update last deduction time
                    schedule.last_deduction = current_time

        return deduction_made, total_deducted

    def calculate_needed_until_visit(
        self, visit_date: datetime, include_safety_margin: bool = True
    ) -> int:
        """
        Calculate how many units of medication are needed until the next hospital visit.

        Args:
            visit_date: The date of the next hospital visit
            include_safety_margin: Whether to include the safety margin days in the calculation

        Returns:
            The number of units needed
        """
        # Ensure visit_date is timezone-aware
        visit_date = ensure_timezone_utc(visit_date)
        now = utcnow()

        days_until_visit = (visit_date - now).days
        if days_until_visit < 0:
            days_until_visit = 0

        total_days = days_until_visit
        if include_safety_margin:
            total_days += self.safety_margin_days

        return int(total_days * self.daily_usage)

    def calculate_needed_for_two_visit_intervals(self, days_between_visits: int) -> int:
        """
        Calculate how many units are needed to last until the next-but-one visit.

        Args:
            days_between_visits: Typical number of days between hospital visits

        Returns:
            The number of units needed
        """
        # For next-but-one visit, we need medication for two visit intervals
        total_days = days_between_visits * 2

        # Add safety margin
        total_days += self.safety_margin_days

        return int(total_days * self.daily_usage)

    def calculate_packages_needed(self, units_needed: int) -> Dict[str, int]:
        """
        Convert required units into package quantities, optimizing for package sizes.

        Args:
            units_needed: Total number of units/pills needed

        Returns:
            Dictionary with keys 'N1', 'N2', 'N3' and corresponding package counts
        """
        packages = {"N1": 0, "N2": 0, "N3": 0}
        remaining = units_needed

        # Try to use larger packages first if more efficient
        if self.package_size_n3 and self.package_size_n3 > 0:
            packages["N3"] = remaining // self.package_size_n3
            remaining %= self.package_size_n3

        if self.package_size_n2 and self.package_size_n2 > 0 and remaining > 0:
            packages["N2"] = remaining // self.package_size_n2
            remaining %= self.package_size_n2

        if self.package_size_n1 and self.package_size_n1 > 0 and remaining > 0:
            # Round up to ensure we have enough
            packages["N1"] = (
                remaining + self.package_size_n1 - 1
            ) // self.package_size_n1

        return packages


class Inventory(db.Model):
    """
    Model representing the current inventory for a medication.
    """

    __tablename__ = "inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medication_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("medications.id"), unique=True
    )
    current_count: Mapped[int] = mapped_column(
        Integer, default=0, comment="Current pill/unit count"
    )

    # Package counts
    packages_n1: Mapped[int] = mapped_column(Integer, default=0)
    packages_n2: Mapped[int] = mapped_column(Integer, default=0)
    packages_n3: Mapped[int] = mapped_column(Integer, default=0)

    # Relationship
    medication: Mapped[Medication] = relationship(
        "Medication", back_populates="inventory"
    )
    inventory_logs: Mapped[List[InventoryLog]] = relationship(
        "InventoryLog", back_populates="inventory", cascade="all, delete-orphan"
    )

    last_updated: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    def __repr__(self) -> str:
        return f"<Inventory for {self.medication.name}: {self.current_count} units>"

    @property
    def is_low(self) -> bool:
        """Check if the inventory is below the minimum threshold."""
        return self.current_count < self.medication.min_threshold

    def update_count(self, adjustment: int, notes: Optional[str] = None) -> None:
        """
        Update inventory count and create a log entry.

        Args:
            adjustment: The amount to adjust (positive for additions, negative for deductions)
            notes: Optional notes about the adjustment
        """
        previous_count = self.current_count
        self.current_count += adjustment
        self.last_updated = utcnow()

        # Create log entry
        log = InventoryLog(
            inventory_id=self.id,
            previous_count=previous_count,
            adjustment=adjustment,
            new_count=self.current_count,
            notes=notes,
        )
        db.session.add(log)

    def calculate_total_units_from_packages(self) -> int:
        """Calculate total units based on package counts and sizes."""
        total = 0
        if self.medication.package_size_n1:
            total += self.packages_n1 * self.medication.package_size_n1
        if self.medication.package_size_n2:
            total += self.packages_n2 * self.medication.package_size_n2
        if self.medication.package_size_n3:
            total += self.packages_n3 * self.medication.package_size_n3
        return total

    def update_from_packages(self) -> None:
        """Update current_count based on package quantities."""
        self.current_count = self.calculate_total_units_from_packages()
        self.last_updated = utcnow()


class InventoryLog(db.Model):
    """
    Model for tracking inventory changes.
    """

    __tablename__ = "inventory_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inventory_id: Mapped[int] = mapped_column(Integer, ForeignKey("inventory.id"))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    previous_count: Mapped[int] = mapped_column(Integer)
    adjustment: Mapped[int] = mapped_column(Integer)
    new_count: Mapped[int] = mapped_column(Integer)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationship
    inventory: Mapped[Inventory] = relationship(
        "Inventory", back_populates="inventory_logs"
    )

    def __repr__(self) -> str:
        change = "+" if self.adjustment > 0 else ""
        return f"<InventoryLog {self.timestamp}: {change}{self.adjustment}>"


class HospitalVisit(db.Model):
    """
    Model representing a scheduled hospital visit.
    Extended to support visit interval planning.
    """

    __tablename__ = "hospital_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    visit_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # New field for tracking if an order should be for one or two visit intervals
    order_for_next_but_one: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="If true, orders for this visit should last until the next-but-one visit",
    )

    # Relationships
    orders: Mapped[List[Order]] = relationship(
        "Order", back_populates="hospital_visit", cascade="all, delete-orphan"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self) -> str:
        return f"<HospitalVisit {self.visit_date.strftime('%Y-%m-%d')}>"

    @property
    def days_until(self) -> int:
        """Calculate days until this hospital visit."""
        # Ensure visit_date is timezone-aware
        visit_date = ensure_timezone_utc(self.visit_date)
        now = utcnow()

        delta = visit_date - now
        return max(0, delta.days)


class Order(db.Model):
    """
    Model representing a medication order for a hospital visit.
    """

    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    hospital_visit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hospital_visits.id")
    )
    created_date: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Status can be 'planned', 'printed', 'fulfilled'
    status: Mapped[str] = mapped_column(String(20), default="planned")

    # Relationships
    hospital_visit: Mapped[HospitalVisit] = relationship(
        "HospitalVisit", back_populates="orders"
    )
    order_items: Mapped[List[OrderItem]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Order for visit {self.hospital_visit_id}, status: {self.status}>"


class OrderItem(db.Model):
    """
    Model representing an item in a medication order.
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, ForeignKey("orders.id"))
    medication_id: Mapped[int] = mapped_column(Integer, ForeignKey("medications.id"))

    quantity_needed: Mapped[int] = mapped_column(Integer)
    packages_n1: Mapped[int] = mapped_column(Integer, default=0)
    packages_n2: Mapped[int] = mapped_column(Integer, default=0)
    packages_n3: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    order: Mapped[Order] = relationship("Order", back_populates="order_items")
    medication: Mapped[Medication] = relationship(
        "Medication", back_populates="order_items"
    )

    def __repr__(self) -> str:
        return f"<OrderItem {self.medication.name} for order {self.order_id}>"


class ScheduleType(enum.Enum):
    """Enum for different types of medication schedules."""

    DAILY = "daily"
    INTERVAL = "interval"  # Every X days
    WEEKDAYS = "weekdays"  # Specific days of the week


class MedicationSchedule(db.Model):
    """
    Model representing a medication schedule with timing information.
    Multiple schedules can be defined for a single medication.
    """

    __tablename__ = "medication_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medication_id: Mapped[int] = mapped_column(Integer, ForeignKey("medications.id"))

    # Schedule type
    schedule_type: Mapped[ScheduleType] = mapped_column(
        Enum(ScheduleType), nullable=False
    )

    # For interval type: take every X days (1 = daily, 2 = every other day, etc.)
    interval_days: Mapped[int] = mapped_column(Integer, default=1)

    # For weekdays type: selected days (stored as JSON array of day numbers, 0=Monday, 6=Sunday)
    weekdays: Mapped[Optional[str]] = mapped_column(JSON, nullable=True)

    # Time of day for taking medication (can be multiple)
    # Stored as JSON array of 24h format times, e.g., ["09:00", "17:00"]
    times_of_day: Mapped[str] = mapped_column(JSON, nullable=False)

    # Units to take at this schedule
    units_per_dose: Mapped[float] = mapped_column(Float, default=1.0)

    # Last automatic deduction date/time
    last_deduction: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationship
    medication: Mapped["Medication"] = relationship(
        "Medication", back_populates="schedules"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self) -> str:
        return f"<MedicationSchedule {self.id} for medication {self.medication_id}>"

    @property
    def formatted_times(self) -> List[str]:
        """Return the list of times from the JSON string."""
        if isinstance(self.times_of_day, str):
            return json.loads(self.times_of_day)
        return self.times_of_day

    @property
    def formatted_weekdays(self) -> List[int]:
        """Return the list of weekdays from the JSON string."""
        if self.weekdays is None:
            return []
        if isinstance(self.weekdays, str):
            return json.loads(self.weekdays)
        return self.weekdays

    def is_due_now(self, current_time: datetime) -> bool:
        """
        Check if medication is due to be taken at the current time.
        Args:
            current_time: The current datetime
        Returns:
            Boolean indicating if the medication is due
        """
        # Ensure current_time is timezone-aware
        current_time = ensure_timezone_utc(current_time)

        # If we've already deducted today or there's no last deduction, check schedule
        if self.last_deduction is not None:
            last_deduction = ensure_timezone_utc(self.last_deduction)
            last_deduction_date = last_deduction.date()
            if last_deduction_date == current_time.date():
                return False  # Already deducted today

        # Get current time in HH:MM format for comparison
        current_time_str = current_time.strftime("%H:%M")
        times_list = self.formatted_times

        # Check if current time matches any of the scheduled times
        if current_time_str not in times_list:
            return False

        # For daily schedule, it's due if the time matches
        if self.schedule_type == ScheduleType.DAILY:
            return True

        # For interval schedule, check if it's been interval_days since last deduction
        elif self.schedule_type == ScheduleType.INTERVAL:
            if self.last_deduction is None:
                return True  # First time taking this medication

            last_deduction = ensure_timezone_utc(self.last_deduction)
            days_since_last = (current_time.date() - last_deduction.date()).days
            return days_since_last >= self.interval_days

        # For weekday schedule, check if today is one of the selected days
        elif self.schedule_type == ScheduleType.WEEKDAYS:
            # Get day of week (0=Monday, 6=Sunday)
            current_weekday = current_time.weekday()
            return current_weekday in self.formatted_weekdays

        return False

    def calculate_daily_usage(self) -> float:
        """
        Calculate the average daily usage based on the schedule.
        Returns:
            Average daily usage in units
        """
        doses_per_day = len(self.formatted_times)

        if self.schedule_type == ScheduleType.DAILY:
            return doses_per_day * self.units_per_dose

        elif self.schedule_type == ScheduleType.INTERVAL:
            # For interval, divide by the interval days
            return (doses_per_day * self.units_per_dose) / self.interval_days

        elif self.schedule_type == ScheduleType.WEEKDAYS:
            # For weekdays, calculate based on number of days per week
            days_per_week = len(self.formatted_weekdays)
            return (doses_per_day * self.units_per_dose * days_per_week) / 7

        return 0.0


class HospitalVisitSettings(db.Model):
    """
    System-wide settings for hospital visits and planning.
    Singleton model (only one row expected).
    """

    __tablename__ = "hospital_visit_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Default interval between hospital visits in days (e.g., 90 days)
    default_visit_interval: Mapped[int] = mapped_column(Integer, default=90)

    # Whether to automatically create a visit at the default interval
    auto_schedule_visits: Mapped[bool] = mapped_column(Boolean, default=False)

    # Whether orders should by default cover until next-but-one visit
    default_order_for_next_but_one: Mapped[bool] = mapped_column(Boolean, default=True)

    # Last automatic deduction check timestamp
    last_deduction_check: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        onupdate=utcnow,
    )

    def __repr__(self) -> str:
        return f"<HospitalVisitSettings interval={self.default_visit_interval} days>"

    @classmethod
    def get_settings(cls) -> HospitalVisitSettings:
        """
        Get or create the hospital visit settings.

        Returns:
            The settings object (singleton)
        """
        settings = cls.query.first()
        if settings is None:
            settings = cls(
                default_visit_interval=90,
                auto_schedule_visits=False,
                default_order_for_next_but_one=True,
            )
            db.session.add(settings)
            db.session.commit()
        return settings
