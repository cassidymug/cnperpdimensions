"""
Inventory Allocation Service

This service handles the allocation and distribution of inventory from headquarters
to branches, including:
- Receiving inventory at headquarters
- Allocating inventory to branches
- Processing allocation requests from branches
- Tracking inventory movements between locations
- Branch-specific inventory visibility
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, func, or_, desc
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
import uuid

from app.models.inventory import Product, InventoryTransaction
from app.models.inventory_allocation import (
    BranchInventoryAllocation,
    InventoryAllocationRequest,
    InventoryAllocationMovement,
    BranchStockSnapshot,
    HeadquartersInventory
)
from app.models.branch import Branch
from app.models.user import User


class InventoryAllocationService:
    """Service for managing inventory allocation between headquarters and branches"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # ============================================================================
    # HEADQUARTERS INVENTORY MANAGEMENT
    # ============================================================================
    
    def receive_inventory_at_headquarters(
        self,
        product_id: str,
        quantity: int,
        cost_per_unit: float,
        supplier_reference: str = None,
        received_by: str = None,
        notes: str = None
    ) -> Dict:
        """Record receipt of inventory at headquarters from suppliers"""
        
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")
        
        # Get or create headquarters inventory record
        hq_inventory = self.db.query(HeadquartersInventory).filter(
            HeadquartersInventory.product_id == product_id
        ).first()
        
        if not hq_inventory:
            hq_inventory = HeadquartersInventory(
                product_id=product_id,
                total_received_quantity=0,
                total_allocated_quantity=0,
                available_for_allocation=0
            )
            self.db.add(hq_inventory)
        
        # Update headquarters inventory quantities
        hq_inventory.total_received_quantity += quantity
        hq_inventory.available_for_allocation += quantity
        
        # Update average cost calculation
        current_total_cost = hq_inventory.total_cost_value or 0
        new_total_cost = current_total_cost + (quantity * cost_per_unit)
        new_total_quantity = hq_inventory.total_received_quantity
        
        hq_inventory.average_cost_per_unit = new_total_cost / new_total_quantity if new_total_quantity > 0 else cost_per_unit
        hq_inventory.total_cost_value = new_total_cost
        hq_inventory.last_received_date = date.today()
        
        # Create inventory transaction for headquarters receipt
        receipt_transaction = InventoryTransaction(
            product_id=product_id,
            transaction_type='headquarters_receipt',
            quantity=quantity,
            unit_cost=cost_per_unit,
            total_cost=quantity * cost_per_unit,
            reference=supplier_reference or f"HQ-RECEIPT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            note=notes or f"Received {quantity} units at headquarters",
            date=date.today(),
            created_by=received_by,
            branch_id=None  # Headquarters has no branch_id
        )
        self.db.add(receipt_transaction)
        
        self.db.commit()
        
        return {
            "success": True,
            "product_id": product_id,
            "quantity_received": quantity,
            "cost_per_unit": cost_per_unit,
            "total_cost": quantity * cost_per_unit,
            "new_hq_available": hq_inventory.available_for_allocation,
            "transaction_id": receipt_transaction.id
        }
    
    def get_headquarters_inventory(self, product_id: str = None) -> List[Dict]:
        """Get current headquarters inventory levels for all products.

        Returns one row per Product. If a product has no HeadquartersInventory row yet,
        the quantities and costs are zero-filled so the UI can still list it and allow
        receiving/allocating operations.
        """

        # LEFT OUTER JOIN Products -> HeadquartersInventory to include all products
        query = self.db.query(Product, HeadquartersInventory).outerjoin(
            HeadquartersInventory, HeadquartersInventory.product_id == Product.id
        )

        if product_id:
            query = query.filter(Product.id == product_id)

        results = query.all()

        inventory_data: List[Dict] = []
        for product, hq_inv in results:
            # Determine if HQ record has real HQ activity; if not, treat as absent (ignore legacy seed rows)
            has_real_hq_activity = False
            if hq_inv:
                hq_txn_count = self.db.query(func.count(InventoryTransaction.id)).filter(
                    InventoryTransaction.product_id == product.id,
                    InventoryTransaction.branch_id.is_(None),
                    InventoryTransaction.transaction_type.in_(['headquarters_receipt', 'branch_allocation'])
                ).scalar() or 0
                has_real_hq_activity = hq_txn_count > 0

            # When no HQ record exists yet OR HQ record has no real activity, fall back to product's inventory and cost
            if (not hq_inv) or (hq_inv and not has_real_hq_activity):
                fallback_qty = int(product.quantity or 0)
                fallback_cost = float(product.cost_price or 0)
                rp = int(product.reorder_point or product.minimum_stock_level or 10)
                total_received = fallback_qty
                total_allocated = 0
                available_for_allocation = fallback_qty
                reserved_for_allocation = 0
                damaged_quantity = 0
                avg_cost = fallback_cost
                total_cost_value = fallback_qty * fallback_cost
                last_received_date = None
                last_allocated_date = None
                reorder_point = rp
            else:
                # Use actual HQ figures
                total_received = int(hq_inv.total_received_quantity or 0)
                total_allocated = int(hq_inv.total_allocated_quantity or 0)
                available_for_allocation = int(hq_inv.available_for_allocation or 0)
                reserved_for_allocation = int(hq_inv.reserved_for_allocation or 0)
                damaged_quantity = int(hq_inv.damaged_quantity or 0)
                avg_cost = float(hq_inv.average_cost_per_unit or 0)
                total_cost_value = float(hq_inv.total_cost_value or 0)
                last_received_date = hq_inv.last_received_date
                last_allocated_date = hq_inv.last_allocated_date
                reorder_point = int(hq_inv.reorder_point or 10)

            inventory_data.append({
                "product_id": product.id,
                "product_name": product.name,
                "sku": product.sku,
                "total_received": total_received,
                "total_allocated": total_allocated,
                "available_for_allocation": available_for_allocation,
                "reserved_for_allocation": reserved_for_allocation,
                "damaged_quantity": damaged_quantity,
                "average_cost_per_unit": avg_cost,
                "total_cost_value": total_cost_value,
                "last_received_date": last_received_date,
                "last_allocated_date": last_allocated_date,
                "reorder_point": reorder_point,
                "is_low_stock": available_for_allocation <= reorder_point
            })

        return inventory_data
    
    # ============================================================================
    # BRANCH ALLOCATION MANAGEMENT
    # ============================================================================
    
    def allocate_inventory_to_branch(
        self,
        product_id: str,
        branch_id: str,
        quantity: int,
        allocated_by: str = None,
        expected_delivery_date: date = None,
        transport_method: str = None,
        notes: str = None
    ) -> Dict:
        """Allocate inventory from headquarters to a specific branch"""
        
        # Validate product and branch exist
        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")
        
        branch = self.db.query(Branch).filter(Branch.id == branch_id).first()
        if not branch:
            raise ValueError("Branch not found")
        
        # Check headquarters inventory availability
        hq_inventory = self.db.query(HeadquartersInventory).filter(
            HeadquartersInventory.product_id == product_id
        ).first()
        
        if not hq_inventory or hq_inventory.available_for_allocation < quantity:
            available = hq_inventory.available_for_allocation if hq_inventory else 0
            raise ValueError(f"Insufficient inventory at headquarters. Available: {available}, Requested: {quantity}")
        
        # Generate allocation reference
        allocation_ref = f"ALLOC-{branch.code or branch_id[:6].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create or update branch allocation record
        existing_allocation = self.db.query(BranchInventoryAllocation).filter(
            and_(
                BranchInventoryAllocation.product_id == product_id,
                BranchInventoryAllocation.branch_id == branch_id,
                BranchInventoryAllocation.allocation_status.in_(['pending', 'shipped'])
            )
        ).first()
        
        if existing_allocation:
            # Update existing pending allocation
            existing_allocation.allocated_quantity += quantity
            existing_allocation.total_allocated_cost += quantity * float(hq_inventory.average_cost_per_unit)
            existing_allocation.notes = f"{existing_allocation.notes or ''} | Additional allocation: {quantity} units"
            allocation = existing_allocation
        else:
            # Create new allocation
            allocation = BranchInventoryAllocation(
                product_id=product_id,
                branch_id=branch_id,
                allocated_quantity=quantity,
                allocated_cost_per_unit=hq_inventory.average_cost_per_unit,
                total_allocated_cost=quantity * float(hq_inventory.average_cost_per_unit),
                allocation_status='pending',
                allocation_reference=allocation_ref,
                allocated_by=allocated_by,
                expected_delivery_date=expected_delivery_date,
                transport_method=transport_method,
                notes=notes
            )
            self.db.add(allocation)
        # Ensure allocation has an ID before referencing it in child rows
        self.db.flush()
        
        # Update headquarters inventory
        hq_inventory.available_for_allocation -= quantity
        hq_inventory.total_allocated_quantity += quantity
        hq_inventory.last_allocated_date = date.today()
        
        # Create allocation movement record
        movement = InventoryAllocationMovement(
            allocation_id=allocation.id,
            movement_type='allocated',
            quantity=quantity,
            processed_by=allocated_by,
            from_location='headquarters',
            to_location=f'branch_{branch_id}',
            unit_cost=hq_inventory.average_cost_per_unit,
            total_cost=quantity * float(hq_inventory.average_cost_per_unit),
            notes=f"Allocated to {branch.name}"
        )
        self.db.add(movement)
        
        # Create inventory transaction for the allocation
        allocation_transaction = InventoryTransaction(
            product_id=product_id,
            transaction_type='branch_allocation',
            quantity=-quantity,  # Negative because it's leaving headquarters
            unit_cost=hq_inventory.average_cost_per_unit,
            total_cost=quantity * float(hq_inventory.average_cost_per_unit),
            reference=allocation_ref,
            note=f"Allocated {quantity} units to {branch.name}",
            date=date.today(),
            created_by=allocated_by,
            branch_id=None  # Headquarters transaction
        )
        self.db.add(allocation_transaction)
        
        self.db.commit()
        
        return {
            "success": True,
            "allocation_id": allocation.id,
            "allocation_reference": allocation.allocation_reference,
            "product_name": product.name,
            "branch_name": branch.name,
            "allocated_quantity": quantity,
            "cost_per_unit": float(hq_inventory.average_cost_per_unit),
            "total_cost": quantity * float(hq_inventory.average_cost_per_unit),
            "expected_delivery": expected_delivery_date,
            "remaining_hq_stock": hq_inventory.available_for_allocation
        }
    
    def ship_allocation_to_branch(
        self,
        allocation_id: str,
        shipped_by: str = None,
        tracking_number: str = None,
        actual_quantity_shipped: int = None
    ) -> Dict:
        """Mark allocation as shipped from headquarters"""
        
        allocation = self.db.query(BranchInventoryAllocation).filter(
            BranchInventoryAllocation.id == allocation_id
        ).first()
        
        if not allocation:
            raise ValueError("Allocation not found")
        
        if allocation.allocation_status != 'pending':
            raise ValueError(f"Cannot ship allocation with status: {allocation.allocation_status}")
        
        shipped_quantity = actual_quantity_shipped or allocation.allocated_quantity
        
        # Update allocation status
        allocation.allocation_status = 'shipped'
        allocation.tracking_number = tracking_number
        
        # Create shipping movement record
        shipping_movement = InventoryAllocationMovement(
            allocation_id=allocation_id,
            movement_type='shipped',
            quantity=shipped_quantity,
            processed_by=shipped_by,
            from_location='headquarters',
            to_location='in_transit',
            unit_cost=allocation.allocated_cost_per_unit,
            total_cost=shipped_quantity * float(allocation.allocated_cost_per_unit),
            reference_number=tracking_number,
            notes=f"Shipped {shipped_quantity} units to {allocation.branch.name}"
        )
        self.db.add(shipping_movement)
        
        self.db.commit()
        
        return {
            "success": True,
            "allocation_id": allocation_id,
            "allocation_reference": allocation.allocation_reference,
            "shipped_quantity": shipped_quantity,
            "tracking_number": tracking_number,
            "status": "shipped"
        }
    
    def receive_allocation_at_branch(
        self,
        allocation_id: str,
        received_by: str = None,
        actual_quantity_received: int = None,
        condition_notes: str = None
    ) -> Dict:
        """Mark allocation as received at the branch"""
        
        allocation = self.db.query(BranchInventoryAllocation).filter(
            BranchInventoryAllocation.id == allocation_id
        ).first()
        
        if not allocation:
            raise ValueError("Allocation not found")
        
        if allocation.allocation_status != 'shipped':
            raise ValueError(f"Cannot receive allocation with status: {allocation.allocation_status}")
        
        received_quantity = actual_quantity_received or allocation.allocated_quantity
        
        # Update allocation
        allocation.allocation_status = 'received'
        allocation.received_quantity = received_quantity
        allocation.available_quantity = received_quantity
        allocation.actual_delivery_date = date.today()
        allocation.received_by = received_by
        
        if condition_notes:
            allocation.notes = f"{allocation.notes or ''} | Receiving notes: {condition_notes}"
        
        # Create receiving movement record
        receiving_movement = InventoryAllocationMovement(
            allocation_id=allocation_id,
            movement_type='received',
            quantity=received_quantity,
            processed_by=received_by,
            from_location='in_transit',
            to_location=f'branch_{allocation.branch_id}',
            unit_cost=allocation.allocated_cost_per_unit,
            total_cost=received_quantity * float(allocation.allocated_cost_per_unit),
            notes=condition_notes or f"Received {received_quantity} units at {allocation.branch.name}"
        )
        self.db.add(receiving_movement)
        
        # Create inventory transaction for the branch
        branch_receipt_transaction = InventoryTransaction(
            product_id=allocation.product_id,
            transaction_type='branch_receipt',
            quantity=received_quantity,
            unit_cost=allocation.allocated_cost_per_unit,
            total_cost=received_quantity * float(allocation.allocated_cost_per_unit),
            reference=allocation.allocation_reference,
            note=f"Received {received_quantity} units from headquarters allocation",
            date=date.today(),
            created_by=received_by,
            branch_id=allocation.branch_id
        )
        self.db.add(branch_receipt_transaction)
        
        self.db.commit()
        
        return {
            "success": True,
            "allocation_id": allocation_id,
            "received_quantity": received_quantity,
            "branch_name": allocation.branch.name,
            "available_quantity": allocation.available_quantity,
            "status": "received"
        }
    
    # ============================================================================
    # BRANCH INVENTORY VISIBILITY
    # ============================================================================
    
    def get_branch_inventory(self, branch_id: str, product_id: str = None) -> List[Dict]:
        """Get inventory available at a specific branch"""
        
        query = self.db.query(BranchInventoryAllocation, Product).join(Product).filter(
            and_(
                BranchInventoryAllocation.branch_id == branch_id,
                BranchInventoryAllocation.allocation_status == 'received',
                BranchInventoryAllocation.available_quantity > 0
            )
        )
        
        if product_id:
            query = query.filter(BranchInventoryAllocation.product_id == product_id)
        
        results = query.all()
        
        branch_inventory = []
        for allocation, product in results:
            branch_inventory.append({
                "product_id": product.id,
                "product_name": product.name,
                "sku": product.sku,
                "available_quantity": allocation.available_quantity,
                "reserved_quantity": allocation.reserved_quantity,
                "cost_per_unit": float(allocation.allocated_cost_per_unit),
                "branch_selling_price": float(allocation.branch_selling_price) if allocation.branch_selling_price else float(product.selling_price or 0),
                "total_value": allocation.available_quantity * float(allocation.allocated_cost_per_unit),
                "allocation_date": allocation.allocation_date,
                "is_low_stock": allocation.available_quantity <= allocation.reorder_point,
                "reorder_point": allocation.reorder_point,
                "minimum_stock": allocation.minimum_stock_level
            })
        
        return branch_inventory
    
    def get_branch_stock_summary(self, branch_id: str) -> Dict:
        """Get summary of branch inventory status"""
        
        allocations = self.db.query(BranchInventoryAllocation).filter(
            and_(
                BranchInventoryAllocation.branch_id == branch_id,
                BranchInventoryAllocation.allocation_status == 'received'
            )
        ).all()
        
        total_products = len(allocations)
        total_value = sum(a.available_quantity * float(a.allocated_cost_per_unit) for a in allocations)
        low_stock_count = sum(1 for a in allocations if a.available_quantity <= a.reorder_point)
        out_of_stock_count = sum(1 for a in allocations if a.available_quantity == 0)
        
        return {
            "branch_id": branch_id,
            "total_products": total_products,
            "total_inventory_value": total_value,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "healthy_stock_count": total_products - low_stock_count - out_of_stock_count,
            "summary_date": datetime.now()
        }
    
    # ============================================================================
    # ALLOCATION REQUEST MANAGEMENT
    # ============================================================================
    
    def create_allocation_request(
        self,
        requesting_branch_id: str,
        product_id: str,
        requested_quantity: int,
        reason: str,
        requested_by: str,
        priority_level: str = 'normal',
        required_by_date: date = None,
        justification: str = None
    ) -> Dict:
        """Create a request for inventory allocation from a branch"""
        
        # Generate request reference
        branch = self.db.query(Branch).filter(Branch.id == requesting_branch_id).first()
        request_ref = f"REQ-{branch.code or requesting_branch_id[:6].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        allocation_request = InventoryAllocationRequest(
            requesting_branch_id=requesting_branch_id,
            product_id=product_id,
            requested_quantity=requested_quantity,
            reason=reason,
            justification=justification,
            priority_level=priority_level,
            required_by_date=required_by_date,
            requested_by=requested_by,
            request_reference=request_ref
        )
        
        self.db.add(allocation_request)
        self.db.commit()
        
        return {
            "success": True,
            "request_id": allocation_request.id,
            "request_reference": request_ref,
            "status": "pending"
        }
    
    def get_pending_allocation_requests(self) -> List[Dict]:
        """Get all pending allocation requests for headquarters review"""
        
        requests = self.db.query(
            InventoryAllocationRequest, Branch, Product, User
        ).join(
            Branch, InventoryAllocationRequest.requesting_branch_id == Branch.id
        ).join(
            Product, InventoryAllocationRequest.product_id == Product.id
        ).join(
            User, InventoryAllocationRequest.requested_by == User.id
        ).filter(
            InventoryAllocationRequest.request_status == 'pending'
        ).order_by(
            InventoryAllocationRequest.priority_level.desc(),
            InventoryAllocationRequest.request_date
        ).all()
        
        pending_requests = []
        for request, branch, product, user in requests:
            pending_requests.append({
                "request_id": request.id,
                "request_reference": request.request_reference,
                "branch_name": branch.name,
                "branch_id": branch.id,
                "product_name": product.name,
                "product_sku": product.sku,
                "requested_quantity": request.requested_quantity,
                "reason": request.reason,
                "justification": request.justification,
                "priority_level": request.priority_level,
                "request_date": request.request_date,
                "required_by_date": request.required_by_date,
                "requested_by": user.username,
                "days_pending": (datetime.now() - request.request_date).days
            })
        
        return pending_requests

    # ============================================================================
    # APPROVAL AND LISTING
    # ============================================================================

    def approve_allocation_request(
        self,
        request_id: str,
        approved_quantity: int,
        approved_by: str,
        approval_notes: str | None = None,
    ) -> Dict:
        """Approve an allocation request and create/update the corresponding allocation.

        This reduces HQ available stock, creates (or updates) a BranchInventoryAllocation in 'pending' status,
        records a movement and HQ inventory transaction, and marks the request approved.
        """
        # Load request
        req = self.db.query(InventoryAllocationRequest).filter(
            InventoryAllocationRequest.id == request_id
        ).first()
        if not req:
            raise ValueError("Allocation request not found")
        if req.request_status != 'pending':
            raise ValueError(f"Cannot approve a request with status: {req.request_status}")

        # Validate product and branch
        branch = self.db.query(Branch).filter(Branch.id == req.requesting_branch_id).first()
        if not branch:
            raise ValueError("Requesting branch not found")
        product = self.db.query(Product).filter(Product.id == req.product_id).first()
        if not product:
            raise ValueError("Product not found")

        # Validate HQ stock
        hq_inventory = self.db.query(HeadquartersInventory).filter(
            HeadquartersInventory.product_id == req.product_id
        ).first()
        available = hq_inventory.available_for_allocation if hq_inventory else 0
        if not hq_inventory or available < approved_quantity:
            raise ValueError(f"Insufficient HQ stock. Available: {available}, Requested: {approved_quantity}")

        # Allocation reference
        allocation_ref = f"ALLOC-{branch.code or branch.id[:6].upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create or update pending allocation record for this branch/product
        allocation = self.db.query(BranchInventoryAllocation).filter(
            and_(
                BranchInventoryAllocation.product_id == req.product_id,
                BranchInventoryAllocation.branch_id == req.requesting_branch_id,
                BranchInventoryAllocation.allocation_status.in_(['pending', 'shipped'])
            )
        ).first()
        unit_cost = float(hq_inventory.average_cost_per_unit or 0)
        if allocation:
            allocation.allocated_quantity += approved_quantity
            allocation.total_allocated_cost = float(allocation.total_allocated_cost or 0) + approved_quantity * unit_cost
            if not allocation.allocation_reference:
                allocation.allocation_reference = allocation_ref
            notes_base = allocation.notes or ''
            allocation.notes = f"{notes_base} | Approved from request {req.request_reference}: {approved_quantity}"
        else:
            allocation = BranchInventoryAllocation(
                product_id=req.product_id,
                branch_id=req.requesting_branch_id,
                allocated_quantity=approved_quantity,
                allocated_cost_per_unit=unit_cost,
                total_allocated_cost=approved_quantity * unit_cost,
                allocation_status='pending',
                allocation_reference=allocation_ref,
                notes=f"Approved from request {req.request_reference}"
            )
            self.db.add(allocation)

        # Ensure allocation ID is assigned prior to creating child movement
        self.db.flush()

        # Reduce HQ available and increase total allocated
        hq_inventory.available_for_allocation -= approved_quantity
        hq_inventory.total_allocated_quantity += approved_quantity
        hq_inventory.last_allocated_date = date.today()

        # Movement
        movement = InventoryAllocationMovement(
            allocation_id=allocation.id,
            movement_type='allocated',
            quantity=approved_quantity,
            processed_by=approved_by,
            from_location='headquarters',
            to_location=f'branch_{branch.id}',
            unit_cost=unit_cost,
            total_cost=approved_quantity * unit_cost,
            notes=f"Approved allocation for request {req.request_reference}"
        )
        self.db.add(movement)

        # HQ inventory transaction
        txn = InventoryTransaction(
            product_id=req.product_id,
            transaction_type='branch_allocation',
            quantity=-approved_quantity,
            unit_cost=unit_cost,
            total_cost=approved_quantity * unit_cost,
            reference=allocation_ref,
            note=f"Approved allocation for {branch.name}",
            date=date.today(),
            created_by=approved_by,
            branch_id=None
        )
        self.db.add(txn)

        # Update request
        req.approved_quantity = approved_quantity
        req.request_status = 'approved'
        req.approved_by = approved_by
        req.approved_date = datetime.now()
        if approval_notes:
            req.internal_notes = (req.internal_notes or '') + f"\nApproved: {approval_notes}"
        req.allocation_id = allocation.id

        self.db.commit()

        return {
            "success": True,
            "request_id": req.id,
            "request_reference": req.request_reference,
            "allocation_id": allocation.id,
            "allocation_reference": allocation.allocation_reference,
            "approved_quantity": approved_quantity,
            "remaining_hq_stock": hq_inventory.available_for_allocation
        }

    def get_allocations(self, status: Optional[str] = None, branch_id: Optional[str] = None) -> List[Dict]:
        """List allocations with optional filters by status and branch (no-join version to avoid ambiguity)."""
        q = self.db.query(BranchInventoryAllocation)
        if status:
            q = q.filter(BranchInventoryAllocation.allocation_status == status)
        if branch_id:
            q = q.filter(BranchInventoryAllocation.branch_id == branch_id)
        q = q.order_by(desc(BranchInventoryAllocation.allocation_date))
        allocations = q.all()

        # Hydrate product and branch info in separate queries to avoid join ambiguity
        product_ids = {a.product_id for a in allocations if a.product_id}
        branch_ids = {a.branch_id for a in allocations if a.branch_id}
        products = {}
        branches = {}
        if product_ids:
            for p in self.db.query(Product).filter(Product.id.in_(list(product_ids))).all():
                products[p.id] = p
        if branch_ids:
            for b in self.db.query(Branch).filter(Branch.id.in_(list(branch_ids))).all():
                branches[b.id] = b

        out: List[Dict] = []
        for a in allocations:
            p = products.get(a.product_id)
            b = branches.get(a.branch_id)
            out.append({
                "allocation_id": a.id,
                "allocation_reference": a.allocation_reference,
                "status": a.allocation_status,
                "product_id": a.product_id,
                "product_name": p.name if p else None,
                "sku": p.sku if p else None,
                "branch_id": a.branch_id,
                "branch_name": b.name if b else None,
                "allocated_quantity": a.allocated_quantity,
                "received_quantity": a.received_quantity,
                "available_quantity": a.available_quantity,
                "reserved_quantity": a.reserved_quantity,
                "unit_cost": float(a.allocated_cost_per_unit or 0),
                "total_cost": float(a.total_allocated_cost or 0),
                "allocation_date": a.allocation_date,
                "expected_delivery_date": a.expected_delivery_date,
                "tracking_number": a.tracking_number,
            })
        return out
