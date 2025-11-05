from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class ValidationLevel(str, Enum):
    """Validation levels for accounting entries"""
    BASIC = "basic"
    IFRS = "ifrs"
    COMPLETE = "complete"


class IFRSAccountType(str, Enum):
    """IFRS Account Types"""
    ASSET = "Asset"
    LIABILITY = "Liability"
    EQUITY = "Equity"
    REVENUE = "Revenue"
    EXPENSE = "Expense"


class JournalEntryCreate(BaseModel):
    """Schema for creating a journal entry"""
    accounting_code_id: str = Field(..., description="Accounting code ID")
    entry_type: str = Field(..., description="Entry type (debit/credit)")
    amount: Decimal = Field(..., description="Amount")
    description: Optional[str] = Field(None, description="Description")
    
    @field_validator('entry_type')
    @classmethod
    def validate_entry_type(cls, v):
        if v not in ['debit', 'credit']:
            raise ValueError('Entry type must be "debit" or "credit"')
        return v
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v):
        if v <= 0:
            raise ValueError('Amount must be greater than zero')
        return v


class AccountingEntryCreate(BaseModel):
    """Schema for creating an IFRS-compliant accounting entry"""
    date_prepared: Optional[date] = Field(None, description="Date prepared")
    date_posted: Optional[date] = Field(None, description="Date posted")
    particulars: str = Field(..., description="Entry particulars")
    book: Optional[str] = Field(None, description="Book name")
    entries: List[JournalEntryCreate] = Field(..., description="Journal entries")
    
    @field_validator('entries')
    @classmethod
    def validate_entries(cls, v):
        if not v:
            raise ValueError('At least one journal entry is required')
        return v


class ValidationResult(BaseModel):
    """Schema for validation results"""
    is_valid: bool = Field(..., description="Whether the validation passed")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    details: Dict[str, Any] = Field(default_factory=dict, description="Validation details")


class IFRSBalanceSheet(BaseModel):
    """Schema for IFRS balance sheet"""
    as_of_date: date = Field(..., description="Balance sheet date")
    assets: Dict[str, float] = Field(..., description="Asset balances")
    liabilities: Dict[str, float] = Field(..., description="Liability balances")
    equity: Dict[str, float] = Field(..., description="Equity balances")
    totals: Dict[str, float] = Field(..., description="Total balances")


class IFRSIncomeStatement(BaseModel):
    """Schema for IFRS income statement"""
    period: Dict[str, date] = Field(..., description="Reporting period")
    revenue: Dict[str, float] = Field(..., description="Revenue items")
    expenses: Dict[str, float] = Field(..., description="Expense items")
    totals: Dict[str, float] = Field(..., description="Total amounts")


