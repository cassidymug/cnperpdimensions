from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from app.models.asset_management import (
    Asset, AssetMaintenance, AssetDepreciation, AssetImage, AssetCategoryConfig,
    AssetCategory, AssetStatus, DepreciationMethod
)
from app.models.accounting import AccountingEntry, JournalEntry, AccountingCode
import uuid


class AssetManagementService:
    def __init__(self, db: Session):
        self.db = db

    def create_asset(self, asset_data: Dict[str, Any]) -> Asset:
        """Create a new asset"""
        # Optionally skip accounting entry creation (e.g., when AP journals handle posting)
        skip_accounting_entry: bool = bool(asset_data.pop('skip_accounting_entry', False))
        # Generate asset code if not provided
        if not asset_data.get('asset_code'):
            asset_data['asset_code'] = self._generate_asset_code(asset_data.get('category'))

        # Set current value to purchase cost initially
        if not asset_data.get('current_value'):
            asset_data['current_value'] = asset_data.get('purchase_cost', 0)

        # Set default depreciation settings based on category
        if not asset_data.get('depreciation_method'):
            category_config = self.get_category_config(asset_data.get('category'))
            if category_config:
                asset_data['depreciation_method'] = category_config.default_depreciation_method
                asset_data['useful_life_years'] = category_config.default_useful_life_years
                asset_data['depreciation_rate'] = category_config.default_depreciation_rate
                if not asset_data.get('salvage_value'):
                    salvage_percentage = category_config.default_salvage_value_percentage
                    asset_data['salvage_value'] = (asset_data.get('purchase_cost', 0) * salvage_percentage) / 100

        asset = Asset(**asset_data)
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)

        # Create accounting entry for asset purchase unless explicitly skipped
        if not skip_accounting_entry:
            self._create_asset_purchase_entry(asset)

        return asset

    def update_asset(self, asset_id: str, asset_data: Dict[str, Any]) -> Asset:
        """Update an existing asset"""
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise ValueError("Asset not found")

        for key, value in asset_data.items():
            if hasattr(asset, key):
                setattr(asset, key, value)

        self.db.commit()
        self.db.refresh(asset)
        return asset

    def delete_asset(self, asset_id: str) -> bool:
        """Delete an asset"""
        asset = self.db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            raise ValueError("Asset not found")

        self.db.delete(asset)
        self.db.commit()
        return True

    def get_asset(self, asset_id: str) -> Optional[Asset]:
        """Get asset by ID"""
        return self.db.query(Asset).filter(Asset.id == asset_id).first()

    def get_assets(
        self,
        category: Optional[str] = None,
        status: Optional[str] = None,
        branch_id: Optional[str] = None,
        assigned_to: Optional[str] = None,
        search: Optional[str] = None,
        ifrs_category: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Asset]:
        """Get assets with filters"""
        query = self.db.query(Asset)

        if category:
            query = query.filter(Asset.category == category)

        if status:
            query = query.filter(Asset.status == status)

        if branch_id:
            query = query.filter(Asset.branch_id == branch_id)

        if assigned_to:
            query = query.filter(Asset.assigned_to == assigned_to)

        if ifrs_category:
            query = query.filter(Asset.ifrs_category == ifrs_category)

        if search:
            search_filter = or_(
                Asset.name.ilike(f"%{search}%"),
                Asset.asset_code.ilike(f"%{search}%"),
                Asset.serial_number.ilike(f"%{search}%"),
                Asset.description.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)

        return query.offset(offset).limit(limit).all()

    def get_asset_summary(self) -> Dict[str, Any]:
        """Get asset summary statistics"""
        total_assets = self.db.query(Asset).count()
        active_assets = self.db.query(Asset).filter(Asset.status == AssetStatus.ACTIVE).count()

        # Calculate total values
        result = self.db.query(
            func.sum(Asset.purchase_cost).label('total_purchase_cost'),
            func.sum(Asset.current_value).label('total_current_value'),
            func.sum(Asset.accumulated_depreciation).label('total_depreciation')
        ).first()

        # Assets by category
        category_stats = self.db.query(
            Asset.category,
            func.count(Asset.id).label('count'),
            func.sum(Asset.current_value).label('total_value')
        ).group_by(Asset.category).all()

        # Assets by status
        status_stats = self.db.query(
            Asset.status,
            func.count(Asset.id).label('count')
        ).group_by(Asset.status).all()

        return {
            'total_assets': total_assets,
            'active_assets': active_assets,
            'total_purchase_cost': float(result.total_purchase_cost or 0),
            'total_current_value': float(result.total_current_value or 0),
            'total_depreciation': float(result.total_depreciation or 0),
            'category_stats': [
                {
                    'category': stat.category.value if stat.category else None,
                    'count': stat.count,
                    'total_value': float(stat.total_value or 0)
                } for stat in category_stats
            ],
            'status_stats': [
                {
                    'status': stat.status.value if stat.status else None,
                    'count': stat.count
                } for stat in status_stats
            ]
        }

    def calculate_depreciation(self, asset_id: str, as_of_date: date = None) -> Dict[str, Any]:
        """Calculate depreciation for an asset"""
        asset = self.get_asset(asset_id)
        if not asset:
            raise ValueError("Asset not found")

        return asset.calculate_depreciation(as_of_date)

    def record_depreciation(self, asset_id: str, depreciation_date: date = None) -> AssetDepreciation:
        """Record depreciation for an asset"""
        if depreciation_date is None:
            depreciation_date = date.today()

        asset = self.get_asset(asset_id)
        if not asset:
            raise ValueError("Asset not found")

        # Calculate depreciation
        depreciation_data = asset.calculate_depreciation(depreciation_date)

        # Check if there's actually depreciation to record
        if depreciation_data['depreciation_amount'] <= 0:
            raise ValueError("No depreciation to record for this period")

        # Create depreciation record
        depreciation_record = AssetDepreciation(
            asset_id=asset_id,
            depreciation_date=depreciation_date,
            depreciation_amount=depreciation_data['depreciation_amount'],
            accumulated_depreciation=depreciation_data['accumulated_depreciation'],
            book_value=depreciation_data['book_value']
        )

        self.db.add(depreciation_record)

        # Update asset values
        asset.accumulated_depreciation = depreciation_data['accumulated_depreciation']
        asset.current_value = depreciation_data['book_value']

        # Commit the depreciation record and asset update first
        self.db.commit()
        self.db.refresh(depreciation_record)

        # Create accounting entry for depreciation (separate transaction)
        try:
            self._create_depreciation_entry(asset, depreciation_data['depreciation_amount'])
        except Exception as e:
            # Log but don't fail - the depreciation is recorded even if accounting entry fails
            print(f"Warning: Depreciation recorded but accounting entry failed: {str(e)}")

        return depreciation_record

    def create_maintenance_record(self, maintenance_data: Dict[str, Any]) -> AssetMaintenance:
        """Create a maintenance record for an asset"""
        maintenance = AssetMaintenance(**maintenance_data)
        self.db.add(maintenance)
        self.db.commit()
        self.db.refresh(maintenance)
        return maintenance

    def get_maintenance_records(self, asset_id: str) -> List[AssetMaintenance]:
        """Get maintenance records for an asset"""
        return self.db.query(AssetMaintenance).filter(
            AssetMaintenance.asset_id == asset_id
        ).order_by(AssetMaintenance.maintenance_date.desc()).all()

    def get_upcoming_maintenance(self, days_ahead: int = 30) -> List[Asset]:
        """Get assets with upcoming maintenance"""
        target_date = date.today() + timedelta(days=days_ahead)
        return self.db.query(Asset).filter(
            and_(
                Asset.next_service_date <= target_date,
                Asset.next_service_date >= date.today(),
                Asset.status == AssetStatus.ACTIVE
            )
        ).all()

    def get_depreciation_report(self, as_of_date: date = None) -> Dict[str, Any]:
        """Generate depreciation report"""
        if as_of_date is None:
            as_of_date = date.today()

        assets = self.db.query(Asset).filter(Asset.status == AssetStatus.ACTIVE).all()

        report_data = []
        total_purchase_cost = 0
        total_current_value = 0
        total_depreciation = 0

        for asset in assets:
            depreciation_data = asset.calculate_depreciation(as_of_date)

            report_data.append({
                'asset_id': asset.id,
                'asset_code': asset.asset_code,
                'name': asset.name,
                'category': asset.category.value if asset.category else None,
                'purchase_date': asset.purchase_date.isoformat() if asset.purchase_date else None,
                'purchase_cost': float(asset.purchase_cost or 0),
                'current_value': float(asset.current_value or 0),
                'book_value': depreciation_data['book_value'],
                'accumulated_depreciation': depreciation_data['accumulated_depreciation'],
                'depreciation_method': asset.depreciation_method.value if asset.depreciation_method else None,
                'useful_life_years': asset.useful_life_years
            })

            total_purchase_cost += float(asset.purchase_cost or 0)
            total_current_value += depreciation_data['book_value']
            total_depreciation += depreciation_data['accumulated_depreciation']

        return {
            'as_of_date': as_of_date.isoformat(),
            'total_purchase_cost': total_purchase_cost,
            'total_current_value': total_current_value,
            'total_depreciation': total_depreciation,
            'assets': report_data
        }

    def get_asset_by_serial_number(self, serial_number: str) -> Optional[Asset]:
        """Get asset by serial number"""
        return self.db.query(Asset).filter(Asset.serial_number == serial_number).first()

    def get_vehicle_by_registration(self, registration: str) -> Optional[Asset]:
        """Get vehicle by registration number"""
        return self.db.query(Asset).filter(
            and_(
                Asset.vehicle_registration == registration,
                Asset.category == AssetCategory.VEHICLE
            )
        ).first()

    def get_category_config(self, category: str) -> Optional[AssetCategoryConfig]:
        """Get category configuration"""
        return self.db.query(AssetCategoryConfig).filter(
            AssetCategoryConfig.category == category
        ).first()

    def create_category_config(self, config_data: Dict[str, Any]) -> AssetCategoryConfig:
        """Create category configuration"""
        config = AssetCategoryConfig(**config_data)
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def get_all_category_configs(self) -> List[AssetCategoryConfig]:
        """Get all category configurations"""
        return self.db.query(AssetCategoryConfig).all()

    def _generate_asset_code(self, category: str) -> str:
        """Generate unique asset code"""
        prefix = category.upper()[:3] if category else "AST"
        year = datetime.now().year

        # Get count of assets for this category this year
        count = self.db.query(Asset).filter(
            and_(
                Asset.category == category,
                func.extract('year', Asset.created_at) == year
            )
        ).count()

        return f"{prefix}{year}{count + 1:04d}"

    def _create_asset_purchase_entry(self, asset: Asset):
        """Create accounting entry for asset purchase"""
        if not asset.accounting_code_id:
            return

        # Create accounting entry
        entry = AccountingEntry(
            date_prepared=asset.purchase_date,
            date_posted=asset.purchase_date,
            particulars=f"Asset Purchase: {asset.name}",
            book="Asset Register",
            status="posted",
            branch_id=asset.branch_id
        )
        self.db.add(entry)
        self.db.flush()  # Get the ID

        # Create journal entries
        # Debit Asset Account
        asset_entry = JournalEntry(
            accounting_code_id=asset.accounting_code_id,
            accounting_entry_id=entry.id,
            entry_type="debit",
            narration=f"Asset Purchase: {asset.name}",
            date=asset.purchase_date,
            debit_amount=asset.purchase_cost,
            credit_amount=0,
            branch_id=asset.branch_id
        )
        self.db.add(asset_entry)

        # Credit Bank/Cash Account (assuming cash purchase for now)
        # You might want to make this configurable
        cash_account = self.db.query(AccountingCode).filter(
            AccountingCode.code == "1111"  # Cash in Hand
        ).first()

        if cash_account:
            cash_entry = JournalEntry(
                accounting_code_id=cash_account.id,
                accounting_entry_id=entry.id,
                entry_type="credit",
                narration=f"Payment for Asset: {asset.name}",
                date=asset.purchase_date,
                debit_amount=0,
                credit_amount=asset.purchase_cost,
                branch_id=asset.branch_id
            )
            self.db.add(cash_entry)

        self.db.commit()

    def _create_depreciation_entry(self, asset: Asset, depreciation_amount: float):
        """Create accounting entry for depreciation"""
        if depreciation_amount <= 0:
            return

        try:
            # Create accounting entry
            entry = AccountingEntry(
                date_prepared=date.today(),
                date_posted=date.today(),
                particulars=f"Depreciation: {asset.name} ({asset.asset_code})",
                book="Asset Register",
                status="posted",
                branch_id=asset.branch_id
            )
            self.db.add(entry)
            self.db.flush()

            # Create journal entries
            # Debit Depreciation Expense (5228 or similar)
            depreciation_expense_account = self.db.query(AccountingCode).filter(
                or_(
                    AccountingCode.code == "5228",
                    AccountingCode.code == "5200",
                    AccountingCode.name.ilike("%depreciation%expense%")
                )
            ).first()

            if not depreciation_expense_account:
                # Create default depreciation expense account if it doesn't exist
                depreciation_expense_account = AccountingCode(
                    code="5228",
                    name="Depreciation Expense",
                    account_type="Expense",
                    category="Operating Expenses"
                )
                self.db.add(depreciation_expense_account)
                self.db.flush()

            depreciation_entry = JournalEntry(
                accounting_code_id=depreciation_expense_account.id,
                accounting_entry_id=entry.id,
                entry_type="debit",
                narration=f"Depreciation: {asset.name}",
                date=date.today(),
                debit_amount=depreciation_amount,
                credit_amount=0,
                branch_id=asset.branch_id
            )
            self.db.add(depreciation_entry)

            # Credit Accumulated Depreciation (122x or similar contra-asset account)
            # Get the asset's main accounting code first
            accumulated_depreciation_account = None

            if asset.accounting_code_id:
                # Try to find related accumulated depreciation account
                asset_account = self.db.query(AccountingCode).filter(
                    AccountingCode.id == asset.accounting_code_id
                ).first()

                if asset_account and asset_account.code:
                    # Look for accumulated depreciation account related to this asset type
                    # For example, if asset is 1210, look for 1220 (Accumulated Depreciation)
                    base_code = asset_account.code[:3]  # Get first 3 digits
                    accumulated_depreciation_account = self.db.query(AccountingCode).filter(
                        AccountingCode.code.like(f"{base_code}%"),
                        AccountingCode.name.ilike("%accumulated%depreciation%")
                    ).first()

            if not accumulated_depreciation_account:
                # Try generic accumulated depreciation accounts
                accumulated_depreciation_account = self.db.query(AccountingCode).filter(
                    or_(
                        AccountingCode.code.like("122%"),
                        AccountingCode.code == "1220",
                        AccountingCode.name.ilike("%accumulated%depreciation%")
                    )
                ).first()

            if not accumulated_depreciation_account:
                # Create default accumulated depreciation account
                accumulated_depreciation_account = AccountingCode(
                    code="1220",
                    name="Accumulated Depreciation",
                    account_type="Asset",
                    category="Fixed Assets",
                    is_contra_account=True
                )
                self.db.add(accumulated_depreciation_account)
                self.db.flush()

            acc_dep_entry = JournalEntry(
                accounting_code_id=accumulated_depreciation_account.id,
                accounting_entry_id=entry.id,
                entry_type="credit",
                narration=f"Accumulated Depreciation: {asset.name}",
                date=date.today(),
                debit_amount=0,
                credit_amount=depreciation_amount,
                branch_id=asset.branch_id
            )
            self.db.add(acc_dep_entry)

            # Commit the accounting entries
            self.db.commit()

        except Exception as e:
            # Log the error and rollback only accounting entries
            print(f"Warning: Failed to create accounting entry for depreciation: {str(e)}")
            import traceback
            traceback.print_exc()
            self.db.rollback()
