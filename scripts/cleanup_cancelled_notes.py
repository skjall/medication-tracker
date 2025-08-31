#!/usr/bin/env python
"""
Script to remove default 'Cancelled by user' notes from order items.
Run this once to clean up existing data.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from main import create_app
from models import db, OrderItem

def cleanup_cancelled_notes():
    """Remove default 'Cancelled by user' notes from database."""
    app = create_app()
    
    with app.app_context():
        # Find all items with the default cancelled text
        items = OrderItem.query.filter(
            OrderItem.fulfillment_notes.in_([
                'Cancelled by user',
                'Vom Benutzer storniert',  # German translation
                'Annulé par l\'utilisateur'  # French translation if exists
            ])
        ).all()
        
        if items:
            print(f"Found {len(items)} items with default cancellation notes")
            for item in items:
                print(f"  - Clearing notes for order item {item.id}")
                item.fulfillment_notes = None
            
            db.session.commit()
            print(f"Successfully cleared {len(items)} default notes")
        else:
            print("No items found with default cancellation notes")

if __name__ == "__main__":
    cleanup_cancelled_notes()