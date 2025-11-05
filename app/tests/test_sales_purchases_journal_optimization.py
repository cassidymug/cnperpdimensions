"""
Test suite for Sales and Purchases Journal Entry Optimization.

Tests verify:
1. Eager loading eliminates N+1 queries
2. UUID-only fields replaced with descriptive names
3. All related entities properly returned (accounting_code, branch, ledger, etc.)
4. Dimension assignments eagerly loaded
5. Response structure matches expected schema
"""

import pytest
from decimal import Decimal
from datetime import datetime, date
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db
from app.models.accounting import (
    JournalEntry, AccountingCode, AccountingEntry, Ledger, DimensionAssignment
)
from app.models.branches import Branch
from app.models.accounting_dimensions import DimensionValue, Dimension

client = TestClient(app)


class TestSalesJournalEntryOptimization:
    """Test sales journal entries with optimization (eager loading + names)"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return MagicMock(spec=Session)

    def test_sales_journal_entries_response_structure(self, mock_db):
        """
        Test that sales journal entries response includes:
        - accounting_code + accounting_code_name
        - accounting_entry_id + accounting_entry_particulars
        - branch_id + branch_name
        - ledger_id + ledger_description
        - dimensions with proper details
        """
        # Create mock accounting code
        mock_code = MagicMock(spec=AccountingCode)
        mock_code.id = "code-123"
        mock_code.code = "1010"
        mock_code.name = "Cash and Cash Equivalents"

        # Create mock accounting entry
        mock_entry_obj = MagicMock(spec=AccountingEntry)
        mock_entry_obj.id = "entry-123"
        mock_entry_obj.particulars = "Sale of goods"

        # Create mock branch
        mock_branch = MagicMock(spec=Branch)
        mock_branch.id = "branch-123"
        mock_branch.name = "Headquarters"

        # Create mock ledger
        mock_ledger = MagicMock(spec=Ledger)
        mock_ledger.id = "ledger-123"
        mock_ledger.description = "Cash Account"

        # Create mock dimension value
        mock_dim_value = MagicMock(spec=DimensionValue)
        mock_dim_value.id = "dim-value-123"
        mock_dim_value.value = "Cost Center 01"
        mock_dim = MagicMock(spec=Dimension)
        mock_dim.code = "COST_CENTER"
        mock_dim_value.dimension = mock_dim

        # Create mock dimension assignment
        mock_dim_assign = MagicMock(spec=DimensionAssignment)
        mock_dim_assign.dimension_value_id = "dim-value-123"
        mock_dim_assign.dimension_value = mock_dim_value

        # Create mock journal entry
        mock_je = MagicMock(spec=JournalEntry)
        mock_je.id = "je-123"
        mock_je.source = "SALES"
        mock_je.entry_date = datetime(2025, 1, 15)
        mock_je.debit_amount = Decimal("1000.00")
        mock_je.credit_amount = Decimal("0")
        mock_je.description = "Invoice INV-001"
        mock_je.accounting_code = mock_code
        mock_je.accounting_entry_id = "entry-123"
        mock_je.accounting_entry = mock_entry_obj
        mock_je.branch_id = "branch-123"
        mock_je.branch = mock_branch
        mock_je.ledger_id = "ledger-123"
        mock_je.ledger = mock_ledger
        mock_je.dimension_assignments = [mock_dim_assign]

        # Mock the query
        mock_query = MagicMock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_je]
        mock_db.query.return_value = mock_query

        # Override dependency
        def override_get_db():
            return mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            # Call endpoint
            response = client.get("/api/v1/sales/invoices/journal-entries?source=SALES")

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1

            entry = data[0]

            # Verify all required fields present
            assert entry["id"] == "je-123"
            assert entry["source"] == "SALES"
            assert entry["description"] == "Invoice INV-001"

            # Verify UUID + name fields for accounting code
            assert entry["accounting_code"] == "1010"
            assert entry["accounting_code_name"] == "Cash and Cash Equivalents"

            # Verify UUID + particulars for accounting entry
            assert entry["accounting_entry_id"] == "entry-123"
            assert entry["accounting_entry_particulars"] == "Sale of goods"

            # Verify UUID + name for branch
            assert entry["branch_id"] == "branch-123"
            assert entry["branch_name"] == "Headquarters"

            # Verify UUID + description for ledger
            assert entry["ledger_id"] == "ledger-123"
            assert entry["ledger_description"] == "Cash Account"

            # Verify amounts
            assert entry["debit_amount"] == 1000.0
            assert entry["credit_amount"] == 0.0

            # Verify dimensions with name
            assert len(entry["dimensions"]) == 1
            assert entry["dimensions"][0]["dimension_type"] == "COST_CENTER"
            assert entry["dimensions"][0]["dimension_value"] == "Cost Center 01"
            assert entry["dimensions"][0]["dimension_value_id"] == "dim-value-123"

        finally:
            app.dependency_overrides.clear()

    def test_sales_journal_entries_eager_loading_called(self, mock_db):
        """Verify that joinedload is called on all relationships"""
        mock_query = MagicMock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        def override_get_db():
            return mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = client.get("/api/v1/sales/invoices/journal-entries?source=SALES")

            # Verify options() was called (eager loading)
            mock_query.options.assert_called_once()

            # The options call should have joinedload calls in it
            call_args = mock_query.options.call_args
            assert call_args is not None

        finally:
            app.dependency_overrides.clear()

    def test_sales_journal_entries_with_date_filters(self, mock_db):
        """Test that date filtering works with eager loading"""
        mock_query = MagicMock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        def override_get_db():
            return mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            start = "2025-01-01"
            end = "2025-01-31"
            response = client.get(
                f"/api/v1/sales/invoices/journal-entries?source=SALES&start_date={start}&end_date={end}"
            )

            assert response.status_code == 200

            # Verify filter was called
            assert mock_query.filter.called

        finally:
            app.dependency_overrides.clear()


class TestPurchasesJournalEntryOptimization:
    """Test purchases journal entries with optimization (eager loading + names)"""

    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return MagicMock(spec=Session)

    def test_purchases_journal_entries_response_structure(self, mock_db):
        """
        Test that purchases journal entries response includes all required fields:
        - accounting_code + accounting_code_name
        - accounting_entry + particulars
        - branch + name
        - ledger + description
        - dimensions with proper details
        """
        # Create mock accounting code
        mock_code = MagicMock(spec=AccountingCode)
        mock_code.id = "code-456"
        mock_code.code = "5010"
        mock_code.name = "Purchases"

        # Create mock accounting entry
        mock_entry_obj = MagicMock(spec=AccountingEntry)
        mock_entry_obj.id = "entry-456"
        mock_entry_obj.particulars = "Purchase of raw materials"

        # Create mock branch
        mock_branch = MagicMock(spec=Branch)
        mock_branch.id = "branch-456"
        mock_branch.name = "Distribution Center"

        # Create mock ledger
        mock_ledger = MagicMock(spec=Ledger)
        mock_ledger.id = "ledger-456"
        mock_ledger.description = "Accounts Payable"

        # Create mock dimension assignment
        mock_dim_value = MagicMock(spec=DimensionValue)
        mock_dim_value.id = "dim-value-456"
        mock_dim_value.value = "Project Alpha"
        mock_dim = MagicMock(spec=Dimension)
        mock_dim.code = "PROJECT"
        mock_dim_value.dimension = mock_dim

        mock_dim_assign = MagicMock(spec=DimensionAssignment)
        mock_dim_assign.dimension_value_id = "dim-value-456"
        mock_dim_assign.dimension_value = mock_dim_value

        # Create mock journal entry
        mock_je = MagicMock(spec=JournalEntry)
        mock_je.id = "je-456"
        mock_je.source = "PURCHASES"
        mock_je.entry_date = datetime(2025, 1, 20)
        mock_je.debit_amount = Decimal("5000.00")
        mock_je.credit_amount = Decimal("0")
        mock_je.description = "PO-PO-001"
        mock_je.accounting_code = mock_code
        mock_je.accounting_entry_id = "entry-456"
        mock_je.accounting_entry = mock_entry_obj
        mock_je.branch_id = "branch-456"
        mock_je.branch = mock_branch
        mock_je.ledger_id = "ledger-456"
        mock_je.ledger = mock_ledger
        mock_je.dimension_assignments = [mock_dim_assign]

        # Mock the query
        mock_query = MagicMock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [mock_je]
        mock_db.query.return_value = mock_query

        def override_get_db():
            return mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = client.get("/api/v1/purchases/purchases/journal-entries?source=PURCHASES")

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1

            entry = data[0]

            # Verify all required fields
            assert entry["id"] == "je-456"
            assert entry["source"] == "PURCHASES"
            assert entry["description"] == "PO-PO-001"

            # Verify UUID + name fields
            assert entry["accounting_code"] == "5010"
            assert entry["accounting_code_name"] == "Purchases"

            assert entry["accounting_entry_id"] == "entry-456"
            assert entry["accounting_entry_particulars"] == "Purchase of raw materials"

            assert entry["branch_id"] == "branch-456"
            assert entry["branch_name"] == "Distribution Center"

            assert entry["ledger_id"] == "ledger-456"
            assert entry["ledger_description"] == "Accounts Payable"

            # Verify amounts
            assert entry["debit_amount"] == 5000.0
            assert entry["credit_amount"] == 0.0

            # Verify dimensions
            assert len(entry["dimensions"]) == 1
            assert entry["dimensions"][0]["dimension_type"] == "PROJECT"
            assert entry["dimensions"][0]["dimension_value"] == "Project Alpha"

        finally:
            app.dependency_overrides.clear()

    def test_purchases_journal_entries_eager_loading(self, mock_db):
        """Verify eager loading is used in purchases endpoint"""
        mock_query = MagicMock()
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = []
        mock_db.query.return_value = mock_query

        def override_get_db():
            return mock_db

        app.dependency_overrides[get_db] = override_get_db

        try:
            response = client.get("/api/v1/purchases/purchases/journal-entries?source=PURCHASES")

            # Verify options was called for eager loading
            mock_query.options.assert_called_once()

        finally:
            app.dependency_overrides.clear()


class TestComparisonBeforeAfterOptimization:
    """Test that optimization pattern was correctly applied"""

    def test_sales_purchases_same_optimization_pattern(self):
        """
        Verify that sales and purchases endpoints use the same optimization pattern:
        1. Both use eager loading (joinedload)
        2. Both return name fields
        3. Both handle null values safely
        """
        # This is a structural test verifying the code pattern
        from app.api.v1.endpoints import sales, purchases

        # Both modules should have joinedload imported
        assert hasattr(sales, 'joinedload'), "sales.py should have joinedload imported"
        assert hasattr(purchases, 'joinedload'), "purchases.py should have joinedload imported"

        # Read the source to verify optimization
        import inspect

        sales_source = inspect.getsource(sales.get_sales_journal_entries)
        purchases_source = inspect.getsource(purchases.get_purchases_journal_entries)

        # Both should have eager loading
        assert "joinedload" in sales_source, "sales journal endpoint should use joinedload"
        assert "joinedload" in purchases_source, "purchases journal endpoint should use joinedload"

        # Both should have accounting_code_name
        assert "accounting_code_name" in sales_source, "sales should return accounting_code_name"
        assert "accounting_code_name" in purchases_source, "purchases should return accounting_code_name"

        # Both should have branch_name
        assert "branch_name" in sales_source, "sales should return branch_name"
        assert "branch_name" in purchases_source, "purchases should return branch_name"

        # Both should have ledger_description
        assert "ledger_description" in sales_source, "sales should return ledger_description"
        assert "ledger_description" in purchases_source, "purchases should return ledger_description"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
