from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, and_, or_, func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional, Dict
from decimal import Decimal
from datetime import datetime, date

from app.core.database import get_db
from app.core.response_wrapper import UnifiedResponse
from app.models.purchases import Supplier, Purchase, PurchaseItem, PurchaseOrder, PurchaseOrderItem
from app.models.inventory import Product
from app.models.accounting import AccountingCode, JournalEntry, AccountingEntry
from app.models.accounting_dimensions import AccountingDimensionValue
from app.schemas.purchases import (
    SupplierResponse, SupplierCreate, SupplierUpdate,
    PurchaseResponse, PurchaseCreate, PurchaseUpdate,
    PurchaseItemUpdate, PurchaseItemResponse
)
from app.services.asset_management_service import AssetManagementService
from app.services.landed_cost_service import LandedCostService
from app.services.ifrs_accounting_service import IFRSAccountingService
from app.services.purchase_service import PurchaseService
# from app.core.security import get_current_user  # Removed for development
router = APIRouter()  # Dependencies removed for development


def normalize_asset_category(category_input: str) -> str:
    """Convert user-friendly asset category names to proper enum values"""
    if not category_input:
        return 'EQUIPMENT'

    # Mapping from user-friendly names to enum values
    category_mapping = {
        'vehicle': 'VEHICLE',
        'vehicles': 'VEHICLE',
        'car': 'VEHICLE',
        'truck': 'VEHICLE',
        'equipment': 'EQUIPMENT',
        'machinery': 'MACHINERY',
        'furniture': 'FURNITURE',
        'computer': 'COMPUTER',
        'computers': 'COMPUTER',
        'office_equipment': 'OFFICE_EQUIPMENT',
        'office': 'OFFICE_EQUIPMENT',
        'building': 'BUILDING',
        'buildings': 'BUILDING',
        'land': 'LAND',
        'software': 'SOFTWARE',
        'intangible': 'INTANGIBLE',
        'inventory': 'INVENTORY',
        'other': 'OTHER'
    }

    # Normalize input and look up mapping
    normalized_input = category_input.lower().strip()
    return category_mapping.get(normalized_input, 'EQUIPMENT')


