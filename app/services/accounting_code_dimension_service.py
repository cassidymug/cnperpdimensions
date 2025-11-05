"""
Accounting Code Dimension Requirements Service

This service handles the business logic for managing dimension requirements
for accounting codes.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.accounting import AccountingCode
from app.models.accounting_code_dimensions import (
    AccountingCodeDimensionRequirement,
    AccountingCodeDimensionTemplate,
    AccountingCodeDimensionTemplateItem
)
from app.models.accounting_dimensions import AccountingDimension, AccountingDimensionValue
from app.schemas.accounting_dimensions import AccountingDimensionValueResponse


class AccountingCodeDimensionService:
    """Service for managing dimension requirements on accounting codes"""

    def __init__(self, db: Session):
        self.db = db

    def get_account_dimension_requirements(self, accounting_code_id: str) -> List[Dict[str, Any]]:
        """Get all dimension requirements for an accounting code"""
        requirements = self.db.query(AccountingCodeDimensionRequirement)\
            .filter(AccountingCodeDimensionRequirement.accounting_code_id == accounting_code_id)\
            .order_by(AccountingCodeDimensionRequirement.priority)\
            .all()

        return [req.to_dict() for req in requirements]

    def create_account_dimension_requirement(
        self,
        accounting_code_id: str,
        dimension_id: str,
        is_required: bool = False,
        default_dimension_value_id: Optional[str] = None,
        priority: int = 1,
        description: Optional[str] = None
    ) -> AccountingCodeDimensionRequirement:
        """Create a new dimension requirement for an accounting code"""

        # Validate that the accounting code exists
        account = self.db.query(AccountingCode).filter(AccountingCode.id == accounting_code_id).first()
        if not account:
            raise ValueError(f"Accounting code {accounting_code_id} not found")

        # Validate that the dimension exists
        dimension = self.db.query(AccountingDimension).filter(AccountingDimension.id == dimension_id).first()
        if not dimension:
            raise ValueError(f"Dimension {dimension_id} not found")

        # Check if requirement already exists
        existing = self.db.query(AccountingCodeDimensionRequirement)\
            .filter(and_(
                AccountingCodeDimensionRequirement.accounting_code_id == accounting_code_id,
                AccountingCodeDimensionRequirement.dimension_id == dimension_id
            )).first()

        if existing:
            raise ValueError(f"Dimension requirement already exists for this account and dimension")

        # Validate default dimension value if provided
        if default_dimension_value_id:
            dim_value = self.db.query(AccountingDimensionValue)\
                .filter(and_(
                    AccountingDimensionValue.id == default_dimension_value_id,
                    AccountingDimensionValue.dimension_id == dimension_id
                )).first()
            if not dim_value:
                raise ValueError(f"Default dimension value {default_dimension_value_id} not found or doesn't belong to dimension {dimension_id}")

        requirement = AccountingCodeDimensionRequirement(
            accounting_code_id=accounting_code_id,
            dimension_id=dimension_id,
            is_required=is_required,
            default_dimension_value_id=default_dimension_value_id,
            priority=priority,
            description=description
        )

        self.db.add(requirement)
        self.db.commit()
        self.db.refresh(requirement)

        return requirement

    def update_account_dimension_requirement(
        self,
        requirement_id: str,
        is_required: Optional[bool] = None,
        default_dimension_value_id: Optional[str] = None,
        priority: Optional[int] = None,
        description: Optional[str] = None
    ) -> AccountingCodeDimensionRequirement:
        """Update an existing dimension requirement"""

        requirement = self.db.query(AccountingCodeDimensionRequirement)\
            .filter(AccountingCodeDimensionRequirement.id == requirement_id).first()

        if not requirement:
            raise ValueError(f"Dimension requirement {requirement_id} not found")

        if is_required is not None:
            requirement.is_required = is_required

        if default_dimension_value_id is not None:
            if default_dimension_value_id:
                # Validate the dimension value belongs to the requirement's dimension
                dim_value = self.db.query(AccountingDimensionValue)\
                    .filter(and_(
                        AccountingDimensionValue.id == default_dimension_value_id,
                        AccountingDimensionValue.dimension_id == requirement.dimension_id
                    )).first()
                if not dim_value:
                    raise ValueError(f"Dimension value {default_dimension_value_id} not found or doesn't belong to the requirement's dimension")

            requirement.default_dimension_value_id = default_dimension_value_id

        if priority is not None:
            requirement.priority = priority

        if description is not None:
            requirement.description = description

        self.db.commit()
        self.db.refresh(requirement)

        return requirement

    def delete_account_dimension_requirement(self, requirement_id: str) -> bool:
        """Delete a dimension requirement"""

        requirement = self.db.query(AccountingCodeDimensionRequirement)\
            .filter(AccountingCodeDimensionRequirement.id == requirement_id).first()

        if not requirement:
            return False

        self.db.delete(requirement)
        self.db.commit()

        return True

    def get_dimension_balances_for_account(self, accounting_code_id: str) -> Dict[str, Any]:
        """Get account balance broken down by dimensions"""

        # This would require complex queries joining journal entries with dimension assignments
        # For now, return a placeholder structure

        account = self.db.query(AccountingCode).filter(AccountingCode.id == accounting_code_id).first()
        if not account:
            raise ValueError(f"Accounting code {accounting_code_id} not found")

        # Get dimension requirements for this account
        requirements = self.get_account_dimension_requirements(accounting_code_id)

        # TODO: Implement actual dimension-based balance calculation
        # This would involve:
        # 1. Get all journal entries for this account
        # 2. Get dimension assignments for each entry
        # 3. Group balances by dimension values
        # 4. Calculate totals for each dimension combination

        return {
            "account_id": accounting_code_id,
            "account_code": account.code,
            "account_name": account.name,
            "total_balance": float(account.balance or 0),
            "dimension_requirements": requirements,
            "dimension_balances": [],  # TODO: Implement actual calculation
            "message": "Dimension-based balance calculation not yet implemented"
        }

    def apply_template_to_accounts(
        self,
        template_id: str,
        account_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Apply a dimension template to accounting codes"""

        template = self.db.query(AccountingCodeDimensionTemplate)\
            .filter(AccountingCodeDimensionTemplate.id == template_id).first()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Get accounts to apply template to
        if account_ids:
            accounts = self.db.query(AccountingCode)\
                .filter(AccountingCode.id.in_(account_ids)).all()
        else:
            # Apply to all accounts matching template criteria
            query = self.db.query(AccountingCode)

            if template.account_type:
                query = query.filter(AccountingCode.account_type == template.account_type)

            if template.category:
                query = query.filter(AccountingCode.category == template.category)

            if template.account_code_pattern:
                # Simple pattern matching - extend as needed
                if template.account_code_pattern.endswith('*'):
                    prefix = template.account_code_pattern[:-1]
                    query = query.filter(AccountingCode.code.like(f"{prefix}%"))

            accounts = query.all()

        results = {
            "template_id": template_id,
            "template_name": template.name,
            "accounts_processed": 0,
            "requirements_created": 0,
            "errors": []
        }

        for account in accounts:
            try:
                results["accounts_processed"] += 1

                # Apply each template item to this account
                for template_item in template.dimension_requirements:
                    try:
                        self.create_account_dimension_requirement(
                            accounting_code_id=account.id,
                            dimension_id=template_item.dimension_id,
                            is_required=template_item.is_required,
                            default_dimension_value_id=template_item.default_dimension_value_id,
                            priority=template_item.priority,
                            description=f"Applied from template: {template.name}"
                        )
                        results["requirements_created"] += 1
                    except ValueError as e:
                        # Skip if requirement already exists or other validation error
                        if "already exists" not in str(e):
                            results["errors"].append(f"Account {account.code}: {str(e)}")

            except Exception as e:
                results["errors"].append(f"Account {account.code}: {str(e)}")

        return results