class AccountBalanceValidation(BaseModel):
    """Schema for account balance validation"""
    account_code: str = Field(..., description="Account code")
    account_name: str = Field(..., description="Account name")
    is_valid: bool = Field(..., description="Whether the balance is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    details: Dict[str, Any] = Field(default_factory=dict, description="Balance details")


class TrialBalanceValidation(BaseModel):
    """Schema for trial balance validation"""
    as_of_date: date = Field(..., description="Trial balance date")
    is_valid: bool = Field(..., description="Whether the trial balance is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    details: Dict[str, Any] = Field(default_factory=dict, description="Trial balance details")


class IFRSReportingValidation(BaseModel):
    """Schema for IFRS reporting validation"""
    as_of_date: date = Field(..., description="Validation date")
    is_valid: bool = Field(..., description="Whether IFRS reporting is compliant")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    details: Dict[str, Any] = Field(default_factory=dict, description="IFRS reporting details")


class ValidationSummary(BaseModel):
    """Schema for validation summary"""
    period: Dict[str, date] = Field(..., description="Validation period")
    total_entries: int = Field(..., description="Total entries validated")
    valid_entries: int = Field(..., description="Valid entries count")
    invalid_entries: int = Field(..., description="Invalid entries count")
    total_errors: int = Field(..., description="Total errors found")
    total_warnings: int = Field(..., description="Total warnings found")
    common_errors: List[tuple] = Field(default_factory=list, description="Common errors")
    validation_details: Dict[str, Any] = Field(default_factory=dict, description="Validation details")


class AutoCreateEntryRequest(BaseModel):
    """Schema for automatic entry creation request"""
    transaction_type: str = Field(..., description="Transaction type (sale/purchase/bank_transaction)")
    transaction_id: str = Field(..., description="Transaction ID")
    
    @field_validator('transaction_type')
    @classmethod
    def validate_transaction_type(cls, v):
        valid_types = ['sale', 'purchase', 'bank_transaction']
        if v not in valid_types:
            raise ValueError(f'Transaction type must be one of: {", ".join(valid_types)}')
        return v


class AutoCreateEntryResponse(BaseModel):
    """Schema for automatic entry creation response"""
    success: bool = Field(..., description="Whether creation was successful")
    transaction_type: str = Field(..., description="Transaction type")
    transaction_id: str = Field(..., description="Transaction ID")
    journal_entries_count: int = Field(..., description="Number of journal entries created")
    total_debits: float = Field(..., description="Total debits")
    total_credits: float = Field(..., description="Total credits")


class IFRSComplianceCheck(BaseModel):
    """Schema for IFRS compliance check"""
    entry_id: Optional[str] = Field(None, description="Accounting entry ID")
    is_compliant: bool = Field(..., description="Whether the entry is IFRS compliant")
    double_entry_balanced: bool = Field(..., description="Whether debits equal credits")
    ifrs_compliant: bool = Field(..., description="Whether IFRS requirements are met")
    total_debits: float = Field(..., description="Total debits")
    total_credits: float = Field(..., description="Total credits")
    compliance_issues: List[str] = Field(default_factory=list, description="Compliance issues")


class IFRSAccountRules(BaseModel):
    """Schema for IFRS account rules"""
    account_type: IFRSAccountType = Field(..., description="Account type")
    normal_balance: str = Field(..., description="Normal balance (debit/credit)")
    increase_with: str = Field(..., description="Increase with (debit/credit)")
    decrease_with: str = Field(..., description="Decrease with (debit/credit)")
    balance_sheet: bool = Field(..., description="Appears on balance sheet")
    income_statement: bool = Field(..., description="Appears on income statement")


class IFRSReportingCategory(BaseModel):
    """Schema for IFRS reporting category"""
    code: str = Field(..., description="Category code")
    name: str = Field(..., description="Category name")
    description: Optional[str] = Field(None, description="Category description")


class IFRSComplianceReport(BaseModel):
    """Schema for comprehensive IFRS compliance report"""
    report_date: datetime = Field(..., description="Report generation date")
    branch_id: str = Field(..., description="Branch ID")
    period_start: date = Field(..., description="Period start date")
    period_end: date = Field(..., description="Period end date")
    
    # Validation results
    trial_balance_valid: bool = Field(..., description="Trial balance validation")
    ifrs_reporting_valid: bool = Field(..., description="IFRS reporting validation")
    account_balances_valid: bool = Field(..., description="Account balances validation")
    
    # Statistics
    total_entries: int = Field(..., description="Total accounting entries")
    compliant_entries: int = Field(..., description="IFRS compliant entries")
    non_compliant_entries: int = Field(..., description="Non-compliant entries")
    
    # Issues
    errors: List[str] = Field(default_factory=list, description="Compliance errors")
    warnings: List[str] = Field(default_factory=list, description="Compliance warnings")
    
    # Details
    balance_sheet_data: Optional[IFRSBalanceSheet] = Field(None, description="Balance sheet data")
    income_statement_data: Optional[IFRSIncomeStatement] = Field(None, description="Income statement data")
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list, description="Compliance recommendations")


class IFRSComplianceSettings(BaseModel):
    """Schema for IFRS compliance settings"""
    enforce_double_entry: bool = Field(True, description="Enforce double-entry principle")
    require_ifrs_tags: bool = Field(True, description="Require IFRS reporting tags")
    validate_account_types: bool = Field(True, description="Validate account types")
    auto_create_entries: bool = Field(True, description="Auto-create entries for transactions")
    validate_balances: bool = Field(True, description="Validate account balances")
    check_trial_balance: bool = Field(True, description="Check trial balance")
    
    # IFRS specific settings
    required_ifrs_categories: List[str] = Field(default_factory=list, description="Required IFRS categories")
    allowed_account_types: List[str] = Field(default_factory=list, description="Allowed account types")
    validation_level: ValidationLevel = Field(ValidationLevel.COMPLETE, description="Validation level")


class IFRSComplianceMetrics(BaseModel):
    """Schema for IFRS compliance metrics"""
    compliance_rate: float = Field(..., description="Overall compliance rate (0-100)")
    double_entry_compliance: float = Field(..., description="Double-entry compliance rate")
    ifrs_tagging_compliance: float = Field(..., description="IFRS tagging compliance rate")
    account_type_compliance: float = Field(..., description="Account type compliance rate")
    balance_validation_compliance: float = Field(..., description="Balance validation compliance rate")
    
    # Trend data
    daily_compliance: List[Dict[str, Any]] = Field(default_factory=list, description="Daily compliance data")
    weekly_compliance: List[Dict[str, Any]] = Field(default_factory=list, description="Weekly compliance data")
    monthly_compliance: List[Dict[str, Any]] = Field(default_factory=list, description="Monthly compliance data")
    
    # Top issues
    top_errors: List[Dict[str, Any]] = Field(default_factory=list, description="Most common errors")
    top_warnings: List[Dict[str, Any]] = Field(default_factory=list, description="Most common warnings")


class IFRSComplianceDashboard(BaseModel):
    """Schema for IFRS compliance dashboard"""
    summary: IFRSComplianceMetrics = Field(..., description="Compliance metrics")
    recent_entries: List[Dict[str, Any]] = Field(default_factory=list, description="Recent accounting entries")
    validation_results: List[Dict[str, Any]] = Field(default_factory=list, description="Recent validation results")
    compliance_alerts: List[Dict[str, Any]] = Field(default_factory=list, description="Compliance alerts")
    recommendations: List[str] = Field(default_factory=list, description="Compliance recommendations") 