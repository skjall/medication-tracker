"""
This module defines prescription template related models.
"""

# Standard library imports
from datetime import datetime
import json
import logging
import os
from typing import Dict, Optional

# Third-party imports
from flask import current_app
from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

# Local application imports
from .base import db, utcnow

# Create a logger for this module
logger = logging.getLogger(__name__)


class PrescriptionTemplate(db.Model):
    """
    Model for storing prescription form template configuration.
    This defines how prescription orders are formatted for the PDF form.
    """

    __tablename__ = "prescription_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Template file path (stored in data/templates directory)
    template_file: Mapped[str] = mapped_column(String(255), nullable=False)

    # Form field configuration
    first_field_tab_index: Mapped[int] = mapped_column(Integer, default=1)
    medications_per_page: Mapped[int] = mapped_column(Integer, default=15)

    # Column mappings (JSON representation of field mappings)
    # Example format: {"1": "medication_name", "2": "active_ingredient", etc.}
    column_mappings: Mapped[str] = mapped_column(JSON, nullable=False)

    # Whether this is the active template
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    # Template file upload timestamp
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    def __repr__(self) -> str:
        return f"<PrescriptionTemplate {self.name}>"

    @property
    def template_path(self) -> str:
        """Get the full path to the template file."""
        return os.path.join(
            current_app.root_path, "data", "templates", self.template_file
        )

    @property
    def column_mapping_dict(self) -> Dict[str, str]:
        """Get the column mappings as a dictionary."""
        if isinstance(self.column_mappings, str):
            return json.loads(self.column_mappings)
        return self.column_mappings

    @classmethod
    def get_active_template(cls) -> Optional["PrescriptionTemplate"]:
        """Get the currently active template or None if none is active."""
        return cls.query.filter_by(is_active=True).first()

    def activate(self) -> None:
        """Make this template the active template."""
        # First deactivate all templates
        PrescriptionTemplate.query.update({PrescriptionTemplate.is_active: False})

        # Then activate this one
        self.is_active = True
        db.session.commit()
