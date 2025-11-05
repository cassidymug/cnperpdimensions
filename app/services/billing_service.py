"""
Billing Service

Handles recurring billing, meter readings, and automated invoice generation
for rentals, utilities, subscriptions, and usage-based billing.
"""

from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional
import uuid

from app.models.billing import BillingCycle, BillableItem, RecurringInvoice, RecurringPayment
from app.models.sales import Customer, Invoice, InvoiceItem
from app.models.inventory import Product
from app.services.invoice_service import InvoiceService


class BillingService:
    """Comprehensive billing management service"""

    def __init__(self, db: Session):
        self.db = db
        self.invoice_service = InvoiceService(db)

    # ============================================================================
    # BILLING CYCLES
    # ============================================================================

    def create_billing_cycle(
        self,
        name: str,
        customer_id: str,
        cycle_type: str,
        interval: str,
        interval_count: int = 1,
        start_date: date = None,
        end_date: date = None,
        description: str = None
    ) -> BillingCycle:
        """Create a new billing cycle for a customer"""

        if not start_date:
            start_date = date.today()

        cycle = BillingCycle(
            id=str(uuid.uuid4()),
            name=name,
            customer_id=customer_id,
            cycle_type=cycle_type,
            interval=interval,
            interval_count=interval_count,
            start_date=start_date,
            end_date=end_date,
            status='active',
            description=description,
            meta_data={}
        )

        self.db.add(cycle)
        self.db.commit()
        self.db.refresh(cycle)

        return cycle

    def get_billing_cycles(
        self,
        customer_id: str = None,
        status: str = None
    ) -> List[BillingCycle]:
        """Get billing cycles with optional filters"""

        query = self.db.query(BillingCycle)

        if customer_id:
            query = query.filter(BillingCycle.customer_id == customer_id)

        if status:
            query = query.filter(BillingCycle.status == status)

        return query.all()

    def get_billing_cycle(self, cycle_id: str) -> Optional[BillingCycle]:
        """Get a specific billing cycle"""
        return self.db.query(BillingCycle).filter(BillingCycle.id == cycle_id).first()

    # ============================================================================
    # BILLABLE ITEMS
    # ============================================================================

    def create_billable_item(
        self,
        billing_cycle_id: str,
        billable_type: str,
        billable_id: str,
        amount: Decimal,
        start_date: date,
        end_date: date = None,
        description: str = None,
        meta_data: Dict = None
    ) -> BillableItem:
        """
        Create a new billable item

        Args:
            billing_cycle_id: The billing cycle this item belongs to
            billable_type: Type of billing (rental_property, utility_water, subscription_service, etc.)
            billable_id: Reference to the product/service being billed
            amount: Billing amount
            start_date: When billing starts
            end_date: When billing ends (optional for ongoing)
            description: Description of the billable item
            meta_data: Additional data (meter numbers, license info, etc.)
        """

        if not meta_data:
            meta_data = {}

        # Extract license fields if present in metadata
        license_number = meta_data.get('license_number')
        license_type = meta_data.get('license_type')
        license_expiry = meta_data.get('expiry_date')

        item = BillableItem(
            id=str(uuid.uuid4()),
            billing_cycle_id=billing_cycle_id,
            billable_type=billable_type,
            billable_id=billable_id,
            amount=amount,
            description=description,
            start_date=start_date,
            end_date=end_date,
            status='active',
            meta_data=meta_data,
            license_number=license_number,
            license_type=license_type,
            license_expiry_date=license_expiry
        )

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        return item

    def get_billable_items(
        self,
        billing_cycle_id: str = None,
        billable_type: str = None,
        status: str = None
    ) -> List[BillableItem]:
        """Get billable items with optional filters"""

        query = self.db.query(BillableItem)

        if billing_cycle_id:
            query = query.filter(BillableItem.billing_cycle_id == billing_cycle_id)

        if billable_type:
            query = query.filter(BillableItem.billable_type == billable_type)

        if status:
            query = query.filter(BillableItem.status == status)

        return query.all()

    def get_billable_item(self, item_id: str) -> Optional[BillableItem]:
        """Get a specific billable item"""
        return self.db.query(BillableItem).filter(BillableItem.id == item_id).first()

    def update_billable_item(
        self,
        item_id: str,
        **kwargs
    ) -> BillableItem:
        """Update a billable item"""

        item = self.get_billable_item(item_id)
        if not item:
            raise ValueError(f"Billable item {item_id} not found")

        for key, value in kwargs.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)

        self.db.commit()
        self.db.refresh(item)

        return item

    # ============================================================================
    # METER READINGS (for utilities)
    # ============================================================================

    def record_meter_reading(
        self,
        item_id: str,
        reading_date: date,
        reading_value: Decimal,
        notes: str = None
    ) -> Dict:
        """
        Record a meter reading for a utility billable item

        Returns:
            Dictionary with usage, amount, and updated item info
        """

        item = self.get_billable_item(item_id)
        if not item:
            raise ValueError(f"Billable item {item_id} not found")

        if not item.billable_type.startswith('utility_'):
            raise ValueError("Meter readings can only be recorded for utility items")

        meta_data = item.meta_data or {}

        # Get previous reading
        last_reading = Decimal(meta_data.get('current_reading', 0))

        # Calculate usage
        usage = reading_value - last_reading

        # Get rate per unit
        rate = Decimal(meta_data.get('rate', item.amount))

        # Calculate amount for this period
        amount = usage * rate

        # Update metadata with new reading
        meta_data['last_reading'] = float(last_reading)
        meta_data['current_reading'] = float(reading_value)
        meta_data['last_reading_date'] = reading_date.isoformat()
        meta_data['usage'] = float(usage)
        meta_data['amount'] = float(amount)

        if notes:
            meta_data['last_reading_notes'] = notes

        # Add to reading history
        if 'reading_history' not in meta_data:
            meta_data['reading_history'] = []

        meta_data['reading_history'].append({
            'date': reading_date.isoformat(),
            'reading': float(reading_value),
            'usage': float(usage),
            'amount': float(amount),
            'notes': notes
        })

        # Update the item
        item.meta_data = meta_data
        item.amount = amount  # Update amount for next invoice generation

        self.db.commit()
        self.db.refresh(item)

        return {
            'last_reading': float(last_reading),
            'current_reading': float(reading_value),
            'usage': float(usage),
            'rate': float(rate),
            'amount': float(amount),
            'reading_date': reading_date.isoformat()
        }

    # ============================================================================
    # INVOICE GENERATION
    # ============================================================================

    def generate_invoices_for_cycle(
        self,
        billing_cycle_id: str,
        invoice_date: date = None,
        created_by: str = None
    ) -> List[Invoice]:
        """
        Generate invoices for all active items in a billing cycle

        Args:
            billing_cycle_id: The billing cycle to generate invoices for
            invoice_date: Invoice date (defaults to today)
            created_by: User creating the invoices

        Returns:
            List of created invoices
        """

        if not invoice_date:
            invoice_date = date.today()

        cycle = self.get_billing_cycle(billing_cycle_id)
        if not cycle:
            raise ValueError(f"Billing cycle {billing_cycle_id} not found")

        # Get all active billable items for this cycle
        items = self.get_billable_items(
            billing_cycle_id=billing_cycle_id,
            status='active'
        )

        if not items:
            return []

        # Group items by customer (should all be same customer for a cycle)
        invoices_created = []

        # Get customer from cycle
        customer = self.db.query(Customer).filter(Customer.id == cycle.customer_id).first()
        if not customer:
            raise ValueError(f"Customer {cycle.customer_id} not found")

        # Prepare invoice items
        invoice_items = []
        for item in items:
            # Get product details
            product = self.db.query(Product).filter(Product.id == item.billable_id).first()
            if not product:
                continue

            # Determine description based on billing type
            description = item.description or f"{item.billable_type.replace('_', ' ').title()}"

            # For utilities, include meter reading info
            if item.billable_type.startswith('utility_'):
                meta = item.meta_data or {}
                description += f" (Meter: {meta.get('meter_number', 'N/A')}, "
                description += f"Usage: {meta.get('usage', 0)} units)"

            invoice_items.append({
                'product_id': item.billable_id,
                'quantity': 1,
                'unit_price': float(item.amount),
                'description': description
            })

        if not invoice_items:
            return []

        # Calculate due date based on cycle interval
        payment_terms = 30  # Default
        if cycle.interval == 'monthly':
            payment_terms = 30
        elif cycle.interval == 'quarterly':
            payment_terms = 90
        elif cycle.interval == 'annual':
            payment_terms = 365

        due_date = invoice_date + timedelta(days=payment_terms)

        # Create the invoice
        invoice = self.invoice_service.create_invoice(
            customer_id=customer.id,
            branch_id=customer.branch_id,
            invoice_items=invoice_items,
            due_date=due_date,
            payment_terms=payment_terms,
            notes=f"Billing for cycle: {cycle.name}",
            created_by=created_by
        )

        # Create recurring invoice records for tracking
        for item in items:
            recurring_invoice = RecurringInvoice(
                id=str(uuid.uuid4()),
                billing_cycle_id=cycle.id,
                billable_item_id=item.id,
                invoice_number=invoice.invoice_number,
                due_date=due_date,
                amount=item.amount,
                status='pending',
                description=f"Invoice for {item.description or item.billable_type}",
                meta_data={'invoice_id': invoice.id}
            )
            self.db.add(recurring_invoice)

        self.db.commit()
        invoices_created.append(invoice)

        return invoices_created

    def generate_all_due_invoices(
        self,
        reference_date: date = None,
        created_by: str = None
    ) -> Dict:
        """
        Generate invoices for all billing cycles that are due

        Args:
            reference_date: Date to check for due invoices (defaults to today)
            created_by: User creating the invoices

        Returns:
            Dictionary with count and list of created invoices
        """

        if not reference_date:
            reference_date = date.today()

        # Get all active billing cycles
        cycles = self.get_billing_cycles(status='active')

        invoices_created = []

        for cycle in cycles:
            # Determine if invoices are due based on cycle type and last invoice date
            # For now, generate for all active cycles
            # TODO: Add logic to check last invoice date and interval

            try:
                cycle_invoices = self.generate_invoices_for_cycle(
                    billing_cycle_id=cycle.id,
                    invoice_date=reference_date,
                    created_by=created_by
                )
                invoices_created.extend(cycle_invoices)
            except Exception as e:
                print(f"Error generating invoices for cycle {cycle.id}: {e}")
                continue

        return {
            'count': len(invoices_created),
            'invoices': [
                {
                    'id': inv.id,
                    'invoice_number': inv.invoice_number,
                    'customer_id': inv.customer_id,
                    'total_amount': float(inv.total_amount)
                }
                for inv in invoices_created
            ]
        }

    # ============================================================================
    # DASHBOARD & REPORTING
    # ============================================================================

    def get_dashboard_stats(self) -> Dict:
        """Get billing dashboard statistics"""

        # Get all active items
        all_items = self.get_billable_items(status='active')

        # Categorize items
        rentals = [i for i in all_items if 'rental' in i.billable_type]
        utilities = [i for i in all_items if 'utility' in i.billable_type]
        subscriptions = [i for i in all_items if 'subscription' in i.billable_type]
        usage = [i for i in all_items if 'usage' in i.billable_type]

        # Calculate revenues
        rentals_revenue = sum(float(i.amount) for i in rentals)
        subscriptions_revenue = sum(float(i.amount) for i in subscriptions)
        usage_revenue = sum(float(i.amount) for i in usage)

        # Count pending meter readings (utilities without recent readings)
        pending_readings = 0
        for util in utilities:
            meta = util.meta_data or {}
            last_reading_date = meta.get('last_reading_date')
            if not last_reading_date:
                pending_readings += 1
            else:
                # Check if reading is older than 30 days
                try:
                    last_date = datetime.fromisoformat(last_reading_date).date()
                    if (date.today() - last_date).days > 30:
                        pending_readings += 1
                except:
                    pending_readings += 1

        return {
            'active_rentals': len(rentals),
            'rentals_revenue': rentals_revenue,
            'utility_meters': len(utilities),
            'pending_readings': pending_readings,
            'subscriptions': len(subscriptions),
            'subscriptions_revenue': subscriptions_revenue,
            'usage_items': len(usage),
            'usage_revenue': usage_revenue,
            'total_active_items': len(all_items)
        }

    def get_customer_billing_summary(self, customer_id: str) -> Dict:
        """Get billing summary for a specific customer"""

        # Get customer's billing cycles
        cycles = self.get_billing_cycles(customer_id=customer_id, status='active')

        # Get all billable items for these cycles
        all_items = []
        for cycle in cycles:
            items = self.get_billable_items(billing_cycle_id=cycle.id, status='active')
            all_items.extend(items)

        # Calculate totals
        total_monthly = sum(float(i.amount) for i in all_items if 'monthly' in i.billable_type.lower())
        total_annual = sum(float(i.amount) for i in all_items)

        return {
            'customer_id': customer_id,
            'active_cycles': len(cycles),
            'active_items': len(all_items),
            'estimated_monthly': total_monthly,
            'estimated_annual': total_annual,
            'cycles': [
                {
                    'id': c.id,
                    'name': c.name,
                    'cycle_type': c.cycle_type,
                    'item_count': len(self.get_billable_items(billing_cycle_id=c.id, status='active'))
                }
                for c in cycles
            ]
        }
