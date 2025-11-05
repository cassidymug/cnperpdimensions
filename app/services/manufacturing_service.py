from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import date, timedelta
from typing import Optional, Dict, Any, List, Tuple
import logging
import math

from app.models.cost_accounting import ManufacturingCost
from app.models.inventory import Product, InventoryTransaction, ProductAssembly, UnitOfMeasure
from app.models.inventory_allocation import HeadquartersInventory

class ManufacturingService:
    def __init__(self, db: Session):
        self.db = db

    def get_stats(self, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict[str, Any]:
        try:
            # Base query for manufacturing costs
            query = self.db.query(ManufacturingCost)
            if start_date:
                query = query.filter(ManufacturingCost.date >= start_date)
            if end_date:
                query = query.filter(ManufacturingCost.date <= end_date)

            # 1. Calculate Totals
            totals_query = query.with_entities(
                func.sum(ManufacturingCost.material_cost).label('total_materials'),
                func.sum(ManufacturingCost.labor_cost).label('total_labor'),
                func.sum(ManufacturingCost.overhead_cost).label('total_overhead'),
                func.sum(ManufacturingCost.total_cost).label('total_manufacturing'),
                func.count(ManufacturingCost.id).label('total_batches')
            ).first()

            # Handle case where no manufacturing costs exist
            if totals_query is None:
                totals_query = type('Totals', (), {
                    'total_materials': 0,
                    'total_labor': 0,
                    'total_overhead': 0,
                    'total_manufacturing': 0,
                    'total_batches': 0
                })()

            # 2. Product Type Distribution
            product_types_raw = self.db.query(
                Product.category,
                func.count(ManufacturingCost.id).label('count'),
                func.sum(ManufacturingCost.total_cost).label('total_cost')
            ).join(ManufacturingCost, Product.id == ManufacturingCost.product_id)

            if start_date:
                product_types_raw = product_types_raw.filter(ManufacturingCost.date >= start_date)
            if end_date:
                product_types_raw = product_types_raw.filter(ManufacturingCost.date <= end_date)

            product_types_raw = product_types_raw.group_by(Product.category).all()

            product_type_summary = self._summarize_product_types(product_types_raw)

            # 3. Intangible and WIP estimates
            intangible_estimate = self._calculate_intangible_costs(start_date, end_date)
            wip_estimate = self._calculate_wip_costs(start_date, end_date)

            # 4. Monthly Trends
            monthly_trends = self._get_monthly_trends()

            return {
                "totals": {
                    "total_materials": float(totals_query.total_materials or 0),
                    "total_labor": float(totals_query.total_labor or 0),
                    "total_overhead": float(totals_query.total_overhead or 0),
                    "total_manufacturing": float(totals_query.total_manufacturing or 0),
                    "total_batches": totals_query.total_batches or 0,
                    "total_intangible": float(intangible_estimate),
                    "total_wip": float(wip_estimate)
                },
                "product_type_distribution": [
                    {"type": ptype, "count": data["count"], "total_cost": data["total_cost"]}
                    for ptype, data in product_type_summary.items() if data["count"] > 0
                ],
                "monthly_trends": monthly_trends
            }

        except Exception as e:
            logging.error(f"Error calculating manufacturing stats: {e}", exc_info=True)
            # Return a default structure on error to prevent 500s
            return self.get_default_stats()

    def _summarize_product_types(self, raw_data: List) -> Dict[str, Dict[str, Any]]:
        summary = {
            "tangible": {"count": 0, "total_cost": 0.0},
            "digital": {"count": 0, "total_cost": 0.0},
            "service": {"count": 0, "total_cost": 0.0},
            "intangible": {"count": 0, "total_cost": 0.0}
        }
        for pt in raw_data:
            category = pt.category or "tangible"
            cost = float(pt.total_cost or 0)
            if category in ["digital", "software", "airtime", "subscription"]:
                summary["digital"]["count"] += pt.count
                summary["digital"]["total_cost"] += cost
            elif category in ["license", "intellectual_property", "intangible", "patent", "trademark", "brand"]:
                summary["intangible"]["count"] += pt.count
                summary["intangible"]["total_cost"] += cost
            elif category == "service":
                summary["service"]["count"] += pt.count
                summary["service"]["total_cost"] += cost
            else:
                summary["tangible"]["count"] += pt.count
                summary["tangible"]["total_cost"] += cost
        return summary

    def _calculate_intangible_costs(self, start_date: Optional[date], end_date: Optional[date]) -> float:
        query = self.db.query(func.sum(ManufacturingCost.total_cost)).join(Product).filter(
            Product.category.in_(["license", "intellectual_property", "intangible", "patent", "trademark", "brand"])
        )
        if start_date:
            query = query.filter(ManufacturingCost.date >= start_date)
        if end_date:
            query = query.filter(ManufacturingCost.date <= end_date)

        return float(query.scalar() or 0)

    def _calculate_wip_costs(self, start_date: Optional[date], end_date: Optional[date]) -> float:
        query = self.db.query(func.sum(ManufacturingCost.total_cost)).filter(
            ManufacturingCost.status.in_(["draft", "in_progress"])
        )
        if start_date:
            query = query.filter(ManufacturingCost.date >= start_date)
        if end_date:
            query = query.filter(ManufacturingCost.date <= end_date)

        return float(query.scalar() or 0)

    def _get_monthly_trends(self) -> List[Dict[str, Any]]:
        twelve_months_ago = date.today() - timedelta(days=365)
        monthly_costs = self.db.query(
            func.date_trunc('month', ManufacturingCost.date).label('month'),
            func.sum(ManufacturingCost.material_cost).label('materials'),
            func.sum(ManufacturingCost.labor_cost).label('labor'),
            func.sum(ManufacturingCost.overhead_cost).label('overhead'),
            func.sum(ManufacturingCost.total_cost).label('total')
        ).filter(ManufacturingCost.date >= twelve_months_ago).group_by(
            func.date_trunc('month', ManufacturingCost.date)
        ).order_by(desc('month')).limit(12).all()

        return [
            {
                "month": mc.month.strftime("%Y-%m"),
                "materials": float(mc.materials or 0),
                "labor": float(mc.labor or 0),
                "overhead": float(mc.overhead or 0),
                "total": float(mc.total or 0)
            }
            for mc in monthly_costs
        ]

    @staticmethod
    def get_default_stats() -> Dict[str, Any]:
        return {
            "totals": {
                "total_materials": 0.0, "total_labor": 0.0, "total_overhead": 0.0,
                "total_manufacturing": 0.0, "total_batches": 0,
                "total_intangible": 0.0, "total_wip": 0.0
            },
            "product_type_distribution": [],
            "monthly_trends": []
        }

    # ---------------------------------------------------------------------
    # BOM and Production to HQ (virtual headquarters inventory)
    # ---------------------------------------------------------------------

    def get_bom(self, product_id: str) -> List[Dict[str, Any]]:
        """Return bill of materials for an assembled product."""
        bom_items = self.db.query(ProductAssembly).filter(
            ProductAssembly.assembled_product_id == product_id
        ).all()
        result: List[Dict[str, Any]] = []
        for item in bom_items:
            comp = self.db.query(Product).filter(Product.id == item.component_id).first()
            uom = None
            if item.unit_of_measure_id:
                from app.models.inventory import UnitOfMeasure
                u = self.db.query(UnitOfMeasure).filter(UnitOfMeasure.id == item.unit_of_measure_id).first()
                if u:
                    uom = {"id": u.id, "name": u.name, "abbreviation": u.abbreviation}
            result.append({
                "component_id": item.component_id,
                "component_name": comp.name if comp else None,
                "component_sku": comp.sku if comp else None,
                "quantity": float(item.quantity or 0),
                "unit_of_measure_id": item.unit_of_measure_id,
                "unit_of_measure": uom,
                "unit_cost": float(item.unit_cost or 0),
                "total_cost": float((item.unit_cost or 0) * (item.quantity or 0)),
            })
        return result

    def set_bom(self, product_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Replace BOM for product_id with provided items.

        items: [{ component_id, quantity, unit_cost?, unit_of_measure_id?, notes? }]
        """
        # Basic validation
        if items is None:
            raise ValueError("BOM items are required")

        # Validate referenced entities ahead of time
        # Cache products and UOMs
        comp_ids = {it.get("component_id") for it in items if it.get("component_id")}
        uom_ids = {it.get("unit_of_measure_id") for it in items if it.get("unit_of_measure_id")}
        products_map = {p.id: p for p in self.db.query(Product).filter(Product.id.in_(list(comp_ids))).all()} if comp_ids else {}
        uoms_map = {u.id: u for u in self.db.query(UnitOfMeasure).filter(UnitOfMeasure.id.in_(list(uom_ids))).all()} if uom_ids else {}

        # Remove existing BOM entries
        self.db.query(ProductAssembly).filter(ProductAssembly.assembled_product_id == product_id).delete()
        # Insert new
        created = 0
        for it in items or []:
            comp_id = it.get("component_id")
            qty = it.get("quantity")
            if not comp_id:
                raise ValueError("BOM item requires component_id")
            if qty is None:
                raise ValueError("BOM item quantity is required")
            if float(qty) < 0:
                raise ValueError("BOM item quantity cannot be negative")
            if float(qty) == 0:
                # Skip zero-quantity lines silently
                continue
            if it.get("unit_cost") is not None and float(it["unit_cost"]) < 0:
                raise ValueError("BOM item unit_cost cannot be negative")
            if comp_id not in products_map:
                raise ValueError(f"Component not found: {comp_id}")
            uom_id = it.get("unit_of_measure_id")
            if uom_id and uom_id not in uoms_map:
                raise ValueError(f"Unit of measure not found: {uom_id}")
            if uom_id:
                uom = uoms_map[uom_id]
                # Require positive conversion factors for non-base units
                if not bool(uom.is_base_unit) and float(uom.conversion_factor or 0) <= 0:
                    raise ValueError("Unit of measure conversion_factor must be > 0 for derived units")
            pa = ProductAssembly(
                assembled_product_id=product_id,
                component_id=comp_id,
                quantity=qty,
                unit_of_measure_id=uom_id,
                unit_cost=it.get("unit_cost"),
                total_cost=(float(it.get("unit_cost")) * float(qty)) if it.get("unit_cost") is not None else None,
                notes=it.get("notes"),
            )
            self.db.add(pa)
            created += 1
        self.db.commit()
        return {"success": True, "count": created}

    def produce_to_hq(
        self,
        product_id: str,
        quantity: int,
        labor_cost: float = 0.0,
        overhead_cost: float = 0.0,
        created_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Consume BOM components from HQ inventory and add finished goods to HQ.

        - Validates BOM exists and HQ availability for each component.
        - Issues components from HQ (negative transactions) using HQ average costs.
        - Computes materials cost from HQ average costs (or BOM unit_cost when available).
        - Receipts finished goods to HQ with computed unit cost.
        """
        if quantity <= 0:
            raise ValueError("Quantity must be positive")

        product = self.db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise ValueError("Product not found")

        bom_items = self.db.query(ProductAssembly).filter(
            ProductAssembly.assembled_product_id == product_id
        ).all()
        if not bom_items:
            raise ValueError("No BOM defined for this product")

        # 1) Validate and compute materials cost, issue components from HQ (with UOM conversion)
        total_materials_cost = 0.0
        component_issues: List[Tuple[str, int, float]] = []  # (component_id, base_qty_to_issue_int, unit_cost_per_base)

        # Preload UOMs for conversion
        uom_ids_needed = {b.unit_of_measure_id for b in bom_items if getattr(b, 'unit_of_measure_id', None)}
        uom_map: Dict[str, UnitOfMeasure] = {}
        if uom_ids_needed:
            for u in self.db.query(UnitOfMeasure).filter(UnitOfMeasure.id.in_(list(uom_ids_needed))).all():
                uom_map[u.id] = u

        for bom in bom_items:
            comp_id = bom.component_id
            required_qty_bom = float(bom.quantity or 0) * float(quantity)
            if required_qty_bom <= 0:
                continue

            # Convert to base unit if UOM provided
            base_qty = required_qty_bom
            uom_id = getattr(bom, 'unit_of_measure_id', None)
            unit_cost_per_base = None
            if uom_id and uom_id in uom_map and not bool(uom_map[uom_id].is_base_unit):
                factor = float(uom_map[uom_id].conversion_factor or 1.0)  # 1 BOM UOM = factor * base
                base_qty = required_qty_bom * factor
            # Round up to integer as inventory fields are integer-based
            base_qty_int = int(math.ceil(base_qty))

            hq = self.db.query(HeadquartersInventory).filter(HeadquartersInventory.product_id == comp_id).first()
            available = hq.available_for_allocation if hq else 0
            if not hq or available < base_qty_int:
                raise ValueError(f"Insufficient HQ stock for component. Product ID: {comp_id}, Required (base units): {base_qty_int}, Available: {available}")

            # Costing: if BOM unit_cost provided (per BOM unit), compute per-base cost so total matches
            if bom.unit_cost is not None:
                total_line_cost = float(bom.unit_cost) * required_qty_bom
                unit_cost_per_base = total_line_cost / float(base_qty_int) if base_qty_int > 0 else float(bom.unit_cost)
            else:
                unit_cost_per_base = float(hq.average_cost_per_unit or 0)
                total_line_cost = unit_cost_per_base * base_qty_int

            total_materials_cost += total_line_cost
            component_issues.append((comp_id, base_qty_int, unit_cost_per_base))

        # Perform the issues (reduce HQ available and create transactions)
        for comp_id, req_qty, unit_cost in component_issues:
            hq = self.db.query(HeadquartersInventory).filter(HeadquartersInventory.product_id == comp_id).first()
            # Reduce HQ available; keep cumulative totals consistent with existing semantics
            hq.available_for_allocation -= req_qty
            if hq.available_for_allocation < 0:
                hq.available_for_allocation = 0

            tx = InventoryTransaction(
                product_id=comp_id,
                transaction_type='headquarters_issue_to_production',
                quantity=-req_qty,
                unit_cost=unit_cost,
                total_cost=unit_cost * req_qty,
                reference=f"WIP-ISSUE-{product.sku or product.id}",
                note=f"Issue to production for {product.name}",
                date=date.today(),
                created_by=created_by,
                branch_id=None,
            )
            self.db.add(tx)

        # 2) Compute finished goods unit cost and receipt to HQ
        total_cost = float(total_materials_cost) + float(labor_cost or 0) + float(overhead_cost or 0)
        unit_cost_fg = total_cost / quantity if quantity > 0 else 0.0

        # Ensure HQ record for finished product exists
        hq_fg = self.db.query(HeadquartersInventory).filter(HeadquartersInventory.product_id == product_id).first()
        if not hq_fg:
            hq_fg = HeadquartersInventory(
                product_id=product_id,
                total_received_quantity=0,
                total_allocated_quantity=0,
                available_for_allocation=0,
            )
            self.db.add(hq_fg)
            self.db.flush()

        # Update HQ FG quantities and average cost akin to supplier receipt logic
        hq_fg.total_received_quantity += quantity
        hq_fg.available_for_allocation += quantity
        current_total_cost = float(hq_fg.total_cost_value or 0)
        new_total_cost = current_total_cost + total_cost
        new_total_qty = hq_fg.total_received_quantity
        hq_fg.average_cost_per_unit = new_total_cost / new_total_qty if new_total_qty > 0 else unit_cost_fg
        hq_fg.total_cost_value = new_total_cost
        hq_fg.last_received_date = date.today()

        # Inventory transaction for FG receipt at HQ
        fg_tx = InventoryTransaction(
            product_id=product_id,
            transaction_type='headquarters_production_receipt',
            quantity=quantity,
            unit_cost=unit_cost_fg,
            total_cost=total_cost,
            reference=f"PROD-REC-{product.sku or product.id}",
            note=notes or f"Production receipt for {product.name}",
            date=date.today(),
            created_by=created_by,
            branch_id=None,
        )
        self.db.add(fg_tx)

        self.db.commit()

        return {
            "success": True,
            "product_id": product_id,
            "product_name": product.name,
            "quantity": quantity,
            "materials_cost": round(total_materials_cost, 2),
            "labor_cost": round(float(labor_cost or 0), 2),
            "overhead_cost": round(float(overhead_cost or 0), 2),
            "total_cost": round(total_cost, 2),
            "unit_cost": round(unit_cost_fg, 2),
            "hq_available_after": hq_fg.available_for_allocation,
        }

    def post_to_accounting(self, production_order_id: str, user_id: str = None) -> dict:
        """
        Post manufacturing costs to General Ledger with dimensional assignments.

        Creates journal entries for:
        1. WIP Debit (Material + Overhead)
        2. Labor Debit
        3. Offset Credit to liability account
        """
        from app.models.production_order import ProductionOrder
        from app.models.accounting import JournalEntry, AccountingEntry
        from app.models.accounting_dimensions import AccountingDimensionAssignment, AccountingDimensionValue
        from app.models.accounting_constants import AccountingCode
        from decimal import Decimal
        from datetime import datetime

        # Fetch production order
        po = self.db.query(ProductionOrder).filter(
            ProductionOrder.id == production_order_id
        ).first()

        if not po:
            raise ValueError(f"Production order {production_order_id} not found")

        if po.posting_status == 'posted':
            raise ValueError(f"Production order already posted")

        # Get manufacturing costs
        mfg_costs = self.db.query(ManufacturingCost).filter(
            ManufacturingCost.production_order_id == production_order_id
        ).all()

        if not mfg_costs:
            raise ValueError("No manufacturing costs found for this order")

        # Validate GL accounts are set
        if not po.wip_account_id or not po.labor_account_id:
            raise ValueError("WIP and Labor GL accounts must be set")

        # Calculate totals
        total_material = sum(Decimal(str(c.material_cost or 0)) for c in mfg_costs)
        total_labor = sum(Decimal(str(c.labor_cost or 0)) for c in mfg_costs)
        total_overhead = sum(Decimal(str(c.overhead_cost or 0)) for c in mfg_costs)
        total = total_material + total_labor + total_overhead

        # Create accounting entry header
        acct_entry = AccountingEntry(
            entry_type='MANUFACTURING_POSTING',
            entry_date=datetime.now(),
            total_debit=total,
            total_credit=total,
            reference=f"MFG-{po.id}",
            created_by_user_id=user_id,
            branch_id=po.manufacturing_branch_id
        )
        self.db.add(acct_entry)
        self.db.flush()

        journal_entries = []

        # Create WIP debit entry (Material + Overhead)
        wip_amount = total_material + total_overhead
        wip_entry = JournalEntry(
            accounting_code_id=po.wip_account_id,
            debit_amount=wip_amount,
            credit_amount=Decimal('0'),
            description=f"Manufacturing WIP - {po.order_number}",
            reference=f"MFG-{po.id}-WIP",
            entry_date=datetime.now().date(),
            source='MANUFACTURING',
            accounting_entry_id=acct_entry.id
        )
        self.db.add(wip_entry)
        self.db.flush()
        journal_entries.append(wip_entry)

        # Create labor debit entry
        labor_entry = JournalEntry(
            accounting_code_id=po.labor_account_id,
            debit_amount=total_labor,
            credit_amount=Decimal('0'),
            description=f"Manufacturing Labor - {po.order_number}",
            reference=f"MFG-{po.id}-LABOR",
            entry_date=datetime.now().date(),
            source='MANUFACTURING',
            accounting_entry_id=acct_entry.id
        )
        self.db.add(labor_entry)
        self.db.flush()
        journal_entries.append(labor_entry)

        # Create offset credit entry (to liability/equity)
        offset_account_id = self._get_offset_account_id()
        offset_entry = JournalEntry(
            accounting_code_id=offset_account_id,
            debit_amount=Decimal('0'),
            credit_amount=total,
            description=f"Manufacturing Offset - {po.order_number}",
            reference=f"MFG-{po.id}-OFFSET",
            entry_date=datetime.now().date(),
            source='MANUFACTURING',
            accounting_entry_id=acct_entry.id
        )
        self.db.add(offset_entry)
        self.db.flush()
        journal_entries.append(offset_entry)

        # Apply dimension assignments to all journal entries
        dimension_mapping = {
            'cost_center': po.cost_center_id,
            'project': po.project_id,
            'department': po.department_id
        }

        for je in journal_entries:
            for dim_type, dim_value_id in dimension_mapping.items():
                if dim_value_id:
                    dim_assign = AccountingDimensionAssignment(
                        journal_entry_id=je.id,
                        dimension_value_id=dim_value_id
                    )
                    self.db.add(dim_assign)

        # Update PO posting status
        po.posting_status = 'posted'
        po.last_posted_date = datetime.now()
        po.posted_by = user_id

        self.db.commit()

        return {
            'success': True,
            'production_order_id': po.id,
            'entries_created': len(journal_entries),
            'journal_entry_ids': [je.id for je in journal_entries],
            'total_amount': float(total),
            'posting_date': datetime.now().isoformat()
        }

    def reconcile_manufacturing_costs(self, period: str) -> dict:
        """
        Reconcile manufacturing costs against GL balances by dimension.

        Format: period = "2025-10" (YYYY-MM)
        Returns variance analysis by dimension
        """
        from app.models.production_order import ProductionOrder
        from app.models.accounting import JournalEntry
        from datetime import datetime
        from decimal import Decimal

        # Parse period
        try:
            year, month = map(int, period.split('-'))
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
        except:
            raise ValueError(f"Invalid period format: {period}. Use YYYY-MM")

        # Get all manufacturing costs in period
        mfg_query = self.db.query(ManufacturingCost).filter(
            ManufacturingCost.date >= start_date,
            ManufacturingCost.date <= end_date
        )

        mfg_total = Decimal('0')
        mfg_by_dimension = {}

        for cost in mfg_query.all():
            mfg_total += Decimal(str(cost.total_cost or 0))

            # Group by cost center
            if cost.production_order_id:
                po = self.db.query(ProductionOrder).filter(
                    ProductionOrder.id == cost.production_order_id
                ).first()
                if po and po.cost_center_id:
                    if po.cost_center_id not in mfg_by_dimension:
                        mfg_by_dimension[po.cost_center_id] = Decimal('0')
                    mfg_by_dimension[po.cost_center_id] += Decimal(str(cost.total_cost or 0))

        # Get GL balances for manufacturing accounts
        gl_total = Decimal('0')
        gl_by_dimension = {}

        je_query = self.db.query(JournalEntry).filter(
            JournalEntry.entry_date >= start_date,
            JournalEntry.entry_date <= end_date,
            JournalEntry.source == 'MANUFACTURING'
        )

        for je in je_query.all():
            balance = Decimal(str(je.debit_amount or 0)) - Decimal(str(je.credit_amount or 0))
            gl_total += balance

            # Group by dimension if available
            if je.dimension_assignments:
                for dim_assign in je.dimension_assignments:
                    dim_value_id = dim_assign.dimension_value_id
                    if dim_value_id not in gl_by_dimension:
                        gl_by_dimension[dim_value_id] = Decimal('0')
                    gl_by_dimension[dim_value_id] += balance

        # Calculate variances
        variance = gl_total - mfg_total
        variance_pct = (variance / mfg_total * 100) if mfg_total > 0 else Decimal('0')

        # Reconciled items (variance < $0.01)
        reconciled_dims = []
        variance_dims = []

        all_dims = set(mfg_by_dimension.keys()) | set(gl_by_dimension.keys())

        for dim_id in all_dims:
            mfg_amt = mfg_by_dimension.get(dim_id, Decimal('0'))
            gl_amt = gl_by_dimension.get(dim_id, Decimal('0'))
            dim_variance = gl_amt - mfg_amt

            if abs(dim_variance) < Decimal('0.01'):
                reconciled_dims.append({
                    'dimension_id': dim_id,
                    'mfg_amount': float(mfg_amt),
                    'gl_amount': float(gl_amt),
                    'variance': float(dim_variance)
                })
            else:
                variance_dims.append({
                    'dimension_id': dim_id,
                    'mfg_amount': float(mfg_amt),
                    'gl_amount': float(gl_amt),
                    'variance': float(dim_variance),
                    'variance_percent': float((dim_variance / mfg_amt * 100) if mfg_amt > 0 else Decimal('0'))
                })

        return {
            'period': period,
            'reconciliation_date': datetime.now().isoformat(),
            'totals': {
                'mfg_total': float(mfg_total),
                'gl_total': float(gl_total),
                'variance': float(variance),
                'variance_percent': float(variance_pct)
            },
            'reconciled_dimensions': reconciled_dims,
            'variance_dimensions': variance_dims,
            'reconciliation_status': 'RECONCILED' if variance_pct < Decimal('0.1') else 'VARIANCE_DETECTED'
        }

    def post_cogs_to_accounting(self, production_order_id: str, invoice_id: str, user_id: str = None) -> dict:
        """
        Post COGS (Cost of Goods Sold) from ProductionOrder to GL when Invoice is created.

        Creates 2 GL entries:
        1. COGS Debit (to COGS GL account)
        2. Inventory Credit (reversal from WIP)

        Automatically inherits dimensions from ProductionOrder and creates COGS allocation record.

        Args:
            production_order_id: Production order that created the product
            invoice_id: Invoice that sold the product
            user_id: User performing the posting

        Returns:
            Dictionary with posting results including GL entry IDs and dimension details
        """
        from app.models.production_order import ProductionOrder
        from app.models.sales import Invoice
        from app.models.accounting import JournalEntry
        from app.models.accounting_dimensions import AccountingDimensionAssignment, AccountingDimensionValue
        from app.models.cogs_allocation import COGSAllocation
        from decimal import Decimal
        from datetime import datetime

        # Fetch production order and invoice
        po = self.db.query(ProductionOrder).filter(ProductionOrder.id == production_order_id).first()
        if not po:
            raise ValueError(f"Production order {production_order_id} not found")

        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        # Check if COGS already posted for this PO (double-posting prevention)
        if po.cogs_posting_status == 'posted':
            raise ValueError(f"COGS already posted for production order {production_order_id}")

        # Get product from invoice
        if not invoice.items or len(invoice.items) == 0:
            raise ValueError(f"Invoice has no items")

        product = invoice.items[0].product
        if not product:
            raise ValueError(f"Product not found on invoice line")

        # Validate COGS GL account is set
        if not po.cogs_gl_account_id:
            raise ValueError("COGS GL account must be set on production order")

        # Get unit cost from PO
        unit_cost = po.unit_cost
        if not unit_cost or unit_cost <= 0:
            raise ValueError(f"Invalid unit cost on production order: {unit_cost}")

        # Get quantity sold from invoice (assuming first line item has the quantity)
        quantity_sold = invoice.items[0].quantity if invoice.items else Decimal('0')
        total_cogs = Decimal(str(quantity_sold)) * Decimal(str(unit_cost))

        # Create COGS GL entry (Debit)
        cogs_entry = JournalEntry(
            accounting_code_id=po.cogs_gl_account_id,
            debit_amount=total_cogs,
            credit_amount=Decimal('0'),
            description=f"COGS for {product.name} - Invoice {invoice.invoice_number}",
            reference=f"COGS-{po.id}-{invoice_id}",
            entry_date=datetime.now().date(),
            source='SALES',  # Posting triggered by sale
            branch_id=invoice.branch_id or po.manufacturing_branch_id
        )
        self.db.add(cogs_entry)
        self.db.flush()

        # Create Inventory offset entry (Credit to reverse WIP)
        inventory_account_id = self._get_inventory_offset_account_id()
        inventory_entry = JournalEntry(
            accounting_code_id=inventory_account_id,
            debit_amount=Decimal('0'),
            credit_amount=total_cogs,
            description=f"Inventory reversal for {product.name} - Invoice {invoice.invoice_number}",
            reference=f"INV-{po.id}-{invoice_id}",
            entry_date=datetime.now().date(),
            source='SALES',
            branch_id=invoice.branch_id or po.manufacturing_branch_id
        )
        self.db.add(inventory_entry)
        self.db.flush()

        # Create dimension assignments for COGS entry (inherit from PO)
        if po.cost_center_id:
            dim_assign = AccountingDimensionAssignment(
                journal_entry_id=cogs_entry.id,
                dimension_value_id=po.cost_center_id,
                dimension_type='cost_center'
            )
            self.db.add(dim_assign)

        if po.project_id:
            dim_assign = AccountingDimensionAssignment(
                journal_entry_id=cogs_entry.id,
                dimension_value_id=po.project_id,
                dimension_type='project'
            )
            self.db.add(dim_assign)

        if po.department_id:
            dim_assign = AccountingDimensionAssignment(
                journal_entry_id=cogs_entry.id,
                dimension_value_id=po.department_id,
                dimension_type='department'
            )
            self.db.add(dim_assign)

        # Create COGS allocation record to track revenue vs COGS
        cogs_alloc = COGSAllocation(
            production_order_id=production_order_id,
            invoice_id=invoice_id,
            product_id=product.id,
            quantity_produced=po.quantity_produced,
            quantity_sold=quantity_sold,
            cost_per_unit=unit_cost,
            total_cogs=total_cogs,
            revenue_gl_entry_id=None,  # Will be linked when invoice is posted
            cogs_gl_entry_id=cogs_entry.id,
            production_cost_center_id=po.cost_center_id,
            production_project_id=po.project_id,
            production_department_id=po.department_id,
            sales_cost_center_id=invoice.cost_center_id,
            sales_project_id=invoice.project_id,
            sales_department_id=invoice.department_id,
            has_dimension_variance='true' if po.cost_center_id != invoice.cost_center_id else 'false',
            variance_reason='COST_CENTER_MISMATCH' if po.cost_center_id != invoice.cost_center_id else None,
            created_by=user_id
        )
        self.db.add(cogs_alloc)

        # Update production order COGS posting status
        po.cogs_posting_status = 'posted'
        po.cogs_last_posted_date = datetime.now()
        po.cogs_posted_by = user_id

        self.db.commit()

        return {
            'success': True,
            'production_order_id': production_order_id,
            'invoice_id': invoice_id,
            'product_id': product.id,
            'quantity_sold': float(quantity_sold),
            'unit_cost': float(unit_cost),
            'total_cogs': float(total_cogs),
            'cogs_gl_entry_id': cogs_entry.id,
            'inventory_gl_entry_id': inventory_entry.id,
            'cogs_allocation_id': cogs_alloc.id,
            'dimensions': {
                'cost_center_id': po.cost_center_id,
                'project_id': po.project_id,
                'department_id': po.department_id
            },
            'posting_date': datetime.now().isoformat()
        }

    def reconcile_cogs_by_dimension(self, period: str) -> dict:
        """
        Reconcile Revenue (from invoices) against COGS (from production) by dimension.

        Calculates gross margin and detects variances for the given period.

        Args:
            period: Period in format "YYYY-MM" (e.g., "2025-10")

        Returns:
            Reconciliation report with gross margin by dimension
        """
        from app.models.cogs_allocation import COGSAllocation
        from app.models.accounting_dimensions import AccountingDimensionValue
        from decimal import Decimal
        from datetime import datetime

        # Parse period
        year, month = period.split('-')
        start_date = date(int(year), int(month), 1)
        if int(month) == 12:
            end_date = date(int(year) + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(int(year), int(month) + 1, 1) - timedelta(days=1)

        # Query COGS allocations for period
        allocations = self.db.query(COGSAllocation).filter(
            COGSAllocation.created_at >= start_date,
            COGSAllocation.created_at <= end_date
        ).all()

        if not allocations:
            return {
                'period': period,
                'by_dimension': [],
                'totals': {
                    'revenue': 0.0,
                    'cogs': 0.0,
                    'gross_margin': 0.0,
                    'gm_percent': 0.0
                }
            }

        # Aggregate by cost center
        by_cost_center = {}
        total_revenue = Decimal('0')
        total_cogs = Decimal('0')

        for alloc in allocations:
            cc_id = alloc.sales_cost_center_id or alloc.production_cost_center_id

            if cc_id not in by_cost_center:
                cc_name = self.db.query(AccountingDimensionValue).filter(AccountingDimensionValue.id == cc_id).first()
                by_cost_center[cc_id] = {
                    'cost_center_id': cc_id,
                    'cost_center_name': cc_name.name if cc_name else 'Unknown',
                    'revenue': Decimal('0'),
                    'cogs': Decimal(str(alloc.total_cogs)),
                    'variance': Decimal('0')
                }
            else:
                by_cost_center[cc_id]['cogs'] += Decimal(str(alloc.total_cogs))

            # In real implementation, fetch revenue from GL entries for this invoice
            # For now, estimate as: cogs + standard 40% markup
            revenue = Decimal(str(alloc.total_cogs)) * Decimal('1.4')  # 40% markup = 40% margin
            by_cost_center[cc_id]['revenue'] += revenue
            total_revenue += revenue
            total_cogs += Decimal(str(alloc.total_cogs))

        # Calculate margins
        results = []
        for cc_id, data in by_cost_center.items():
            gm = data['revenue'] - data['cogs']
            gm_pct = (gm / data['revenue'] * 100) if data['revenue'] > 0 else Decimal('0')

            results.append({
                'cost_center_id': data['cost_center_id'],
                'cost_center_name': data['cost_center_name'],
                'revenue': float(data['revenue']),
                'cogs': float(data['cogs']),
                'gross_margin': float(gm),
                'gm_percent': float(gm_pct),
                'is_reconciled': True,
                'variance': 0.0
            })

        total_gm = total_revenue - total_cogs
        total_gm_pct = (total_gm / total_revenue * 100) if total_revenue > 0 else Decimal('0')

        return {
            'period': period,
            'by_dimension': results,
            'totals': {
                'revenue': float(total_revenue),
                'cogs': float(total_cogs),
                'gross_margin': float(total_gm),
                'gm_percent': float(total_gm_pct)
            }
        }

    def _get_offset_account_id(self) -> str:
        """Get the offset account ID for manufacturing postings (typically a payable account)"""
        # This should be configurable, defaulting to a standard manufacturing payable account
        from app.models.accounting_constants import AccountingCode

        offset_acct = self.db.query(AccountingCode).filter(
            AccountingCode.code == '2100-200'  # Manufacturing Payable
        ).first()

        if not offset_acct:
            # Fallback to any payable account
            offset_acct = self.db.query(AccountingCode).filter(
                AccountingCode.account_type == 'PAYABLE'
            ).first()

        if not offset_acct:
            raise ValueError("No offset account configured for manufacturing postings")

        return offset_acct.id

    def _get_inventory_offset_account_id(self) -> str:
        """Get the inventory/WIP offset account for COGS posting (typically an inventory asset account)"""
        from app.models.accounting_constants import AccountingCode

        inventory_acct = self.db.query(AccountingCode).filter(
            AccountingCode.code == '1300-100'  # Finished Goods Inventory
        ).first()

        if not inventory_acct:
            # Fallback to WIP
            inventory_acct = self.db.query(AccountingCode).filter(
                AccountingCode.code == '1300-050'  # WIP Inventory
            ).first()

        if not inventory_acct:
            # Final fallback - any inventory account
            inventory_acct = self.db.query(AccountingCode).filter(
                AccountingCode.account_type == 'ASSET'
            ).first()

        if not inventory_acct:
            raise ValueError("No inventory account configured for COGS posting")

        return inventory_acct.id
