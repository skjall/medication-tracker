"""
Models package initialization.
Imports all models from submodules to make them available when importing from the models package.
"""

# Standard library imports
import logging
from typing import TYPE_CHECKING

# Local application imports
from .base import db, utcnow
from .medication import Medication
from .inventory import Inventory, InventoryLog
from .visit import HospitalVisit, Order, OrderItem
from .schedule import ScheduleType, MedicationSchedule
from .settings import Settings
from .prescription import PrescriptionTemplate

# Re-export utils functions that were originally in models.py
# These need to be migrated to appropriate modules but for now
# we'll keep them available here for backwards compatibility
from utils import ensure_timezone_utc

# Create a logger for this package
logger = logging.getLogger(__name__)

# Define what should be imported when using "from models import *"
__all__ = [
    "db",
    "utcnow",
    "Medication",
    "Inventory",
    "InventoryLog",
    "HospitalVisit",
    "Order",
    "OrderItem",
    "ScheduleType",
    "MedicationSchedule",
    "Settings",
    "PrescriptionTemplate",
    "ensure_timezone_utc",
]
