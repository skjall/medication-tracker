"""
Models package initialization.
Imports all models from submodules to make them available when importing from the models package.
"""

# Standard library imports
import logging

# Local application imports
from .base import db, utcnow
from .physician import Physician
from .medication import Medication
from .active_ingredient import ActiveIngredient
from .medication_product import MedicationProduct
from .product_package import ProductPackage
from .inventory import Inventory, InventoryLog
from .visit import PhysicianVisit, Order, OrderItem
from .schedule import ScheduleType, MedicationSchedule
from .settings import Settings
from .prescription import PrescriptionTemplate
from .scanner import MedicationPackage, ScannedItem, PackageInventory

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
    "Physician",
    "Medication",
    "ActiveIngredient",
    "MedicationProduct",
    "ProductPackage",
    "Inventory",
    "InventoryLog",
    "PhysicianVisit",
    "Order",
    "OrderItem",
    "ScheduleType",
    "MedicationSchedule",
    "Settings",
    "PrescriptionTemplate",
    "MedicationPackage",
    "ScannedItem",
    "PackageInventory",
    "ensure_timezone_utc",
]
