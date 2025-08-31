#!/usr/bin/env python
"""
Script to update order status from 'printed' to 'planned'.
Run this once to update existing data.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from main import create_app
from models import db, Order

def update_order_status():
    """Update orders with 'printed' status to 'planned'."""
    app = create_app()
    
    with app.app_context():
        # Find all orders with 'printed' status
        orders = Order.query.filter_by(status='printed').all()
        
        if orders:
            print(f"Found {len(orders)} orders with 'printed' status")
            for order in orders:
                print(f"  - Updating order {order.id} from 'printed' to 'planned'")
                order.status = 'planned'
            
            db.session.commit()
            print(f"Successfully updated {len(orders)} orders")
        else:
            print("No orders found with 'printed' status")

if __name__ == "__main__":
    update_order_status()