@router.post("/{purchase_id}/receive")
async def receive_purchase_items(
    purchase_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Receive items for a purchase, capture serial/batch/expiry, mark purchase as received"""
    try:
        purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")

        items = payload.get('items', [])
        received_by = payload.get('received_by')

        from app.models.inventory import InventoryTransaction, SerialNumber
        from datetime import date

        # Fallback: if no items provided, derive basic receipt lines from purchase items
        if not items:
            items = [
                {
                    'product_id': it.product_id,
                    'quantity': it.quantity
                } for it in (purchase.purchase_items or [])
            ]

        from decimal import Decimal, InvalidOperation

        for item in items:
            product_id = item.get('product_id')
            qty_raw = item.get('quantity')
            try:
                quantity = Decimal(str(qty_raw)) if qty_raw is not None else Decimal('0')
            except (InvalidOperation, ValueError, TypeError):
                quantity = Decimal('0')
            if quantity <=  Decimal('0'):
                continue

            # Only create inventory transactions for items that have a product_id
            # Non-inventory items (like services, vouchers, etc.) don't need inventory tracking
            if product_id:
                # Create inventory transaction for receiving
                inv_tx = InventoryTransaction(
                    product_id=product_id,
                    transaction_type='goods_receipt',
                    quantity=quantity,
                    unit_cost=None,
                    date=date.today(),
                    reference=f"Purchase receipt {purchase_id}",
                    branch_id=purchase.branch_id,
                    related_purchase_id=purchase_id,
                    note=f"Batch:{item.get('batch_number') or ''}|Expiry:{item.get('expiry_date') or ''}|ReceivedBy:{received_by or ''}"
                )
                db.add(inv_tx)

                # Increment on-hand quantity for the product (basic approach; does not yet account for cost updates or allocations)
                try:
                    product = db.query(Product).filter(Product.id == product_id).first()
                    if product:
                        # Ensure numeric addition works for Decimal/float
                        current_qty = Decimal(str(product.quantity or 0))
                        product.quantity = current_qty + quantity
                except Exception as q_err:  # pragma: no cover - safeguard
                    # We don't fail the entire receipt due to a quantity update issue; inventory transaction still recorded
                    print(f"[WARN] Failed updating product quantity for {product_id}: {q_err}")

                # Serial numbers (only for inventory items)
                serials = item.get('serial_numbers') or []
                for s in serials:
                    if s:
                        sn = SerialNumber(
                            serial=s,
                            product_id=product_id,
                            inventory_transaction_id=None,
                            status='in_stock',
                            purchase_date=purchase.purchase_date,
                            supplier_id=purchase.supplier_id
                        )
                        db.add(sn)

        # Mark purchase as received
        purchase.status = 'received'
        purchase.received_at = date.today() if hasattr(purchase, 'received_at') else purchase.purchase_date
        db.commit()
        return {"success": True, "message": "Items received"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error receiving items: {str(e)}")


@router.get("/suppliers")
async def get_suppliers(
    skip: int = 0,
    limit: int = 100,
    supplier_type: str = None,
    active: bool = None,
    search: str = None,
    db: Session = Depends(get_db),
    # # # current_user parameter removed for development,  # Removed for development,  # Removed for development
):
    """Get all suppliers with optional filtering"""
    try:
        query = db.query(Supplier).options(joinedload(Supplier.accounting_code))
        # query = # Security check removed for development  # Removed for development

        # Apply filters
        if supplier_type:
            query = query.filter(Supplier.supplier_type == supplier_type)

        if active is not None:
            # Assuming there's an active field, if not we'll need to add it
            # For now, we'll return all suppliers
            pass

        if search:
            query = query.filter(
                Supplier.name.ilike(f"%{search}%") |
                Supplier.email.ilike(f"%{search}%") |
                Supplier.contact_person.ilike(f"%{search}%")
            )

        suppliers = query.offset(skip).limit(limit).all()

        # Serialize with nested accounting code summary
        def serialize(s: Supplier):
            base = {
                "id": s.id,
                "name": s.name,
                "email": s.email,
                "telephone": s.telephone,
                "address": s.address,
                "accounting_code_id": s.accounting_code_id,
                "vat_reg_number": s.vat_reg_number,
                "branch_id": s.branch_id,
                "supplier_type": s.supplier_type,
                "contact_person": s.contact_person,
                "payment_terms": s.payment_terms,
                "credit_limit": float(s.credit_limit or 0),
                "current_balance": float(s.current_balance or 0),
                "tax_exempt": s.tax_exempt,
                "active": s.active,
                "notes": s.notes,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            if s.accounting_code:
                base["accounting_code"] = {
                    "id": s.accounting_code.id,
                    "code": s.accounting_code.code,
                    "name": s.accounting_code.name,
                    "account_type": s.accounting_code.account_type,
                }
            return base

        serialized = [serialize(s) for s in suppliers]

        return UnifiedResponse.success(
            data=serialized,
            message=f"Retrieved {len(serialized)} suppliers",
            meta={
                "total": query.count(),
                "skip": skip,
                "limit": limit,
                "filters": {
                    "supplier_type": supplier_type,
                    "active": active,
                    "search": search
                }
            }
        )
    except Exception as e:
        return UnifiedResponse.error(f"Error fetching suppliers: {str(e)}")


@router.get("/suppliers/{supplier_id}")
async def get_supplier(supplier_id: str, db: Session = Depends(get_db)):
    """Get supplier by ID (with accounting code summary)"""
    try:
        supplier = (
            db.query(Supplier)
            .options(joinedload(Supplier.accounting_code))
            .filter(Supplier.id == supplier_id)
            .first()
        )
        if not supplier:
            return UnifiedResponse.error("Supplier not found", status_code=404)

        data = {
            "id": supplier.id,
            "name": supplier.name,
            "email": supplier.email,
            "telephone": supplier.telephone,
            "address": supplier.address,
            "accounting_code_id": supplier.accounting_code_id,
            "vat_reg_number": supplier.vat_reg_number,
            "branch_id": supplier.branch_id,
            "supplier_type": supplier.supplier_type,
            "contact_person": supplier.contact_person,
            "payment_terms": supplier.payment_terms,
            "credit_limit": float(supplier.credit_limit or 0),
            "current_balance": float(supplier.current_balance or 0),
            "tax_exempt": supplier.tax_exempt,
            "active": supplier.active,
            "notes": supplier.notes,
            "created_at": supplier.created_at,
            "updated_at": supplier.updated_at,
        }
        if supplier.accounting_code:
            data["accounting_code"] = {
                "id": supplier.accounting_code.id,
                "code": supplier.accounting_code.code,
                "name": supplier.accounting_code.name,
                "account_type": supplier.accounting_code.account_type,
            }

        return UnifiedResponse.success(
            data=data,
            message=f"Retrieved supplier {supplier.name}"
        )
    except Exception as e:
        return UnifiedResponse.error(f"Error fetching supplier: {str(e)}")


@router.post("/suppliers")
async def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    """Create a new supplier"""
    try:
        db_supplier = Supplier(**supplier.model_dump())
        db.add(db_supplier)
        db.commit()
        db.refresh(db_supplier)
        return UnifiedResponse.success(
            data=db_supplier,
            message=f"Supplier '{db_supplier.name}' created successfully"
        )
    except Exception as e:
        db.rollback()
        return UnifiedResponse.error(f"Error creating supplier: {str(e)}")


@router.put("/suppliers/{supplier_id}")
async def update_supplier(supplier_id: str, supplier: SupplierUpdate, db: Session = Depends(get_db)):
    """Update a supplier"""
    try:
        db_supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not db_supplier:
            return UnifiedResponse.error("Supplier not found", status_code=404)

        update_data = supplier.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_supplier, field, value)

        db.commit()
        db.refresh(db_supplier)
        return UnifiedResponse.success(
            data=db_supplier,
            message=f"Supplier '{db_supplier.name}' updated successfully"
        )
    except Exception as e:
        db.rollback()
        return UnifiedResponse.error(f"Error updating supplier: {str(e)}")


@router.delete("/suppliers/{supplier_id}")
async def delete_supplier(supplier_id: str, db: Session = Depends(get_db)):
    """Delete a supplier if it has no dependent records"""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise UnifiedResponse.error("Supplier not found", status_code=404)

    # Check for dependent records that would block deletion
    dependency_checks = {
        "purchases": db.query(func.count(Purchase.id)).filter(Purchase.supplier_id == supplier_id).scalar(),
        "purchase_orders": db.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.supplier_id == supplier_id).scalar(),
        "products": db.query(func.count(Product.id)).filter(Product.supplier_id == supplier_id).scalar(),
    }

    blocking_dependencies = {k: v for k, v in dependency_checks.items() if v}
    if blocking_dependencies:
        detail_message = ", ".join(
            f"{count} {name.replace('_', ' ')}" for name, count in blocking_dependencies.items()
        )
        raise UnifiedResponse.error(
            message=(
                "Cannot delete supplier because there are related records that depend on it. "
                f"Remove the associated {detail_message} first."
            ),
            code="SUPPLIER_DELETE_BLOCKED",
            details={"dependencies": blocking_dependencies}
        )

    supplier_name = supplier.name
    try:
        db.delete(supplier)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise UnifiedResponse.error(
            message="Failed to delete supplier due to database constraints",
            code="SUPPLIER_DELETE_INTEGRITY_ERROR",
            details=str(exc.orig) if getattr(exc, "orig", None) else str(exc)
        )
    except Exception as exc:
        db.rollback()
        raise UnifiedResponse.error(
            message="Error deleting supplier",
            code="SUPPLIER_DELETE_ERROR",
            details=str(exc)
        )

    return UnifiedResponse.success(
        data={"id": supplier_id, "name": supplier_name},
        message=f"Supplier '{supplier_name}' deleted successfully"
    )


@router.get("", response_model=List[PurchaseResponse])
@router.get("/", response_model=List[PurchaseResponse])
async def get_purchases(
    skip: int = 0,
    limit: int = 100,
    supplier_id: Optional[str] = None,
    branch_id: Optional[str] = None,
    status: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    start_date: Optional[date] = Query(None, alias="start_date"),
    end_date: Optional[date] = Query(None, alias="end_date"),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get all purchases with optional filtering"""
    try:
        query = (
            db.query(Purchase)
            .options(
                joinedload(Purchase.supplier),
                joinedload(Purchase.purchase_items)
            )
            .join(Supplier)
        )

        # Apply filters
        if supplier_id:
            query = query.filter(Purchase.supplier_id == supplier_id)

        if branch_id:
            query = query.filter(Purchase.branch_id == branch_id)

        if status:
            query = query.filter(Purchase.status == status)

        date_from = from_date or start_date
        date_to = to_date or end_date

        if date_from:
            query = query.filter(Purchase.purchase_date >= date_from)

        if date_to:
            query = query.filter(Purchase.purchase_date <= date_to)

        if search:
            query = query.filter(
                or_(
                    Supplier.name.ilike(f"%{search}%"),
                    Purchase.reference.ilike(f"%{search}%"),
                    Purchase.notes.ilike(f"%{search}%")
                )
            )

        purchases = query.order_by(desc(Purchase.purchase_date)).offset(skip).limit(limit).all()
        return purchases
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching purchases: {str(e)}")


@router.get("/by-id/{purchase_id}")
async def get_purchase_by_id(
    purchase_id: str,
    db: Session = Depends(get_db)
):
    """Get a single purchase by ID with all details"""
    print(f"[DEBUG purchases.py v2025.10.19.22.43] Getting purchase {purchase_id}")
    try:
        from app.models.user import User
        purchase = (
            db.query(Purchase)
            .options(
                joinedload(Purchase.supplier),
                joinedload(Purchase.purchase_items).joinedload(PurchaseItem.product),
                joinedload(Purchase.branch)
            )
            .filter(Purchase.id == purchase_id)
            .first()
        )

        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")

        # Build response dict manually to include computed fields
        branch_name = None
        if purchase.branch:
            branch_name = purchase.branch.name

        created_by_name = None
        if purchase.created_by:
            creator = db.query(User).filter(User.id == purchase.created_by).first()
            if creator:
                parts = [p for p in [creator.first_name, creator.last_name] if p]
                created_by_name = " ".join(parts) if parts else creator.username

        # Convert purchase to dict
        result = {
            "id": purchase.id,
            "supplier_id": purchase.supplier_id,
            "reference": purchase.reference,
            "purchase_date": purchase.purchase_date.isoformat() if purchase.purchase_date else None,
            "due_date": purchase.due_date.isoformat() if purchase.due_date else None,
            "status": purchase.status,
            "total_amount": float(purchase.total_amount or 0),
            "total_vat_amount": float(purchase.total_vat_amount or 0),
            "total_amount_ex_vat": float(purchase.total_amount_ex_vat or 0),
            "amount_paid": float(purchase.amount_paid or 0),
            "notes": purchase.notes,
            "branch_id": purchase.branch_id,
            "created_at": purchase.created_at.isoformat() if purchase.created_at else None,
            "updated_at": purchase.updated_at.isoformat() if purchase.updated_at else None,
            "branch_name": branch_name,
            "created_by_name": created_by_name,
            "supplier": {
                "id": purchase.supplier.id,
                "name": purchase.supplier.name,
                "email": purchase.supplier.email,
                # FIXED: Using telephone field (not phone) - v2025.10.19.22.35
                "phone": purchase.supplier.telephone,
                "address": purchase.supplier.address,
            } if purchase.supplier else None,
            "purchase_items": [
                {
                    "id": item.id,
                    "product_id": item.product_id,
                    "product_name": item.product.name if item.product else None,
                    "product_sku": item.product.sku if item.product else None,
                    "description": item.description,
                    "quantity": float(item.quantity or 0),
                    "cost": float(item.cost or 0),
                    "unit_cost": float(item.cost or 0),
                    "total_cost": float(item.total_cost or 0),
                    "vat_rate": float(item.vat_rate or 0),
                    "vat_amount": float(item.vat_amount or 0),
                    "is_asset": item.is_asset or False,
                    "is_inventory": item.is_inventory or False,
                } for item in (purchase.purchase_items or [])
            ]
        }

        return result
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_log = f"Error fetching purchase {purchase_id}: {e}\n{traceback.format_exc()}"
        print(error_log)
        # Also write to file for debugging
        with open("purchase_error.log", "a") as f:
            import datetime
            f.write(f"\n\n=== {datetime.datetime.now()} ===\n{error_log}\n")
        raise HTTPException(status_code=500, detail=f"Error fetching purchase: {str(e)}")


# NOTE: The GET "/{purchase_id}" route is declared later in this file, after static routes like
# "/products" and "/dashboard-stats" to avoid route shadowing issues.


@router.post("", response_model=PurchaseResponse)
@router.post("/", response_model=PurchaseResponse)
async def create_purchase(purchase: PurchaseCreate, db: Session = Depends(get_db)):
    """Create a new purchase with automatic accounting entries and optional landed costs"""
    try:
        print(f"==== PURCHASE CREATION DEBUG ====")
        print(f"Received purchase data: {purchase.model_dump()}")

        # Basic validation
        if not purchase.supplier_id or not purchase.purchase_date or not purchase.items:
            raise HTTPException(status_code=400, detail="Supplier, purchase date, and at least one item are required.")

        print(f"Basic validation passed")

        # Pop items and landed costs to handle them separately
        items_data = purchase.items
        processed_item_payloads = []
        landed_costs_data = purchase.landed_costs

        # Calculate totals from items with proper VAT handling
        total_amount_ex_vat = sum(item.quantity * item.cost for item in items_data)
        total_vat = 0

        # Calculate VAT based on the VAT calculation mode and individual item rates
        for item in items_data:
            line_total = item.quantity * item.cost
            vat_rate = item.vat_rate / 100 if item.vat_rate else 0

            # Calculate VAT amount per line item
            if vat_rate > 0:
                # Assuming exclusive VAT calculation by default (VAT is added to the cost)
                line_vat = Decimal(str(line_total * vat_rate))
                total_vat += line_vat

        # Add landed costs to totals (landed costs are typically VAT-free)
        if landed_costs_data:
            total_amount_ex_vat += Decimal(str(sum(lc.amount for lc in landed_costs_data)))

        # Calculate grand total
        grand_total = total_amount_ex_vat + total_vat

        # Create Purchase object from schema, excluding items, landed costs, and payment fields
        purchase_dict = purchase.model_dump(exclude={
            'items', 'landed_costs', 'payment_method', 'payment_source_id',
            'payment_source_type', 'payment_reference', 'expense_account_id', 'vat_account_id'
        })
        purchase_dict['total_amount'] = grand_total
        purchase_dict['total_vat_amount'] = total_vat
        purchase_dict['total_amount_ex_vat'] = total_amount_ex_vat

        # Set default branch_id if not provided
        if 'branch_id' not in purchase_dict or not purchase_dict['branch_id']:
            # Get the first available branch as default
            from app.models.branch import Branch
            default_branch = db.query(Branch).filter(Branch.active == True).first()
            if default_branch:
                purchase_dict['branch_id'] = default_branch.id
                print(f"Using default branch: {default_branch.name} ({default_branch.id})")

        db_purchase = Purchase(**purchase_dict)
        db.add(db_purchase)
        db.flush()  # Flush to get the purchase ID

        # Process each purchase item
        for item_data in items_data:
            item_dict = item_data.model_dump()
            # Track normalized payload for follow-up processing (e.g., asset creation)
            normalized_payload = item_dict.copy()

            is_asset = bool(item_dict.get('is_asset'))
            if is_asset:
                # Assets should never be treated as inventory lines
                item_dict['is_inventory'] = False
                normalized_payload['is_inventory'] = False
                # Normalize asset category to enumeration-friendly uppercase value
                normalized_payload['asset_category'] = normalize_asset_category(item_dict.get('asset_category'))
                item_dict['asset_category'] = normalized_payload['asset_category']
                # Ensure depreciation method is always lower-case for service consumption
                if normalized_payload.get('asset_depreciation_method'):
                    method = str(normalized_payload['asset_depreciation_method']).lower()
                    normalized_payload['asset_depreciation_method'] = method
                    item_dict['asset_depreciation_method'] = method
            else:
                # Default to inventory when flag not supplied
                if 'is_inventory' not in item_dict:
                    item_dict['is_inventory'] = True
                normalized_payload['is_inventory'] = item_dict['is_inventory']

            item_dict['purchase_id'] = db_purchase.id

            # Derive total_cost if missing (quantity * cost)
            if not item_dict.get('total_cost') and item_dict.get('quantity') is not None and item_dict.get('cost') is not None:
                try:
                    item_dict['total_cost'] = item_dict['quantity'] * item_dict['cost']
                    normalized_payload['total_cost'] = item_dict['total_cost']
                except Exception:
                    # Fallback: ignore if calculation fails
                    pass

            db_item = PurchaseItem(**item_dict)
            db.add(db_item)
            db.flush()  # ensure the purchase item has an ID for downstream processing
            normalized_payload['purchase_item_id'] = db_item.id
            processed_item_payloads.append(normalized_payload)

        # Handle landed costs if present
        if landed_costs_data:
            landed_cost_service = LandedCostService(db)
            landed_cost_payload = {
                "purchase_id": db_purchase.id,
                "reference": f"LC for Purchase {db_purchase.reference or db_purchase.id}",
                "supplier_id": db_purchase.supplier_id,
                "date": db_purchase.purchase_date,
                "items": [lc.model_dump() for lc in landed_costs_data]
            }
            try:
                landed_cost_service.create_landed_cost(landed_cost_payload)
            except Exception as lc_error:
                print(f"Warning: Failed to create landed cost document for purchase {db_purchase.id}: {lc_error}")

        # Commit the purchase and its items
        db.commit()
        db.refresh(db_purchase)

        # --- Post-creation processing: Accounting and Inventory ---

        # 1. Create journal entries for the purchase itself (Dr. Inventory/Expense, Cr. A/P)
        try:
            print(f"Creating journal entries for purchase {db_purchase.id}")
            ifrs_service = IFRSAccountingService(db)
            journal_entries = ifrs_service.create_purchase_journal_entries(db_purchase)
            print(f"Successfully created {len(journal_entries)} main journal entries for purchase {db_purchase.id}")
        except Exception as accounting_error:
            print(f"Warning: Failed to create main accounting entries for purchase {db_purchase.id}: {accounting_error}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")

        # 2. If an initial payment was made, create payment journal entries and update balances
        if purchase.amount_paid and purchase.amount_paid > 0:
            try:
                ifrs_service = IFRSAccountingService(db)

                # Determine payment account based on payment source
                payment_account_id = None
                if purchase.payment_source_type == 'bank' and purchase.payment_source_id:
                    # For bank accounts, use the bank_account_id in the payment details
                    payment_account_id = purchase.payment_source_id
                elif purchase.payment_source_type == 'cash' and purchase.payment_source_id:
                    # For cash accounts, the payment_source_id is the accounting code ID
                    payment_account_id = purchase.payment_source_id
                elif purchase.bank_account_id:
                    # Legacy support
                    payment_account_id = purchase.bank_account_id

                payment_details = {
                    "purchase_id": db_purchase.id,
                    "amount": purchase.amount_paid,
                    "payment_date": db_purchase.purchase_date,
                    "payment_account_id": payment_account_id,
                    "payment_source_type": purchase.payment_source_type or 'bank',
                    "payment_reference": purchase.payment_reference,
                    "branch_id": db_purchase.branch_id,
                    "supplier_id": db_purchase.supplier_id,
                }

                # Create journal entries for payment
                payment_journal_entries = ifrs_service.create_purchase_payment_journal_entries(
                    purchase=db_purchase,
                    payment_amount=purchase.amount_paid,
                    payment_date=db_purchase.purchase_date,
                    bank_account_id=payment_account_id
                )
                print(f"Successfully created {len(payment_journal_entries)} payment journal entries for purchase {db_purchase.id}")

                # Create bank transaction record for bank payments
                if purchase.payment_source_type == 'bank' and purchase.payment_source_id:
                    from app.models.banking import BankTransaction
                    bank_transaction = BankTransaction(
                        bank_account_id=purchase.payment_source_id,
                        date=db_purchase.purchase_date,
                        amount=-purchase.amount_paid,  # Negative for outflow
                        description=f"Purchase payment - {purchase.payment_reference or db_purchase.reference or db_purchase.id}",
                        transaction_type='purchase_payment',
                        reference=purchase.payment_reference or db_purchase.reference,
                        reconciled=False
                    )
                    db.add(bank_transaction)

                # Update account balances
                if purchase.payment_source_type == 'bank' and purchase.payment_source_id:
                    # Update bank account balance
                    from app.models.banking import BankAccount
                    bank_account = db.query(BankAccount).filter(BankAccount.id == purchase.payment_source_id).first()
                    if bank_account:
                        bank_account.balance = (bank_account.balance or 0) - purchase.amount_paid
                        print(f"Updated bank account {bank_account.name} balance: {bank_account.balance}")

                elif purchase.payment_source_type == 'cash' and purchase.payment_source_id:
                    # Update cash account balance in accounting codes
                    from app.models.accounting import AccountingCode
                    cash_account = db.query(AccountingCode).filter(AccountingCode.id == purchase.payment_source_id).first()
                    if cash_account:
                        cash_account.total_credits = (cash_account.total_credits or 0) + purchase.amount_paid
                        cash_account.update_balance()
                        print(f"Updated cash account {cash_account.name} balance: {cash_account.balance}")

                # Commit balance updates
                db.commit()
                print(f"Successfully created journal entries and updated balances for payment of purchase {db_purchase.id}")

            except Exception as payment_je_error:
                print(f"Warning: Failed to create journal entries for initial payment of purchase {db_purchase.id}: {payment_je_error}")
                db.rollback()

        # 3. Create immediate inventory adjustments for all purchases
        # This ensures inventory is updated when purchase is created, not just when received
        try:
            from app.services.inventory_service import InventoryService
            inventory_service = InventoryService(db)
            asset_service = AssetManagementService(db)

            # Prepare quick lookup for processed payloads keyed by purchase item ID
            processed_lookup = {
                payload['purchase_item_id']: payload for payload in processed_item_payloads if payload.get('purchase_item_id')
            }

            # Ensure a PPE account exists so assets can be tagged correctly
            from app.models.accounting import AccountingCode
            ppe_account = db.query(AccountingCode).filter(AccountingCode.reporting_tag == 'A2.1').first()
            if not ppe_account:
                try:
                    ifrs_helper = IFRSAccountingService(db)
                    ppe_account = (
                        ifrs_helper._get_accounting_code_by_ifrs_tag('A2.1') or
                        ifrs_helper._get_default_accounting_code('Property, Plant and Equipment', 'Asset')
                    )
                except Exception:
                    ppe_account = None

            for item in db_purchase.purchase_items:
                payload = processed_lookup.get(item.id, {})
                if getattr(item, 'is_asset', False):
                    # Ensure the asset remains mapped to a PPE account
                    if not item.asset_accounting_code_id and ppe_account:
                        item.asset_accounting_code_id = ppe_account.id

                    name = payload.get('asset_name') or item.asset_name or item.description or f"Asset from {db_purchase.id}"
                    category = payload.get('asset_category') or normalize_asset_category(item.asset_category or 'equipment')
                    depreciation_method = payload.get('asset_depreciation_method') or item.asset_depreciation_method or 'straight_line'
                    useful_life = payload.get('asset_useful_life_years') or item.asset_useful_life_years or 5
                    salvage_value = payload.get('asset_salvage_value') or item.asset_salvage_value or 0

                    quantity = payload.get('quantity') or item.quantity or 1
                    unit_cost = payload.get('cost') or item.cost or 0
                    total_cost = payload.get('total_cost') or item.total_cost or (quantity * unit_cost)

                    asset_payload = {
                        'name': name,
                        'category': category,
                        'purchase_date': db_purchase.purchase_date,
                        'purchase_cost': float(total_cost or 0),
                        'current_value': float(total_cost or 0),
                        'salvage_value': float(salvage_value or 0),
                        'depreciation_method': depreciation_method,
                        'useful_life_years': int(useful_life or 0) or 5,
                        'serial_number': payload.get('asset_serial_number') or item.asset_serial_number,
                        'vehicle_registration': payload.get('asset_vehicle_registration') or item.asset_vehicle_registration,
                        'engine_number': payload.get('asset_engine_number') or item.asset_engine_number,
                        'chassis_number': payload.get('asset_chassis_number') or item.asset_chassis_number,
                        'accounting_code_id': item.asset_accounting_code_id or (ppe_account.id if ppe_account else None),
                        'branch_id': db_purchase.branch_id,
                        'supplier_id': db_purchase.supplier_id,
                        'notes': payload.get('asset_notes') or item.asset_notes or f"Created from purchase {db_purchase.reference or db_purchase.id}",
                        'ifrs_category': 'PPE_IAS_16',
                        # Accounting entry already handled by the purchase journal
                        'skip_accounting_entry': True
                    }

                    # Normalize category via helper to align with enum expectations
                    asset_payload['category'] = normalize_asset_category(asset_payload.get('category'))

                    try:
                        asset_service.create_asset(asset_payload)
                    except Exception as asset_error:
                        print(f"Warning: Failed to create asset for purchase item {item.id}: {asset_error}")
                elif getattr(item, 'is_inventory', False) and item.product_id:
                    # DEBUG: Get product quantity before update
                    from app.models.product import Product
                    product_before = db.query(Product).filter(Product.id == item.product_id).first()
                    qty_before = product_before.quantity if product_before else 0
                    print(f"🔍 DEBUG: Product {item.product_id} quantity BEFORE: {qty_before}, adding: {item.quantity}")

                    # Update product quantity (this also creates the InventoryTransaction internally)
                    # REMOVED duplicate InventoryTransaction creation - the service method creates it
                    success, message = inventory_service.update_product_quantity(
                        product_id=item.product_id,
                        quantity_change=item.quantity,
                        transaction_type='goods_receipt',
                        reference=f"Purchase {db_purchase.reference or db_purchase.id}",
                        branch_id=db_purchase.branch_id,
                        related_purchase_id=db_purchase.id
                    )

                    # DEBUG: Get product quantity after update
                    product_after = db.query(Product).filter(Product.id == item.product_id).first()
                    qty_after = product_after.quantity if product_after else 0
                    expected = qty_before + item.quantity
                    print(f"🔍 DEBUG: Product {item.product_id} quantity AFTER: {qty_after}, expected: {expected}")

                    if success:
                        print(f"✓ Updated inventory for {item.product.name if item.product else 'Product'}: +{item.quantity} units")
                    else:
                        print(f"⚠ Warning updating inventory for product {item.product_id}: {message}")

            db.commit()
            print(f"✓ Inventory adjustments completed for purchase {db_purchase.id}")
        except Exception as inventory_error:
            print(f"⚠ Warning: Failed to create inventory adjustments for purchase {db_purchase.id}: {inventory_error}")
            # Don't rollback the entire purchase for inventory issues
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")

        return db_purchase
    except Exception as e:
        db.rollback()
        print(f"Error creating purchase: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.put("/{purchase_id}", response_model=PurchaseResponse)
async def update_purchase(purchase_id: str, purchase: PurchaseUpdate, db: Session = Depends(get_db)):
    """Update a purchase"""
    try:
        db_purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
        if not db_purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")

        update_data = purchase.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_purchase, field, value)

        db.commit()
        db.refresh(db_purchase)
        return db_purchase
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating purchase: {str(e)}")


@router.post("/{purchase_id}/payment")
async def record_purchase_payment(
    purchase_id: str,
    payment_data: dict,
    db: Session = Depends(get_db)
):
    """Record a payment against a purchase"""
    try:
        # Get the purchase
        purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")

        # Extract payment details
        payment_amount = Decimal(str(payment_data.get('amount', 0)))
        payment_method = payment_data.get('payment_method', 'bank_transfer')
        payment_date = payment_data.get('payment_date')
        reference = payment_data.get('reference', '')
        notes = payment_data.get('notes', '')

        # Validate payment amount
        if payment_amount <= 0:
            raise HTTPException(status_code=400, detail="Payment amount must be greater than 0")

        # Calculate new amount_paid
        current_amount_paid = purchase.amount_paid or Decimal('0')
        new_amount_paid = current_amount_paid + payment_amount

        # Check if payment doesn't exceed total amount
        if new_amount_paid > purchase.total_amount:
            raise HTTPException(
                status_code=400,
                detail=f"Payment amount ({payment_amount}) would exceed remaining balance"
            )

        # Persist payment record and create journals
        from app.models.purchase_payments import PurchasePayment
        from app.services.ifrs_accounting_service import IFRSAccountingService
        from app.models.banking import BankTransaction, BankAccount
        from app.models.accounting import AccountingCode

        payment_record = PurchasePayment(
            purchase_id=purchase.id,
            amount=payment_amount,
            payment_date=payment_date or date.today(),
            payment_method=payment_method,
            reference=reference,
            notes=notes,
            branch_id=purchase.branch_id
        )
        db.add(payment_record)
        db.flush()

        # Update purchase aggregates
        purchase.amount_paid = new_amount_paid
        if new_amount_paid >= purchase.total_amount:
            purchase.status = 'paid'
        elif new_amount_paid > 0:
            purchase.status = 'partially_paid'

        # Commit core payment and purchase updates first
        db.commit()
        db.refresh(purchase)

        # Best-effort: create journals and update balances without failing the whole request
        journal_entries_response = []
        try:
            ifrs_service = IFRSAccountingService(db)
            bank_account_id = None
            cash_account_id = None
            if payment_method in ['bank', 'bank_transfer'] and payment_data.get('payment_source_id'):
                bank_account_id = payment_data.get('payment_source_id')
            elif payment_method in ['cash'] and payment_data.get('payment_source_id'):
                cash_account_id = payment_data.get('payment_source_id')

            payment_journals = ifrs_service.create_purchase_payment_journal_entries(
                purchase=purchase,
                payment_amount=payment_amount,
                payment_date=payment_record.payment_date,
                bank_account_id=bank_account_id
            )

            # Bank transaction or cash accounting code balance update
            if bank_account_id:
                bank_acc = db.query(BankAccount).filter(BankAccount.id == bank_account_id).first()
                if bank_acc:
                    bank_tx = BankTransaction(
                        bank_account_id=bank_account_id,
                        date=payment_record.payment_date,
                        amount=-payment_amount,
                        description=f"Purchase payment - {reference or purchase.reference or purchase.id}",
                        transaction_type='purchase_payment',
                        reference=reference or purchase.reference,
                        reconciled=False
                    )
                    db.add(bank_tx)
                    bank_acc.balance = (bank_acc.balance or 0) - payment_amount
            elif cash_account_id:
                cash_code = db.query(AccountingCode).filter(AccountingCode.id == cash_account_id).first()
                if cash_code:
                    cash_code.total_credits = (cash_code.total_credits or 0) + payment_amount
                    cash_code.update_balance()

            db.commit()
            journal_entries_response = [
                {
                    'id': je.id,
                    'debit': float(je.debit_amount),
                    'credit': float(je.credit_amount),
                    'account': je.accounting_code.code if je.accounting_code else None,
                    'description': je.description
                } for je in payment_journals
            ]
        except Exception as je_err:
            # Log and move on
            print(f"Warning: Failed to create payment journals/updates for purchase {purchase.id}: {je_err}")
            db.rollback()

        return {
            "message": "Payment recorded successfully",
            "purchase_id": purchase_id,
            "payment_amount": float(payment_amount),
            "total_paid": float(new_amount_paid),
            "remaining_balance": float(purchase.total_amount - new_amount_paid),
            "status": purchase.status,
            "journal_entries": journal_entries_response
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error recording payment: {str(e)}")


@router.post("/bulk-payment")
async def bulk_record_payments(
    payment_data: dict,
    db: Session = Depends(get_db)
):
    """Record payments for multiple purchases"""
    try:
        purchase_payments = payment_data.get('payments', [])
        common_data = payment_data.get('common', {})

        if not purchase_payments:
            raise HTTPException(status_code=400, detail="No payments provided")

        results = []
        errors = []

        for payment in purchase_payments:
            try:
                purchase_id = payment.get('purchase_id')
                amount = Decimal(str(payment.get('amount', 0)))

                # Use common data if specific data not provided
                payment_date = payment.get('payment_date') or common_data.get('payment_date')
                payment_method = payment.get('payment_method') or common_data.get('payment_method', 'bank_transfer')
                reference = payment.get('reference') or common_data.get('reference', '')
                notes = payment.get('notes') or common_data.get('notes', '')

                # Get the purchase
                purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
                if not purchase:
                    errors.append(f"Purchase {purchase_id} not found")
                    continue

                # Validate payment amount
                if amount <= 0:
                    errors.append(f"Invalid payment amount for purchase {purchase_id}")
                    continue

                # Calculate new amount_paid
                current_amount_paid = purchase.amount_paid or Decimal('0')
                new_amount_paid = current_amount_paid + amount

                # Check if payment doesn't exceed total amount
                if new_amount_paid > purchase.total_amount:
                    errors.append(f"Payment for purchase {purchase_id} would exceed remaining balance")
                    continue

                # Update purchase amount_paid
                purchase.amount_paid = new_amount_paid

                # Update status based on payment
                if new_amount_paid >= purchase.total_amount:
                    purchase.status = 'paid'
                elif new_amount_paid > 0:
                    purchase.status = 'partially_paid'

                results.append({
                    "purchase_id": purchase_id,
                    "payment_amount": float(amount),
                    "total_paid": float(new_amount_paid),
                    "remaining_balance": float(purchase.total_amount - new_amount_paid),
                    "status": purchase.status
                })

            except Exception as payment_error:
                errors.append(f"Error processing payment for purchase {payment.get('purchase_id', 'unknown')}: {str(payment_error)}")

        db.commit()

        return {
            "message": f"Processed {len(results)} payments successfully",
            "successful_payments": results,
            "errors": errors,
            "total_processed": len(results),
            "total_errors": len(errors)
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing bulk payments: {str(e)}")


@router.get("/{purchase_id}/payment-history")
async def get_payment_history(purchase_id: str, db: Session = Depends(get_db)):
    """Get payment history for a purchase"""
    try:
        purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")

        # For now, return basic payment info
        # In a full implementation, you'd have a separate payments table
        return {
            "purchase_id": purchase_id,
            "total_amount": float(purchase.total_amount),
            "amount_paid": float(purchase.amount_paid or 0),
            "remaining_balance": float(purchase.total_amount - (purchase.amount_paid or 0)),
            "status": purchase.status,
            "payments": [
                # This would be populated from a payments table
                # For now, showing summary only
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching payment history: {str(e)}")


@router.get("/purchase-items/{item_id}", response_model=PurchaseItemResponse)
async def get_purchase_item(item_id: str, db: Session = Depends(get_db)):
    """Fetch a single purchase item (includes extended asset metadata)."""
    db_item = db.query(PurchaseItem).filter(PurchaseItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Purchase item not found")
    return db_item


@router.put("/purchase-items/{item_id}", response_model=PurchaseItemResponse)
async def update_purchase_item(item_id: str, item_update: PurchaseItemUpdate, db: Session = Depends(get_db)):
    """Update a single purchase item including extended asset metadata and return full record."""
    try:
        db_item = db.query(PurchaseItem).filter(PurchaseItem.id == item_id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail="Purchase item not found")

        update_data = item_update.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_item, field, value)

        db.commit()
        db.refresh(db_item)
        return db_item
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error updating purchase item: {str(e)}")


@router.delete("/{purchase_id}")
async def delete_purchase(purchase_id: str, db: Session = Depends(get_db)):
    """Delete a purchase"""
    try:
        purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")

        # Business rule: prevent deleting purchases that have been received or have payments
        protected_statuses = {"received", "partially_paid", "paid"}
        if (purchase.status in protected_statuses) or (purchase.amount_paid and purchase.amount_paid > 0):
            raise HTTPException(
                status_code=409,
                detail="Cannot delete a purchase that is received or has payments. Reverse receipts/payments first."
            )

        print(f"Deleting purchase {purchase_id} and related records...")

        # Delete related purchase items first
        purchase_items = db.query(PurchaseItem).filter(PurchaseItem.purchase_id == purchase_id).all()
        print(f"Found {len(purchase_items)} purchase items to delete")
        for item in purchase_items:
            db.delete(item)

        # Delete related inventory transactions
        from app.models.inventory import InventoryTransaction
        inventory_transactions = db.query(InventoryTransaction).filter(
            InventoryTransaction.related_purchase_id == purchase_id
        ).all()
        print(f"Found {len(inventory_transactions)} inventory transactions to delete")
        for transaction in inventory_transactions:
            db.delete(transaction)

        # Delete related journal entries (if any reference this purchase)
        from app.models.accounting import JournalEntry
        journal_entries = db.query(JournalEntry).filter(
            JournalEntry.reference == purchase_id
        ).all()
        print(f"Found {len(journal_entries)} journal entries to delete")
        for entry in journal_entries:
            db.delete(entry)

        # Delete related payments if any lingering zero/empty records exist (defensive)
        try:
            from app.models.purchase_payments import PurchasePayment
            payments = db.query(PurchasePayment).filter(PurchasePayment.purchase_id == purchase_id).all()
            for p in payments:
                db.delete(p)
        except Exception:
            # Do not fail deletion if payments model/records are unavailable
            pass

        # Now delete the purchase
        db.delete(purchase)
        db.commit()
        print(f"Successfully deleted purchase {purchase_id}")
        return {"message": "Purchase deleted successfully"}
    except Exception as e:
        db.rollback()
        print(f"Error deleting purchase {purchase_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting purchase: {str(e)}")


@router.get("/orders", response_model=List[dict])
async def get_purchase_orders(
    skip: int = 0,
    limit: int = 100,
    supplier_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get purchase orders with optional filtering"""
    try:
        query = db.query(PurchaseOrder)

        if supplier_id:
            query = query.filter(PurchaseOrder.supplier_id == supplier_id)

        if status:
            query = query.filter(PurchaseOrder.status == status)

        orders = query.order_by(desc(PurchaseOrder.date)).offset(skip).limit(limit).all()

        # Format response with supplier details
        result = []
        for order in orders:
            result.append({
                "id": order.id,
                "po_number": order.po_number,
                "date": order.date,
                "supplier_name": order.supplier.name if order.supplier else "Unknown",
                "status": order.status,
                "total_amount": float(order.total_amount) if order.total_amount else 0.0,
                "expected_delivery_date": order.expected_delivery_date,
                "notes": order.notes
            })

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching purchase orders: {str(e)}")


@router.get("/products")
async def get_products_for_purchase(db: Session = Depends(get_db)):
    """Get products available for purchasing"""
    try:
        products = db.query(Product).filter(Product.active == True).all()
        return [
            {
                "id": product.id,
                "name": product.name,
                "description": product.description,
                "current_cost": float(product.cost_price) if product.cost_price else 0.0,
                "selling_price": float(product.selling_price) if product.selling_price else 0.0,
                "stock_quantity": float(product.quantity) if product.quantity else 0.0,
                "unit_of_measure": product.unit_of_measure_id
            }
            for product in products
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")


@router.get("/dashboard-stats")
async def get_purchase_dashboard_stats(db: Session = Depends(get_db)):
    """Get purchase dashboard statistics"""
    try:
        from sqlalchemy import func
        from datetime import datetime, timedelta

        today = datetime.now().date()
        first_day_of_month = today.replace(day=1)

        # Total purchases this month
        total_this_month = db.query(func.sum(Purchase.total_amount)).filter(
            Purchase.purchase_date >= first_day_of_month
        ).scalar() or 0

        # Overall totals for compatibility with UI cards
        total_purchases_count = db.query(func.count(Purchase.id)).scalar() or 0
        total_amount_sum = db.query(func.sum(Purchase.total_amount)).scalar() or 0

        # Pending purchases count
        pending_count = db.query(func.count(Purchase.id)).filter(
            Purchase.status == "pending"
        ).scalar() or 0

        # Active suppliers count
        suppliers_count = db.query(func.count(Supplier.id)).filter(
            Supplier.active == True
        ).scalar() or 0

        # Recent purchases
        recent_purchases = db.query(Purchase).order_by(desc(Purchase.purchase_date)).limit(5).all()

        recent_data = []
        for purchase in recent_purchases:
            recent_data.append({
                "id": purchase.id,
                "date": purchase.purchase_date,
                "supplier_name": purchase.supplier.name if purchase.supplier else "Unknown",
                "amount": float(purchase.total_amount) if purchase.total_amount else 0.0,
                "status": purchase.status
            })



        # Preserve existing keys and add UI-expected aliases
        return {
            # Existing keys
            "total_this_month": float(total_this_month),
            "pending_purchases": int(pending_count),
            "active_suppliers": int(suppliers_count),
            "recent_purchases": recent_data,

            # UI-expected keys for purchases.html cards
            "total_purchases": int(total_purchases_count),
            "total_amount": float(total_amount_sum),
            "pending_orders": int(pending_count),
            "this_month": float(total_this_month),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching dashboard stats: {str(e)}")


# Dimensional Accounting GL Posting Endpoints ==============================

from pydantic import BaseModel
from app.utils.logger import get_logger, log_exception, log_error_with_context

logger = get_logger(__name__)
class GLPostingResponse(BaseModel):
    """Response for GL posting operations"""
    success: bool
    purchase_id: str
    entries_created: int
    journal_entry_ids: List[str]
    total_amount: float
    posting_date: str


class DimensionAccountingDetailsResponse(BaseModel):
    """Purchase accounting dimension details"""
    purchase_id: str
    reference: Optional[str] = None
    total_amount: float
    cost_center: Optional[str] = None
    project: Optional[str] = None
    department: Optional[str] = None
    expense_account: Optional[str] = None
    payable_account: Optional[str] = None
    posting_status: str
    last_posted_date: Optional[str] = None


class JournalEntryResponse(BaseModel):
    """Journal entry response"""
    id: str
    accounting_code: str
    debit_amount: float
    credit_amount: float
    description: str
    source: str
    entry_date: str
    dimensions: List[Dict] = []


class DimensionalAnalysisResponse(BaseModel):
    """Dimensional analysis for purchases"""
    total_expenses: float
    by_cost_center: Dict[str, float]
    by_project: Dict[str, float]
    by_department: Dict[str, float]


class ReconciliationResponse(BaseModel):
    """Reconciliation result"""
    period: str
    purchase_total: float
    gl_total: float
    variance: float
    is_reconciled: bool
    by_dimension: List[Dict] = []


@router.post("/purchases/{purchase_id}/post-accounting", response_model=GLPostingResponse, tags=["accounting"])
def post_purchase_to_accounting(
    purchase_id: str,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Post purchase to General Ledger with dimensional assignments.
    Creates Expense Debit and AP Credit entries with dimension tracking.
    """
    try:
        service = PurchaseService(db)
        result = service.post_purchase_to_accounting(purchase_id, user_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error posting to accounting: {str(e)}")


@router.get("/purchases/{purchase_id}/accounting-details", response_model=DimensionAccountingDetailsResponse, tags=["accounting"])
def get_purchase_accounting_details(
    purchase_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed accounting dimension information for a purchase.
    Shows cost center, project, department assignments and GL accounts.
    """
    try:
        purchase = db.query(Purchase).filter(Purchase.id == purchase_id).first()
        if not purchase:
            raise HTTPException(status_code=404, detail="Purchase not found")

        # Get dimension names
        cost_center_name = None
        project_name = None
        department_name = None

        if purchase.cost_center_id:
            cc = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == purchase.cost_center_id).first()
            cost_center_name = cc.value if cc else None

        if purchase.project_id:
            proj = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == purchase.project_id).first()
            project_name = proj.value if proj else None

        if purchase.department_id:
            dept = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == purchase.department_id).first()
            department_name = dept.value if dept else None

        return {
            'purchase_id': purchase.id,
            'reference': purchase.reference or '',
            'total_amount': float(purchase.total_amount or 0),
            'cost_center': cost_center_name,
            'project': project_name,
            'department': department_name,
            'expense_account': purchase.expense_account.code if purchase.expense_account else None,
            'payable_account': purchase.payable_account.code if purchase.payable_account else None,
            'posting_status': purchase.posting_status or 'draft',
            'last_posted_date': purchase.last_posted_date.isoformat() if purchase.last_posted_date else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/purchases/accounting-bridge", response_model=List[Dict], tags=["accounting"])
def get_purchases_accounting_bridge(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    posting_status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get the bridge table showing purchase-to-GL entry mappings.
    Useful for auditing and reconciliation.
    """
    try:
        query = db.query(Purchase)

        if start_date:
            query = query.filter(Purchase.purchase_date >= start_date)
        if end_date:
            query = query.filter(Purchase.purchase_date <= end_date)
        if posting_status:
            query = query.filter(Purchase.posting_status == posting_status)

        purchases = query.all()

        bridge_data = []
        for purchase in purchases:
            # Get related journal entries
            journal_entries = db.query(JournalEntry).filter(
                JournalEntry.reference.like(f"%PURCHASE-{purchase.id}%")
            ).all()

            bridge_data.append({
                'purchase_id': purchase.id,
                'reference': purchase.reference or '',
                'purchase_date': purchase.purchase_date.isoformat() if purchase.purchase_date else None,
                'total_amount': float(purchase.total_amount or 0),
                'posting_status': purchase.posting_status or 'draft',
                'journal_entry_count': len(journal_entries),
                'journal_entry_ids': [je.id for je in journal_entries],
                'cost_center_id': purchase.cost_center_id,
                'project_id': purchase.project_id,
                'department_id': purchase.department_id
            })

        return bridge_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/purchases/journal-entries", response_model=List[JournalEntryResponse], tags=["accounting"])
def get_purchases_journal_entries(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    source: str = Query("PURCHASES"),
    db: Session = Depends(get_db)
):
    """
    Get all journal entries for purchase transactions.
    Shows debit/credit entries with dimension assignments.
    Optimized with eager loading and name fields instead of UUIDs.
    """
    try:
        # Add eager loading for all relationships
        query = db.query(JournalEntry).options(
            joinedload(JournalEntry.accounting_code),
            joinedload(JournalEntry.accounting_entry),
            joinedload(JournalEntry.branch),
            joinedload(JournalEntry.ledger),
            joinedload(JournalEntry.dimension_assignments)
        ).filter(JournalEntry.source == source)

        if start_date:
            query = query.filter(JournalEntry.entry_date >= start_date)
        if end_date:
            query = query.filter(JournalEntry.entry_date <= end_date)

        entries = query.all()

        result = []
        for entry in entries:
            dimensions = []
            if entry.dimension_assignments:
                for dim_assign in entry.dimension_assignments:
                    dimensions.append({
                        'dimension_value_id': dim_assign.dimension_value_id,
                        'dimension_type': dim_assign.dimension_value.dimension.code if dim_assign.dimension_value and dim_assign.dimension_value.dimension else None,
                        'dimension_value': dim_assign.dimension_value.value if dim_assign.dimension_value else None
                    })

            result.append({
                'id': entry.id,
                'accounting_code': entry.accounting_code.code if entry.accounting_code else None,
                'accounting_code_name': entry.accounting_code.name if entry.accounting_code else None,
                'accounting_entry_id': entry.accounting_entry_id,
                'accounting_entry_particulars': entry.accounting_entry.particulars if entry.accounting_entry else None,
                'branch_id': entry.branch_id,
                'branch_name': entry.branch.name if entry.branch else None,
                'ledger_id': entry.ledger_id,
                'ledger_description': entry.ledger.description if entry.ledger else None,
                'debit_amount': float(entry.debit_amount or 0),
                'credit_amount': float(entry.credit_amount or 0),
                'description': entry.description or '',
                'source': entry.source or '',
                'entry_date': entry.entry_date.isoformat() if entry.entry_date else None,
                'dimensions': dimensions
            })

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/purchases/dimensional-analysis", response_model=DimensionalAnalysisResponse, tags=["accounting"])
def get_purchases_dimensional_analysis(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Analyze purchase expenses by accounting dimensions.
    Groups expenses by cost center, project, and department.
    """
    try:
        query = db.query(Purchase)

        if start_date:
            query = query.filter(Purchase.purchase_date >= start_date)
        if end_date:
            query = query.filter(Purchase.purchase_date <= end_date)

        purchases = query.all()

        total_expenses = Decimal('0')
        by_cost_center = {}
        by_project = {}
        by_department = {}

        for purchase in purchases:
            amount = Decimal(str(purchase.total_amount or 0))
            total_expenses += amount

            # Group by cost center
            if purchase.cost_center_id:
                cc = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == purchase.cost_center_id).first()
                cc_name = cc.value if cc else 'Unknown'
                by_cost_center[cc_name] = float(by_cost_center.get(cc_name, Decimal('0')) + amount)

            # Group by project
            if purchase.project_id:
                proj = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == purchase.project_id).first()
                proj_name = proj.value if proj else 'Unknown'
                by_project[proj_name] = float(by_project.get(proj_name, Decimal('0')) + amount)

            # Group by department
            if purchase.department_id:
                dept = db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == purchase.department_id).first()
                dept_name = dept.value if dept else 'Unknown'
                by_department[dept_name] = float(by_department.get(dept_name, Decimal('0')) + amount)

        return {
            'total_expenses': float(total_expenses),
            'by_cost_center': by_cost_center,
            'by_project': by_project,
            'by_department': by_department
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/purchases/reconcile", response_model=ReconciliationResponse, tags=["accounting"])
def reconcile_purchases(
    period: str = Query(..., description="Period in YYYY-MM format"),
    db: Session = Depends(get_db)
):
    """
    Reconcile purchases against GL entries by dimension.
    Returns variance analysis to identify discrepancies.
    """
    try:
        service = PurchaseService(db)
        result = service.reconcile_purchases_by_dimension(period)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
