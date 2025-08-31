"""
PDF Template model for storing form templates and field mappings.
"""

from datetime import datetime
from typing import Optional
import json
from sqlalchemy import String, Integer, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .base import db, utcnow


class PDFTemplate(db.Model):
    """
    Stores PDF form templates with field mappings and configurations.
    """
    
    __tablename__ = "pdf_templates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    
    # Template identification
    name: Mapped[str] = mapped_column(
        String(200), 
        nullable=False,
        comment="Template name for user reference"
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text, 
        nullable=True,
        comment="Description of what this template is for"
    )
    
    # PDF storage
    filename: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        comment="Original PDF filename"
    )
    
    file_path: Mapped[str] = mapped_column(
        String(500), 
        nullable=False,
        comment="Path to stored PDF file"
    )
    
    # Table configuration
    table_config: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Table detection configuration (rows, columns, boundaries)"
    )
    
    # Field mappings
    field_mappings: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Mapping of data fields to PDF form fields"
    )
    
    # Column formulas
    column_formulas: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Formulas for combining multiple fields in columns"
    )
    
    # Tab order
    tab_order: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        comment="Ordered list of field names for tab navigation"
    )
    
    # PDF structure mapping (for existing form fields)
    pdf_structure: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Structure mapping for existing PDF form fields (patient info, medication rows)"
    )
    
    # Structure mapping - maps PDF form fields to grid positions
    structure_mapping: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Maps PDF form fields to table grid positions (row, column)"
    )
    
    # Mapping step tracker
    mapping_step: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        default='structure',
        comment="Current mapping step: 'structure' or 'content'"
    )
    
    # Settings
    rows_per_page: Mapped[int] = mapped_column(
        Integer,
        default=20,
        comment="Number of rows in the table"
    )
    
    columns_count: Mapped[int] = mapped_column(
        Integer,
        default=5,
        comment="Number of columns in the table"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether this template is available for use"
    )
    
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether this is the default template"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow, nullable=False
    )
    
    def __repr__(self):
        return f"<PDFTemplate {self.name}>"
    
    @property
    def has_fields(self) -> bool:
        """Check if template has form fields defined."""
        return bool(self.field_mappings)
    
    @property
    def total_fields(self) -> int:
        """Get total number of fields in template."""
        if not self.field_mappings:
            return 0
        return len(self.field_mappings)
    
    def get_column_formula(self, column_index: int) -> dict:
        """Get formula configuration for a specific column."""
        if not self.column_formulas:
            return {}
        return self.column_formulas.get(str(column_index), {})
    
    def set_column_formula(self, column_index: int, fields: list, separator: str = " "):
        """Set formula for combining fields in a column."""
        if not self.column_formulas:
            self.column_formulas = {}
        
        self.column_formulas[str(column_index)] = {
            "fields": fields,
            "separator": separator
        }
    
    @classmethod
    def get_default_template(cls):
        """Get the default PDF template."""
        return cls.query.filter_by(is_default=True, is_active=True).first()
    
    def to_dict(self) -> dict:
        """Convert template to dictionary for JSON response."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'filename': self.filename,
            'rows_per_page': self.rows_per_page,
            'columns_count': self.columns_count,
            'has_fields': self.has_fields,
            'total_fields': self.total_fields,
            'is_default': self.is_default,
            'table_config': self.table_config,
            'field_mappings': self.field_mappings,
            'column_formulas': self.column_formulas,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }