from typing import List, Dict, Optional, Tuple
from decimal import Decimal
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models.budgeting import (
    Budget, BudgetAllocation, BudgetTransaction, BudgetUserAccess, BudgetRequest
)
from app.models.purchases import Purchase, PurchaseOrder
from app.models.banking import BankTransaction


class BudgetingService:
    """Comprehensive budgeting business logic service"""

    def __init__(self, db: Session):
        self.db = db

    def create_budget(self, budget_data: Dict) -> Budget:
        """Create a new budget with initial setup"""
        try:
            budget = Budget(**budget_data)
            budget.remaining_amount = budget.total_amount
            
            self.db.add(budget)
            self.db.commit()
            self.db.refresh(budget)
            
            return budget
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error creating budget: {str(e)}")

    def create_allocation(self, allocation_data: Dict) -> BudgetAllocation:
        """Create a budget allocation"""
        try:
            # Validate budget exists and has sufficient remaining amount
            budget = self.db.query(Budget).filter(Budget.id == allocation_data['budget_id']).first()
            if not budget:
                raise Exception("Budget not found")
            
            if budget.remaining_amount < allocation_data['allocated_amount']:
                raise Exception("Insufficient budget remaining for allocation")
            
            allocation = BudgetAllocation(**allocation_data)
            allocation.remaining_amount = allocation.allocated_amount
            
            self.db.add(allocation)
            
            # Update budget amounts
            budget.allocated_amount += allocation.allocated_amount
            budget.remaining_amount -= allocation.allocated_amount
            
            self.db.commit()
            self.db.refresh(allocation)
            
            return allocation
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error creating allocation: {str(e)}")

    def record_transaction(self, transaction_data: Dict, user_id: str) -> BudgetTransaction:
        """Record a budget transaction (purchase, expense, etc.)"""
        try:
            # Validate budget and allocation
            budget = self.db.query(Budget).filter(Budget.id == transaction_data['budget_id']).first()
            if not budget:
                raise Exception("Budget not found")
            
            allocation = None
            if transaction_data.get('allocation_id'):
                allocation = self.db.query(BudgetAllocation).filter(
                    BudgetAllocation.id == transaction_data['allocation_id']
                ).first()
                if not allocation:
                    raise Exception("Allocation not found")
            
            # Check if user has spending permissions
            if not self._user_can_spend(user_id, transaction_data['budget_id']):
                raise Exception("User does not have spending permissions for this budget")
            
            # Check if sufficient funds available
            if allocation and allocation.remaining_amount < transaction_data['amount']:
                raise Exception("Insufficient allocation remaining for transaction")
            
            transaction = BudgetTransaction(**transaction_data)
            transaction.created_by = user_id
            
            self.db.add(transaction)
            
            # Update amounts
            if allocation:
                allocation.spent_amount += transaction.amount
                allocation.remaining_amount -= transaction.amount
            
            budget.spent_amount += transaction.amount
            budget.remaining_amount -= transaction.amount
            
            self.db.commit()
            self.db.refresh(transaction)
            
            return transaction
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error recording transaction: {str(e)}")

    def approve_budget(self, budget_id: str, user_id: str, approved_amount: Optional[Decimal] = None) -> Budget:
        """Approve a budget"""
        try:
            budget = self.db.query(Budget).filter(Budget.id == budget_id).first()
            if not budget:
                raise Exception("Budget not found")
            
            if not self._user_can_approve(user_id, budget_id):
                raise Exception("User does not have approval permissions for this budget")
            
            budget.is_approved = True
            budget.approved_by = user_id
            budget.approved_at = datetime.now()
            
            if approved_amount:
                budget.total_amount = approved_amount
                budget.remaining_amount = approved_amount - budget.spent_amount
            
            self.db.commit()
            self.db.refresh(budget)
            
            return budget
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error approving budget: {str(e)}")

    def grant_user_access(self, access_data: Dict) -> BudgetUserAccess:
        """Grant user access to a budget"""
        try:
            access = BudgetUserAccess(**access_data)
            self.db.add(access)
            self.db.commit()
            self.db.refresh(access)
            
            return access
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error granting user access: {str(e)}")

    def create_budget_request(self, request_data: Dict, user_id: str) -> BudgetRequest:
        """Create a budget request"""
        try:
            request = BudgetRequest(**request_data)
            request.requested_by = user_id
            request.requested_at = datetime.now()
            
            self.db.add(request)
            self.db.commit()
            self.db.refresh(request)
            
            return request
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error creating budget request: {str(e)}")

    def approve_budget_request(self, request_id: str, user_id: str, approved_amount: Optional[Decimal] = None, rejection_reason: Optional[str] = None) -> BudgetRequest:
        """Approve or reject a budget request"""
        try:
            request = self.db.query(BudgetRequest).filter(BudgetRequest.id == request_id).first()
            if not request:
                raise Exception("Budget request not found")
            
            if request.status != "pending":
                raise Exception("Request is not in pending status")
            
            if approved_amount:
                request.status = "approved"
                request.approved_by = user_id
                request.approved_at = datetime.now()
                request.approved_amount = approved_amount
            else:
                request.status = "rejected"
                request.approved_by = user_id
                request.approved_at = datetime.now()
                request.rejection_reason = rejection_reason
            
            self.db.commit()
            self.db.refresh(request)
            
            return request
        except Exception as e:
            self.db.rollback()
            raise Exception(f"Error processing budget request: {str(e)}")

    def get_budget_analytics(self, branch_id: Optional[str] = None) -> Dict:
        """Get comprehensive budget analytics"""
        try:
            query = self.db.query(Budget)
            if branch_id:
                query = query.filter(Budget.branch_id == branch_id)
            
            budgets = query.all()
            
            total_budgets = len(budgets)
            active_budgets = len([b for b in budgets if b.status == "active"])
            total_allocated = sum(b.allocated_amount for b in budgets)
            total_spent = sum(b.spent_amount for b in budgets)
            total_remaining = sum(b.remaining_amount for b in budgets)
            
            average_utilization = 0
            if total_allocated > 0:
                average_utilization = (total_spent / total_allocated) * 100
            
            budget_summaries = []
            for budget in budgets:
                utilization = 0
                if budget.allocated_amount > 0:
                    utilization = (budget.spent_amount / budget.allocated_amount) * 100
                
                budget_summaries.append({
                    "budget_id": budget.id,
                    "budget_name": budget.name,
                    "total_amount": budget.total_amount,
                    "allocated_amount": budget.allocated_amount,
                    "spent_amount": budget.spent_amount,
                    "remaining_amount": budget.remaining_amount,
                    "utilization_percentage": utilization,
                    "status": budget.status
                })
            
            return {
                "total_budgets": total_budgets,
                "active_budgets": active_budgets,
                "total_allocated": total_allocated,
                "total_spent": total_spent,
                "total_remaining": total_remaining,
                "average_utilization": average_utilization,
                "budget_summaries": budget_summaries
            }
        except Exception as e:
            raise Exception(f"Error getting budget analytics: {str(e)}")

    def link_purchase_to_budget(self, purchase_id: str, budget_id: str, user_id: str, allocation_id: Optional[str] = None) -> BudgetTransaction:
        """Link a purchase to a budget transaction"""
        try:
            purchase = self.db.query(Purchase).filter(Purchase.id == purchase_id).first()
            if not purchase:
                raise Exception("Purchase not found")
            
            transaction_data = {
                "budget_id": budget_id,
                "allocation_id": allocation_id,
                "transaction_type": "purchase",
                "amount": purchase.total_amount,
                "description": f"Purchase from {purchase.supplier.name if purchase.supplier else 'Unknown'}",
                "reference": purchase.reference or purchase.id,
                "purchase_id": purchase_id,
                "status": "approved"
            }
            
            return self.record_transaction(transaction_data, user_id)
        except Exception as e:
            raise Exception(f"Error linking purchase to budget: {str(e)}")

    def link_purchase_order_to_budget(self, po_id: str, budget_id: str, user_id: str, allocation_id: Optional[str] = None) -> BudgetTransaction:
        """Link a purchase order to a budget transaction"""
        try:
            po = self.db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
            if not po:
                raise Exception("Purchase order not found")
            
            transaction_data = {
                "budget_id": budget_id,
                "allocation_id": allocation_id,
                "transaction_type": "purchase_order",
                "amount": po.total_amount or 0,
                "description": f"Purchase Order {po.po_number or po.id}",
                "reference": po.po_number or po.id,
                "purchase_order_id": po_id,
                "status": "pending"
            }
            
            return self.record_transaction(transaction_data, user_id)
        except Exception as e:
            raise Exception(f"Error linking purchase order to budget: {str(e)}")

    # Access control methods
    def _user_can_view(self, user_id: str, budget_id: str) -> bool:
        """Check if user can view budget"""
        access = self.db.query(BudgetUserAccess).filter(
            and_(
                BudgetUserAccess.budget_id == budget_id,
                BudgetUserAccess.user_id == user_id,
                BudgetUserAccess.is_active == True,
                BudgetUserAccess.can_view == True
            )
        ).first()
        return access is not None

    def _user_can_spend(self, user_id: str, budget_id: str) -> bool:
        """Check if user can spend from budget"""
        access = self.db.query(BudgetUserAccess).filter(
            and_(
                BudgetUserAccess.budget_id == budget_id,
                BudgetUserAccess.user_id == user_id,
                BudgetUserAccess.is_active == True,
                BudgetUserAccess.can_spend == True
            )
        ).first()
        return access is not None

    def _user_can_approve(self, user_id: str, budget_id: str) -> bool:
        """Check if user can approve budget"""
        access = self.db.query(BudgetUserAccess).filter(
            and_(
                BudgetUserAccess.budget_id == budget_id,
                BudgetUserAccess.user_id == user_id,
                BudgetUserAccess.is_active == True,
                BudgetUserAccess.can_approve == True
            )
        ).first()
        return access is not None

    def _user_can_manage(self, user_id: str, budget_id: str) -> bool:
        """Check if user can manage budget"""
        access = self.db.query(BudgetUserAccess).filter(
            and_(
                BudgetUserAccess.budget_id == budget_id,
                BudgetUserAccess.user_id == user_id,
                BudgetUserAccess.is_active == True,
                BudgetUserAccess.can_manage == True
            )
        ).first()
        return access is not None
