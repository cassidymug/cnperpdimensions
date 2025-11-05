from datetime import datetime, date
from decimal import Decimal
from typing import List, Dict, Optional, Tuple

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_

from app.models.job_card import JobCard, JobCardMaterial, JobCardLabor, JobCardNote
from app.models.inventory import Product, InventoryTransaction
from app.models.branch import Branch
from app.models.sales import Invoice
from app.models.app_setting import AppSetting
from app.models.user import User
from app.services.inventory_service import InventoryService
from app.services.invoice_service import InvoiceService
from app.services.manufacturing_service import ManufacturingService


class JobCardService:
    """Business logic for job card lifecycle"""

    STATUS_FLOW: Dict[str, List[str]] = {
        "draft": ["scheduled", "in_progress", "cancelled"],
        "scheduled": ["in_progress", "cancelled"],
        "in_progress": ["completed", "invoiced", "cancelled"],
        "completed": ["invoiced", "closed"],
        "invoiced": ["closed"],
        "closed": [],
        "cancelled": [],
    }

    def __init__(self, db: Session):
        self.db = db
        self.inventory_service = InventoryService(db)
        self.invoice_service = InvoiceService(db)
        self.default_currency, self.default_vat = self._load_financial_defaults()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------
    def list_job_cards(
        self,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        branch_id: Optional[str] = None,
        customer_id: Optional[str] = None,
        search: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[Dict[str, object]]:
        query = self.db.query(JobCard)

        if status:
            query = query.filter(JobCard.status == status.lower())
        if job_type:
            query = query.filter(JobCard.job_type == job_type)
        if branch_id:
            query = query.filter(JobCard.branch_id == branch_id)
        if customer_id:
            query = query.filter(JobCard.customer_id == customer_id)
        if from_date:
            query = query.filter(JobCard.start_date >= from_date)
        if to_date:
            query = query.filter(JobCard.start_date <= to_date)
        if search:
            like_filter = f"%{search.lower()}%"
            query = query.filter(
                func.lower(JobCard.job_number).like(like_filter)
                | func.lower(JobCard.description).like(like_filter)
                | func.lower(JobCard.notes).like(like_filter)
            )

        jobs = (
            query.options(
                joinedload(JobCard.materials).joinedload(JobCardMaterial.product),
                joinedload(JobCard.labor_entries),
                joinedload(JobCard.customer),
                joinedload(JobCard.branch),
                joinedload(JobCard.invoice),
            )
            .order_by(JobCard.created_at.desc())
            .all()
        )
        return [self._serialize_job_card(job) for job in jobs]

    def get_job_card(self, job_id: str) -> Dict[str, object]:
        job = (
            self.db.query(JobCard)
            .options(
                joinedload(JobCard.materials).joinedload(JobCardMaterial.product),
                joinedload(JobCard.labor_entries),
                joinedload(JobCard.notes_entries),
                joinedload(JobCard.customer),
                joinedload(JobCard.branch),
                joinedload(JobCard.invoice),
            )
            .filter(JobCard.id == job_id)
            .first()
        )
        if not job:
            raise ValueError("Job card not found")
        return self._serialize_job_card(job, include_notes=True)

    def create_job_card(self, payload: Dict[str, object], user_id: Optional[str] = None) -> Dict[str, object]:
        branch_id = payload.get("branch_id")
        if not branch_id:
            raise ValueError("Branch is required for job cards")

        technician_id = self._validate_technician(payload.get("technician_id"), branch_id)
        job = JobCard(
            job_number=self._generate_job_number(branch_id),
            customer_id=payload["customer_id"],
            branch_id=branch_id,
            job_type=payload.get("job_type", "service"),
            priority=(payload.get("priority") or "normal").lower(),
            status=(payload.get("status") or "draft").lower(),
            description=payload.get("description"),
            notes=payload.get("notes"),
            start_date=payload.get("start_date"),
            due_date=payload.get("due_date"),
            technician_id=technician_id,
            created_by_id=user_id,
            currency=payload.get("currency") or self.default_currency,
            vat_rate=self._to_decimal(payload.get("vat_rate"), self.default_vat),
            bom_product_id=payload.get("bom_product_id"),
            production_quantity=self._to_decimal(payload.get("production_quantity"), None),
        )

        self.db.add(job)
        self.db.flush()

        materials_payload = payload.get("materials") or []
        labor_payload = payload.get("labor") or []

        if materials_payload:
            self._sync_materials(job, materials_payload, mode="replace")
        if labor_payload:
            self._sync_labor(job, labor_payload, mode="replace")

        self._recalculate_totals(job)
        self.db.commit()
        self.db.refresh(job)
        return self._serialize_job_card(job)

    def update_job_card(self, job_id: str, payload: Dict[str, object], user_id: Optional[str] = None) -> Dict[str, object]:
        job = self._get_job(job_id)
        if job.status in {"cancelled", "closed"}:
            raise ValueError("Cannot update a closed or cancelled job card")

        if "customer_id" in payload:
            job.customer_id = payload["customer_id"]
        if "branch_id" in payload:
            job.branch_id = payload["branch_id"]
        if "job_type" in payload:
            job.job_type = payload["job_type"]
        if "priority" in payload:
            job.priority = payload["priority"]
        if "description" in payload:
            job.description = payload["description"]
        if "notes" in payload:
            job.notes = payload["notes"]
        if "start_date" in payload:
            job.start_date = payload["start_date"]
        if "due_date" in payload:
            job.due_date = payload["due_date"]
        if "technician_id" in payload:
            job.technician_id = self._validate_technician(payload.get("technician_id"), job.branch_id)
        if "currency" in payload:
            job.currency = payload["currency"] or self.default_currency
        if "vat_rate" in payload:
            job.vat_rate = self._to_decimal(payload.get("vat_rate"), self.default_vat)

        if user_id:
            job.updated_by_id = user_id

        if payload.get("materials") is not None:
            self._sync_materials(job, payload.get("materials") or [], mode="replace")
        if payload.get("labor") is not None:
            self._sync_labor(job, payload.get("labor") or [], mode="replace")

        self._recalculate_totals(job)
        self.db.commit()
        self.db.refresh(job)
        return self._serialize_job_card(job)

    def update_materials(self, job_id: str, materials: List[Dict[str, object]], mode: str = "append") -> Dict[str, object]:
        job = self._get_job(job_id)
        if job.status == "cancelled":
            raise ValueError("Cannot change materials on a cancelled job")
        self._sync_materials(job, materials, mode=mode)
        self._recalculate_totals(job)
        self.db.commit()
        self.db.refresh(job)
        return self._serialize_job_card(job)

    def update_labor(self, job_id: str, labor: List[Dict[str, object]], mode: str = "append") -> Dict[str, object]:
        job = self._get_job(job_id)
        if job.status == "cancelled":
            raise ValueError("Cannot change labor on a cancelled job")
        self._sync_labor(job, labor, mode=mode)
        self._recalculate_totals(job)
        self.db.commit()
        self.db.refresh(job)
        return self._serialize_job_card(job)

    def delete_job_card(self, job_id: str, force: bool = False) -> bool:
        """
        Delete a job card and all related data.
        
        Args:
            job_id: The job card ID to delete
            force: If True, delete even if invoiced. If False, prevent deletion of invoiced jobs.
            
        Returns:
            True if deleted successfully
            
        Raises:
            ValueError: If job not found or cannot be deleted
        """
        job = self._get_job(job_id)
        
        # Check if job has been invoiced
        if job.invoice_generated and not force:
            raise ValueError("Cannot delete job card that has been invoiced. Use force=True to override.")
        
        # Check if job has a related invoice by looking up the invoice table
        related_invoice = self.db.query(Invoice).filter(Invoice.job_card_id == job_id).first()
        if related_invoice and not force:
            raise ValueError("Cannot delete job card with a linked invoice. Delete the invoice first or use force=True.")
        
        # If force deleting and there's an invoice, unlink it (set job_card_id to None)
        if related_invoice and force:
            related_invoice.job_card_id = None
            self.db.flush()
        
        # Unlink inventory transactions (set related_job_card_id to None instead of deleting them)
        self.db.query(InventoryTransaction).filter(
            InventoryTransaction.related_job_card_id == job_id
        ).update({"related_job_card_id": None}, synchronize_session=False)
        
        # Delete related records (these have cascade configured, but being explicit)
        # Delete materials
        self.db.query(JobCardMaterial).filter(JobCardMaterial.job_card_id == job_id).delete(synchronize_session=False)
        
        # Delete labor entries
        self.db.query(JobCardLabor).filter(JobCardLabor.job_card_id == job_id).delete(synchronize_session=False)
        
        # Delete notes
        self.db.query(JobCardNote).filter(JobCardNote.job_card_id == job_id).delete(synchronize_session=False)
        
        # Delete the job card itself
        self.db.delete(job)
        self.db.commit()
        
        return True

    def add_note(self, job_id: str, note: str, author_id: Optional[str]) -> Dict[str, object]:
        job = self._get_job(job_id)
        entry = JobCardNote(job_card_id=job.id, note=note, author_id=author_id)
        self.db.add(entry)
        self.db.commit()
        return {
            "id": entry.id,
            "note": entry.note,
            "author_id": entry.author_id,
            "logged_at": entry.logged_at.isoformat(),
        }

    def change_status(
        self,
        job_id: str,
        new_status: str,
        user_id: Optional[str] = None,
        auto_invoice: bool = True,
    ) -> Dict[str, object]:
        job = self._get_job(job_id)
        target_status = new_status.lower()
        if target_status == job.status:
            return self._serialize_job_card(job)
        allowed = self.STATUS_FLOW.get(job.status, [])
        if target_status not in allowed:
            raise ValueError(f"Cannot change status from {job.status} to {target_status}")

        if target_status == "in_progress":
            self._issue_materials(job, user_id)
        if target_status == "cancelled":
            self._return_materials(job)
        if target_status in {"completed", "invoiced"}:
            self._issue_materials(job, user_id)
            # Handle manufacturing production if this is a manufacturing job with BOM
            if job.job_type == "manufacturing" and hasattr(job, 'bom_product_id') and job.bom_product_id:
                self._complete_manufacturing_production(job, user_id)
            job.completed_date = date.today()
            self._recalculate_totals(job)
            if target_status == "invoiced" and auto_invoice and not job.invoice_generated:
                self._generate_invoice(job, user_id)
        if target_status == "closed":
            if job.invoice and job.invoice.amount_due and job.invoice.amount_due > 0:
                raise ValueError("Cannot close job with outstanding invoice balance")

        job.status = target_status
        if user_id:
            job.updated_by_id = user_id
        self.db.commit()
        self.db.refresh(job)
        return self._serialize_job_card(job)

    def generate_invoice(
        self,
        job_id: str,
        user_id: Optional[str] = None,
        save_draft: bool = False,
        is_cash_sale: bool = False,
    ) -> Dict[str, object]:
        job = self._get_job(job_id)
        invoice = self._generate_invoice(job, user_id, save_draft=save_draft, is_cash_sale=is_cash_sale)
        self.db.commit()
        self.db.refresh(job)
        return {
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "total_amount": float(invoice.total_amount or 0),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_financial_defaults(self) -> Tuple[str, Decimal]:
        settings = self.db.query(AppSetting).first()
        currency = (settings.currency if settings and getattr(settings, "currency", None) else "BWP")
        vat_value = None
        if settings and getattr(settings, "vat_rate", None) is not None:
            vat_value = settings.vat_rate
        elif settings and getattr(settings, "default_vat_rate", None) is not None:
            vat_value = settings.default_vat_rate
        return currency, self._to_decimal(vat_value, Decimal("0"))

    def _generate_job_number(self, branch_id: str) -> str:
        branch = self.db.query(Branch).filter(Branch.id == branch_id).first()
        prefix = (branch.code if branch and branch.code else "JC").upper()
        date_part = datetime.utcnow().strftime("%Y%m%d")
        like_pattern = f"{prefix}-{date_part}-%"
        last_job = (
            self.db.query(JobCard)
            .filter(JobCard.job_number.like(like_pattern))
            .order_by(JobCard.job_number.desc())
            .first()
        )
        if last_job:
            try:
                seq = int(last_job.job_number.split("-")[-1]) + 1
            except (ValueError, AttributeError):
                seq = 1
        else:
            seq = 1
        return f"{prefix}-{date_part}-{seq:04d}"

    def _sync_materials(self, job: JobCard, materials: List[Dict[str, object]], mode: str = "append") -> None:
        if mode == "replace":
            for existing in list(job.materials):
                self.db.delete(existing)
            self.db.flush()
        for item in materials:
            product = self.db.query(Product).filter(Product.id == item["product_id"]).first()
            if not product:
                raise ValueError("Product not found for material line")
            if job.branch_id and product.branch_id and product.branch_id != job.branch_id:
                raise ValueError("Selected product is not allocated to this branch")
            quantity = self._to_decimal(item.get("quantity"), Decimal("0"))
            if quantity <= 0:
                continue
            unit_cost = self._to_decimal(item.get("unit_cost"), product.cost_price or Decimal("0"))
            unit_price = self._to_decimal(item.get("unit_price"), product.selling_price or Decimal("0"))
            material = JobCardMaterial(
                product_id=product.id,
                quantity=quantity,
                unit_cost=unit_cost,
                unit_price=unit_price,
                total_cost=unit_cost * quantity,
                total_price=unit_price * quantity,
                notes=item.get("notes"),
            )
            job.materials.append(material)
        self.db.flush()

    def _sync_labor(self, job: JobCard, labor: List[Dict[str, object]], mode: str = "append") -> None:
        if mode == "replace":
            for existing in list(job.labor_entries):
                self.db.delete(existing)
            self.db.flush()
        for item in labor:
            description = item.get("description")
            if not description:
                continue
            hours = self._to_decimal(item.get("hours"), Decimal("0"))
            rate = self._to_decimal(item.get("rate"), Decimal("0"))
            cost_rate = self._to_decimal(item.get("cost_rate"), rate)
            technician_id = self._validate_technician(item.get("technician_id") or job.technician_id, job.branch_id)
            labor_row = JobCardLabor(
                description=description,
                hours=hours,
                rate=rate,
                total_price=rate * hours,
                total_cost=cost_rate * hours,
                technician_id=technician_id,
                product_id=item.get("product_id"),
                notes=item.get("notes"),
            )
            job.labor_entries.append(labor_row)
        self.db.flush()

    def _recalculate_totals(self, job: JobCard) -> None:
        materials_cost = sum(self._to_decimal(m.total_cost, Decimal("0")) for m in job.materials)
        materials_price = sum(self._to_decimal(m.total_price, Decimal("0")) for m in job.materials)
        labor_cost = sum(self._to_decimal(l.total_cost, Decimal("0")) for l in job.labor_entries)
        labor_price = sum(self._to_decimal(l.total_price, Decimal("0")) for l in job.labor_entries)
        job.total_material_cost = materials_cost
        job.total_material_price = materials_price
        job.total_labor_cost = labor_cost
        job.total_labor_price = labor_price
        job.subtotal = materials_price + labor_price
        vat_rate = self._to_decimal(job.vat_rate, Decimal("0"))
        job.vat_amount = (job.subtotal * vat_rate / Decimal("100")) if vat_rate else Decimal("0")
        job.total_amount = job.subtotal + job.vat_amount
        job.amount_due = job.total_amount - self._to_decimal(job.amount_paid, Decimal("0"))

    def _issue_materials(self, job: JobCard, user_id: Optional[str]) -> None:
        for material in job.materials:
            if material.is_issued:
                continue
            quantity = self._to_decimal(material.quantity, Decimal("0"))
            if quantity <= 0:
                continue
            reference = f"JobCard {job.job_number} Material {material.product_id}"
            success, message = self.inventory_service.update_product_quantity(
                material.product_id,
                quantity,
                "job_issue",
                reference=reference,
                branch_id=job.branch_id,
                job_card_id=job.id,
                note=material.notes,
            )
            if not success:
                raise ValueError(message)
            material.is_issued = True
            material.issued_at = datetime.utcnow()
            transaction = (
                self.db.query(InventoryTransaction)
                .filter(
                    InventoryTransaction.product_id == material.product_id,
                    InventoryTransaction.related_job_card_id == job.id,
                )
                .order_by(InventoryTransaction.created_at.desc())
                .first()
            )
            if transaction:
                material.inventory_transaction_id = transaction.id
        self.db.flush()

    def _return_materials(self, job: JobCard) -> None:
        for material in job.materials:
            if not material.is_issued:
                continue
            quantity = self._to_decimal(material.quantity, Decimal("0"))
            if quantity <= 0:
                continue
            reference = f"JobCard {job.job_number} Return {material.product_id}"
            success, message = self.inventory_service.update_product_quantity(
                material.product_id,
                quantity,
                "job_return",
                reference=reference,
                branch_id=job.branch_id,
                job_card_id=job.id,
                note=material.notes,
            )
            if not success:
                raise ValueError(message)
            material.is_issued = False
            material.issued_at = None
            material.inventory_transaction_id = None
        self.db.flush()

    def _complete_manufacturing_production(self, job: JobCard, user_id: Optional[str]) -> None:
        """
        Handle manufacturing production when job is completed.
        Deducts raw materials and adds finished goods to inventory.
        """
        if not hasattr(job, 'bom_product_id') or not job.bom_product_id:
            return
            
        production_qty = getattr(job, 'production_quantity', 1)
        if production_qty <= 0:
            production_qty = 1
            
        # Calculate total labor cost from job card
        total_labor = sum(
            float(self._to_decimal(labor.total_price, Decimal("0")))
            for labor in job.labor_entries
        )
        
        # Use manufacturing service to produce to HQ
        manufacturing_service = ManufacturingService(self.db)
        try:
            result = manufacturing_service.produce_to_hq(
                product_id=job.bom_product_id,
                quantity=production_qty,
                labor_cost=total_labor,
                overhead_cost=0,  # Can be enhanced later
                created_by=user_id,
                notes=f"Produced via Job Card {job.job_number}"
            )
            
            # Store production reference on job card
            if not hasattr(job, 'production_reference'):
                # Add as a note if no production_reference field exists
                note = JobCardNote(
                    job_card_id=job.id,
                    note=f"Manufacturing production completed: {production_qty} units of {result.get('product_name', 'product')}",
                    author_id=user_id,
                    created_at=datetime.utcnow()
                )
                self.db.add(note)
                
        except Exception as e:
            raise ValueError(f"Manufacturing production failed: {str(e)}")

    def _ensure_labor_product(self, branch_id: str) -> Product:
        sku = "JOB-LABOR"
        product = self.db.query(Product).filter(Product.sku == sku).first()
        if product:
            return product
        product = Product(
            name="Job Labour",
            sku=sku,
            description="Labour service for job cards",
            quantity=0,
            cost_price=Decimal("0"),
            selling_price=Decimal("0"),
            unit_of_measure_id=None,
            branch_id=None,
            product_type="service",
            category="service",
            is_serialized=False,
            active=True,
        )
        self.db.add(product)
        self.db.flush()
        return product

    def _generate_invoice(
        self,
        job: JobCard,
        user_id: Optional[str],
        save_draft: bool = False,
        is_cash_sale: bool = False,
    ) -> Invoice:
        if job.invoice_generated and job.invoice:
            return job.invoice
        if not job.customer_id:
            raise ValueError("Job card requires a customer before invoicing")
        vat_rate = float(self._to_decimal(job.vat_rate, self.default_vat))
        invoice_items: List[Dict[str, object]] = []
        for material in job.materials:
            if self._to_decimal(material.quantity, Decimal("0")) <= 0:
                continue
            invoice_items.append(
                {
                    "product_id": material.product_id,
                    "quantity": float(material.quantity),
                    "price": float(material.unit_price),
                    "vat_rate": vat_rate,
                    "description": material.product.name if material.product else "Material",
                }
            )
        for labor in job.labor_entries:
            if self._to_decimal(labor.total_price, Decimal("0")) <= 0:
                continue
            product = None
            if labor.product_id:
                product = self.db.query(Product).filter(Product.id == labor.product_id).first()
            if not product:
                product = self._ensure_labor_product(job.branch_id)
            quantity = float(self._to_decimal(labor.hours, Decimal("0")) or Decimal("1"))
            invoice_items.append(
                {
                    "product_id": product.id,
                    "quantity": quantity,
                    "price": float(labor.rate),
                    "vat_rate": vat_rate,
                    "description": labor.description,
                }
            )
        if not invoice_items:
            raise ValueError("No billable items available to generate invoice")

        invoice = self.invoice_service.create_invoice(
            customer_id=job.customer_id,
            branch_id=job.branch_id,
            invoice_items=invoice_items,
            due_date=job.due_date or date.today(),
            payment_terms=getattr(job.customer, "payment_terms", 30),
            discount_percentage=0,
            notes=f"Generated from job card {job.job_number}",
            created_by=user_id,
            save_draft=save_draft,
            is_cash_sale=is_cash_sale,
        )
        invoice.job_card_id = job.id
        job.invoice_generated = True
        job.amount_due = self._to_decimal(invoice.total_amount, Decimal("0")) - self._to_decimal(invoice.amount_paid, Decimal("0"))
        self.db.flush()
        return invoice

    def list_technicians(
        self,
        role: Optional[str] = None,
        branch_id: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, object]]:
        query = self.db.query(User).filter(User.active.is_(True))
        if role:
            query = query.filter(func.lower(User.role) == role.lower())
        if branch_id:
            query = query.filter(or_(User.branch_id.is_(None), User.branch_id == branch_id))
        if search:
            like = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(User.first_name).like(like),
                    func.lower(User.last_name).like(like),
                    func.lower(User.username).like(like),
                    func.lower(User.email).like(like),
                )
            )
        users = query.order_by(User.first_name.asc(), User.last_name.asc()).all()
        if role and not users:
            fallback_query = self.db.query(User).filter(User.active.is_(True))
            if branch_id:
                fallback_query = fallback_query.filter(or_(User.branch_id.is_(None), User.branch_id == branch_id))
            if search:
                like = f"%{search.lower()}%"
                fallback_query = fallback_query.filter(
                    or_(
                        func.lower(User.first_name).like(like),
                        func.lower(User.last_name).like(like),
                        func.lower(User.username).like(like),
                        func.lower(User.email).like(like),
                    )
                )
            users = fallback_query.order_by(User.first_name.asc(), User.last_name.asc()).all()
        return [
            {
                "id": user.id,
                "name": self._display_user(user) or user.username,
                "role": user.role,
                "branch_id": user.branch_id,
                "branch_name": user.branch.name if user.branch else None,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "username": user.username,
            }
            for user in users
        ]

    def _serialize_job_card(self, job: JobCard, include_notes: bool = False) -> Dict[str, object]:
        return {
            "id": job.id,
            "job_number": job.job_number,
            "customer_id": job.customer_id,
            "customer_name": job.customer.name if job.customer else None,
            "branch_id": job.branch_id,
            "branch_name": job.branch.name if job.branch else None,
            "status": job.status,
            "job_type": job.job_type,
            "priority": job.priority,
            "description": job.description,
            "notes": job.notes,
            "start_date": job.start_date.isoformat() if job.start_date else None,
            "due_date": job.due_date.isoformat() if job.due_date else None,
            "completed_date": job.completed_date.isoformat() if job.completed_date else None,
            "technician_id": job.technician_id,
            "technician_name": self._display_user(job.technician),
            "currency": job.currency,
            "vat_rate": float(self._to_decimal(job.vat_rate, Decimal("0"))),
            "total_material_cost": float(self._to_decimal(job.total_material_cost, Decimal("0"))),
            "total_material_price": float(self._to_decimal(job.total_material_price, Decimal("0"))),
            "total_labor_cost": float(self._to_decimal(job.total_labor_cost, Decimal("0"))),
            "total_labor_price": float(self._to_decimal(job.total_labor_price, Decimal("0"))),
            "subtotal": float(self._to_decimal(job.subtotal, Decimal("0"))),
            "vat_amount": float(self._to_decimal(job.vat_amount, Decimal("0"))),
            "total_amount": float(self._to_decimal(job.total_amount, Decimal("0"))),
            "amount_paid": float(self._to_decimal(job.amount_paid, Decimal("0"))),
            "amount_due": float(self._to_decimal(job.amount_due, Decimal("0"))),
            "invoice_generated": job.invoice_generated,
            "invoice": self._serialize_invoice(job.invoice) if job.invoice else None,
            "materials": [
                {
                    "id": material.id,
                    "product_id": material.product_id,
                    "product_name": material.product.name if material.product else None,
                    "quantity": float(self._to_decimal(material.quantity, Decimal("0"))),
                    "unit_cost": float(self._to_decimal(material.unit_cost, Decimal("0"))),
                    "unit_price": float(self._to_decimal(material.unit_price, Decimal("0"))),
                    "total_cost": float(self._to_decimal(material.total_cost, Decimal("0"))),
                    "total_price": float(self._to_decimal(material.total_price, Decimal("0"))),
                    "is_issued": material.is_issued,
                    "issued_at": material.issued_at.isoformat() if material.issued_at else None,
                    "inventory_transaction_id": material.inventory_transaction_id,
                    "notes": material.notes,
                }
                for material in job.materials
            ],
            "labor": [
                {
                    "id": labor.id,
                    "description": labor.description,
                    "hours": float(self._to_decimal(labor.hours, Decimal("0"))),
                    "rate": float(self._to_decimal(labor.rate, Decimal("0"))),
                    "total_price": float(self._to_decimal(labor.total_price, Decimal("0"))),
                    "total_cost": float(self._to_decimal(labor.total_cost, Decimal("0"))),
                    "technician_id": labor.technician_id,
                    "technician_name": self._display_user(labor.technician),
                    "product_id": labor.product_id,
                    "notes": labor.notes,
                }
                for labor in job.labor_entries
            ],
            "notes_entries": [
                {
                    "id": note.id,
                    "note": note.note,
                    "author_id": note.author_id,
                    "author_name": self._display_user(note.author),
                    "logged_at": note.logged_at.isoformat(),
                }
                for note in job.notes_entries
            ]
            if include_notes
            else [],
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        }

    def _serialize_invoice(self, invoice: Invoice) -> Dict[str, object]:
        return {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "status": invoice.status,
            "total_amount": float(invoice.total_amount or 0),
            "amount_paid": float(invoice.amount_paid or 0),
            "amount_due": float((invoice.total_amount or 0) - (invoice.amount_paid or 0)),
            "due_date": invoice.due_date.isoformat() if invoice.due_date else None,
        }

    def _display_user(self, user) -> Optional[str]:
        if not user:
            return None
        first = getattr(user, "first_name", "") or ""
        last = getattr(user, "last_name", "") or ""
        full = (first + " " + last).strip()
        return full or getattr(user, "username", None)

    def _to_decimal(self, value, default: Decimal) -> Decimal:
        if value is None:
            return default
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except Exception:
            return default

    def _get_job(self, job_id: str) -> JobCard:
        job = self.db.query(JobCard).filter(JobCard.id == job_id).first()
        if not job:
            raise ValueError("Job card not found")
        return job

    def _validate_technician(self, technician_id: Optional[str], branch_id: Optional[str]) -> Optional[str]:
        if not technician_id:
            return None
        query = self.db.query(User).filter(User.id == technician_id, User.active.is_(True))
        if branch_id:
            query = query.filter(or_(User.branch_id.is_(None), User.branch_id == branch_id))
        technician = query.first()
        if not technician:
            raise ValueError("Selected technician is not available")
        return technician.id
