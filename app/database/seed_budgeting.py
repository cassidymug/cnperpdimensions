#!/usr/bin/env python3
"""
Seed data for Budgeting module
"""

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.budgeting import (
    Budget, BudgetAllocation, BudgetTransaction, BudgetUserAccess, BudgetRequest
)
from app.models.user import User
from app.models.branch import Branch
from app.models.banking import BankAccount


def seed_budgeting_data(db: Session):
    """Seed budgeting data"""
    
    # Get existing users and branches for references
    users = db.query(User).all()
    branches = db.query(Branch).all()
    bank_accounts = db.query(BankAccount).all()
    
    if not users or not branches:
        print("Skipping budgeting seed - no users or branches found")
        return
    
    # Create sample budgets
    budgets = [
        {
            "name": "IT Infrastructure Budget 2024",
            "description": "Budget for IT infrastructure improvements and maintenance",
            "budget_type": "department",
            "total_amount": Decimal("50000.00"),
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
            "status": "active",
            "is_approved": True,
            "approved_by": users[0].id if users else None,
            "approved_at": datetime.now(),
            "bank_account_id": bank_accounts[0].id if bank_accounts else None,
            "branch_id": branches[0].id if branches else None,
        },
        {
            "name": "Marketing Campaign Q1",
            "description": "Marketing budget for Q1 campaigns and promotions",
            "budget_type": "project",
            "total_amount": Decimal("25000.00"),
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 3, 31),
            "status": "active",
            "is_approved": True,
            "approved_by": users[0].id if users else None,
            "approved_at": datetime.now(),
            "bank_account_id": bank_accounts[0].id if bank_accounts else None,
            "branch_id": branches[0].id if branches else None,
        },
        {
            "name": "Office Supplies Budget",
            "description": "Monthly budget for office supplies and stationery",
            "budget_type": "category",
            "total_amount": Decimal("5000.00"),
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
            "status": "active",
            "is_approved": True,
            "approved_by": users[0].id if users else None,
            "approved_at": datetime.now(),
            "bank_account_id": bank_accounts[0].id if bank_accounts else None,
            "branch_id": branches[0].id if branches else None,
        }
    ]
    
    created_budgets = []
    for budget_data in budgets:
        budget = Budget(**budget_data)
        budget.remaining_amount = budget.total_amount
        db.add(budget)
        created_budgets.append(budget)
    
    db.commit()
    
    # Create budget allocations
    allocations = [
        {
            "budget_id": created_budgets[0].id,  # IT Infrastructure
            "name": "Hardware Upgrades",
            "description": "Allocation for computer hardware upgrades",
            "allocated_amount": Decimal("20000.00"),
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 6, 30),
            "status": "active",
            "category": "hardware",
            "project_code": "IT-HW-2024"
        },
        {
            "budget_id": created_budgets[0].id,  # IT Infrastructure
            "name": "Software Licenses",
            "description": "Allocation for software licenses and subscriptions",
            "allocated_amount": Decimal("15000.00"),
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 12, 31),
            "status": "active",
            "category": "software",
            "project_code": "IT-SW-2024"
        },
        {
            "budget_id": created_budgets[1].id,  # Marketing Campaign
            "name": "Digital Advertising",
            "description": "Allocation for digital advertising campaigns",
            "allocated_amount": Decimal("15000.00"),
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 3, 31),
            "status": "active",
            "category": "advertising",
            "project_code": "MKT-DIG-2024"
        },
        {
            "budget_id": created_budgets[1].id,  # Marketing Campaign
            "name": "Print Materials",
            "description": "Allocation for print materials and brochures",
            "allocated_amount": Decimal("10000.00"),
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 3, 31),
            "status": "active",
            "category": "print",
            "project_code": "MKT-PRN-2024"
        }
    ]
    
    created_allocations = []
    for allocation_data in allocations:
        allocation = BudgetAllocation(**allocation_data)
        allocation.remaining_amount = allocation.allocated_amount
        
        # Update budget amounts
        budget = db.query(Budget).filter(Budget.id == allocation.budget_id).first()
        budget.allocated_amount += allocation.allocated_amount
        budget.remaining_amount -= allocation.allocated_amount
        
        db.add(allocation)
        created_allocations.append(allocation)
    
    db.commit()
    
    # Create sample transactions
    transactions = [
        {
            "budget_id": created_budgets[0].id,
            "allocation_id": created_allocations[0].id,
            "transaction_type": "purchase",
            "amount": Decimal("5000.00"),
            "description": "Purchase of 10 new laptops for IT department",
            "reference": "PO-IT-001",
            "status": "approved",
            "created_by": users[0].id if users else None,
            "approved_by": users[0].id if users else None,
            "approved_at": datetime.now()
        },
        {
            "budget_id": created_budgets[1].id,
            "allocation_id": created_allocations[2].id,
            "transaction_type": "expense",
            "amount": Decimal("3000.00"),
            "description": "Google Ads campaign for Q1",
            "reference": "INV-GA-001",
            "status": "approved",
            "created_by": users[0].id if users else None,
            "approved_by": users[0].id if users else None,
            "approved_at": datetime.now()
        },
        {
            "budget_id": created_budgets[2].id,
            "transaction_type": "purchase",
            "amount": Decimal("500.00"),
            "description": "Monthly office supplies purchase",
            "reference": "PO-OFF-001",
            "status": "approved",
            "created_by": users[0].id if users else None,
            "approved_by": users[0].id if users else None,
            "approved_at": datetime.now()
        }
    ]
    
    for transaction_data in transactions:
        transaction = BudgetTransaction(**transaction_data)
        db.add(transaction)
        
        # Update budget and allocation amounts
        budget = db.query(Budget).filter(Budget.id == transaction.budget_id).first()
        budget.spent_amount += transaction.amount
        budget.remaining_amount -= transaction.amount
        
        if transaction.allocation_id:
            allocation = db.query(BudgetAllocation).filter(BudgetAllocation.id == transaction.allocation_id).first()
            allocation.spent_amount += transaction.amount
            allocation.remaining_amount -= transaction.amount
    
    db.commit()
    
    # Create user access permissions
    user_access = [
        {
            "budget_id": created_budgets[0].id,
            "user_id": users[0].id if users else None,
            "can_view": True,
            "can_allocate": True,
            "can_spend": True,
            "can_approve": True,
            "can_manage": True,
            "access_start_date": date(2024, 1, 1),
            "access_end_date": date(2024, 12, 31),
            "is_active": True
        },
        {
            "budget_id": created_budgets[1].id,
            "user_id": users[0].id if users else None,
            "can_view": True,
            "can_allocate": True,
            "can_spend": True,
            "can_approve": False,
            "can_manage": False,
            "access_start_date": date(2024, 1, 1),
            "access_end_date": date(2024, 3, 31),
            "is_active": True
        }
    ]
    
    for access_data in user_access:
        access = BudgetUserAccess(**access_data)
        db.add(access)
    
    db.commit()
    
    # Create sample budget requests
    requests = [
        {
            "title": "Additional IT Equipment Request",
            "description": "Request for additional monitors and peripherals",
            "requested_amount": Decimal("3000.00"),
            "budget_id": created_budgets[0].id,
            "priority": "normal",
            "urgency_level": 2,
            "requested_by": users[0].id if users else None,
            "requested_at": datetime.now(),
            "status": "pending"
        },
        {
            "title": "Marketing Event Budget Request",
            "description": "Request for additional budget for trade show participation",
            "requested_amount": Decimal("8000.00"),
            "budget_id": created_budgets[1].id,
            "priority": "high",
            "urgency_level": 4,
            "requested_by": users[0].id if users else None,
            "requested_at": datetime.now(),
            "status": "pending"
        }
    ]
    
    for request_data in requests:
        request = BudgetRequest(**request_data)
        db.add(request)
    
    db.commit()
    
    print(f"✅ Seeded {len(created_budgets)} budgets, {len(created_allocations)} allocations, "
          f"{len(transactions)} transactions, {len(user_access)} user access records, "
          f"and {len(requests)} budget requests")
