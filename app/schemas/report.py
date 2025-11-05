from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, date
from enum import Enum


class ReportType(str, Enum):
    """Report type enumeration"""
    FINANCIAL = "financial"
    SALES = "sales"
    INVENTORY = "inventory"
    OPERATIONAL = "operational"


class ReportCategory(str, Enum):
    """Report category enumeration"""
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW = "cash_flow"
    TRIAL_BALANCE = "trial_balance"
    SALES_ANALYSIS = "sales_analysis"
    CUSTOMER_REPORT = "customer_report"
    INVENTORY_VALUATION = "inventory_valuation"
    STOCK_MOVEMENT = "stock_movement"
    PERFORMANCE_KPI = "performance_kpi"
    ANALYTICS = "analytics"


class ReportStatus(str, Enum):
    """Report status enumeration"""
    DRAFT = "draft"
    GENERATED = "generated"
    ARCHIVED = "archived"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportFormat(str, Enum):
    """Report format enumeration"""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    HTML = "html"


# Base Report Schemas
class ReportBase(BaseModel):
    """Base report schema"""
    name: str = Field(..., description="Report name")
    report_type: ReportType = Field(..., description="Type of report")
    category: ReportCategory = Field(..., description="Report category")
    description: Optional[str] = Field(None, description="Report description")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Report parameters")
    template: Optional[str] = Field(None, description="Report template name")
    format: ReportFormat = Field(ReportFormat.PDF, description="Report format")
    ifrs_compliant: bool = Field(True, description="IFRS compliance flag")
    reporting_period: Optional[str] = Field(None, description="Reporting period")
    currency: str = Field("BWP", description="Report currency")
    exchange_rate: float = Field(1.0, description="Exchange rate")
    notes: Optional[str] = Field(None, description="Report notes")


class ReportCreate(ReportBase):
    """Schema for creating a new report"""
    pass


class ReportUpdate(BaseModel):
    """Schema for updating a report"""
    name: Optional[str] = None
    description: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    template: Optional[str] = None
    format: Optional[ReportFormat] = None
    ifrs_compliant: Optional[bool] = None
    reporting_period: Optional[str] = None
    currency: Optional[str] = None
    exchange_rate: Optional[float] = None
    notes: Optional[str] = None


class ReportResponse(ReportBase):
    """Schema for report response"""
    id: str
    status: ReportStatus
    generated_at: Optional[datetime] = None
    generated_by: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    version: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Financial Report Schemas
class FinancialReportType(str, Enum):
    """Financial report type enumeration"""
    BALANCE_SHEET = "balance_sheet"
    INCOME_STATEMENT = "income_statement"
    CASH_FLOW = "cash_flow"
    TRIAL_BALANCE = "trial_balance"
    STATEMENT_OF_CHANGES_IN_EQUITY = "statement_of_changes_in_equity"
    NOTES_TO_FINANCIAL_STATEMENTS = "notes_to_financial_statements"


class FinancialReportStatus(str, Enum):
    """Financial report status enumeration"""
    DRAFT = "draft"
    PREPARED = "prepared"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    PUBLISHED = "published"


class FinancialReportBase(BaseModel):
    """Base financial report schema"""
    report_type: FinancialReportType = Field(..., description="Financial report type")
    reporting_date: datetime = Field(..., description="Reporting date")
    period_start: datetime = Field(..., description="Period start date")
    period_end: datetime = Field(..., description="Period end date")
    ifrs_version: str = Field("IFRS 9", description="IFRS version")
    presentation_currency: str = Field("BWP", description="Presentation currency")
    functional_currency: str = Field("BWP", description="Functional currency")
    exchange_rate_date: Optional[datetime] = Field(None, description="Exchange rate date")
    exchange_rate: float = Field(1.0, description="Exchange rate")
    report_data: Optional[Dict[str, Any]] = Field(None, description="Report data")
    calculations: Optional[Dict[str, Any]] = Field(None, description="Calculation details")
    notes: Optional[Dict[str, Any]] = Field(None, description="Financial statement notes")


class FinancialReportCreate(FinancialReportBase):
    """Schema for creating a financial report"""
    pass


class FinancialReportUpdate(BaseModel):
    """Schema for updating a financial report"""
    report_type: Optional[FinancialReportType] = None
    reporting_date: Optional[datetime] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    ifrs_version: Optional[str] = None
    presentation_currency: Optional[str] = None
    functional_currency: Optional[str] = None
    exchange_rate_date: Optional[datetime] = None
    exchange_rate: Optional[float] = None
    report_data: Optional[Dict[str, Any]] = None
    calculations: Optional[Dict[str, Any]] = None
    notes: Optional[Dict[str, Any]] = None
    status: Optional[FinancialReportStatus] = None


class FinancialReportResponse(FinancialReportBase):
    """Schema for financial report response"""
    id: str
    status: FinancialReportStatus
    prepared_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    approved_by: Optional[str] = None
    prepared_at: datetime
    reviewed_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Sales Report Schemas
class SalesReportType(str, Enum):
    """Sales report type enumeration"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOMER = "customer"
    PRODUCT = "product"
    REVENUE = "revenue"
    TREND = "trend"


class SalesReportBase(BaseModel):
    """Base sales report schema"""
    report_type: SalesReportType = Field(..., description="Sales report type")
    reporting_date: datetime = Field(..., description="Reporting date")
    period_start: datetime = Field(..., description="Period start date")
    period_end: datetime = Field(..., description="Period end date")
    total_sales: float = Field(0.0, description="Total sales amount")
    total_quantity: int = Field(0, description="Total quantity sold")
    total_transactions: int = Field(0, description="Total number of transactions")
    average_order_value: float = Field(0.0, description="Average order value")
    cash_sales: float = Field(0.0, description="Cash sales amount")
    credit_sales: float = Field(0.0, description="Credit sales amount")
    online_sales: float = Field(0.0, description="Online sales amount")
    new_customers: int = Field(0, description="Number of new customers")
    returning_customers: int = Field(0, description="Number of returning customers")
    customer_retention_rate: float = Field(0.0, description="Customer retention rate")
    top_products: Optional[Dict[str, Any]] = Field(None, description="Top performing products")
    low_performing_products: Optional[Dict[str, Any]] = Field(None, description="Low performing products")
    report_data: Optional[Dict[str, Any]] = Field(None, description="Report data")
    charts_data: Optional[Dict[str, Any]] = Field(None, description="Charts data")


class SalesReportCreate(SalesReportBase):
    """Schema for creating a sales report"""
    pass


class SalesReportResponse(SalesReportBase):
    """Schema for sales report response"""
    id: str
    status: ReportStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Inventory Report Schemas
class InventoryReportType(str, Enum):
    """Inventory report type enumeration"""
    STOCK_LEVELS = "stock_levels"
    MOVEMENT = "movement"
    VALUATION = "valuation"
    AGING = "aging"
    ABC_ANALYSIS = "abc_analysis"
    TURNOVER = "turnover"


class InventoryReportBase(BaseModel):
    """Base inventory report schema"""
    report_type: InventoryReportType = Field(..., description="Inventory report type")
    reporting_date: datetime = Field(..., description="Reporting date")
    total_products: int = Field(0, description="Total number of products")
    total_value: float = Field(0.0, description="Total inventory value")
    low_stock_items: int = Field(0, description="Number of low stock items")
    out_of_stock_items: int = Field(0, description="Number of out of stock items")
    overstocked_items: int = Field(0, description="Number of overstocked items")
    items_received: int = Field(0, description="Number of items received")
    items_sold: int = Field(0, description="Number of items sold")
    items_adjusted: int = Field(0, description="Number of items adjusted")
    fifo_value: float = Field(0.0, description="FIFO valuation")
    lifo_value: float = Field(0.0, description="LIFO valuation")
    average_cost_value: float = Field(0.0, description="Average cost valuation")
    aging_data: Optional[Dict[str, Any]] = Field(None, description="Aging analysis data")
    report_data: Optional[Dict[str, Any]] = Field(None, description="Report data")
    charts_data: Optional[Dict[str, Any]] = Field(None, description="Charts data")


class InventoryReportCreate(InventoryReportBase):
    """Schema for creating an inventory report"""
    pass


class InventoryReportResponse(InventoryReportBase):
    """Schema for inventory report response"""
    id: str
    status: ReportStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Operational Report Schemas
class OperationalReportType(str, Enum):
    """Operational report type enumeration"""
    PERFORMANCE = "performance"
    KPI = "kpi"
    ANALYTICS = "analytics"
    BENCHMARK = "benchmark"
    FORECAST = "forecast"


class OperationalReportBase(BaseModel):
    """Base operational report schema"""
    report_type: OperationalReportType = Field(..., description="Operational report type")
    reporting_date: datetime = Field(..., description="Reporting date")
    period_start: datetime = Field(..., description="Period start date")
    period_end: datetime = Field(..., description="Period end date")
    revenue_growth: float = Field(0.0, description="Revenue growth percentage")
    profit_margin: float = Field(0.0, description="Profit margin percentage")
    customer_satisfaction: float = Field(0.0, description="Customer satisfaction score")
    employee_productivity: float = Field(0.0, description="Employee productivity score")
    kpi_data: Optional[Dict[str, Any]] = Field(None, description="KPI data")
    benchmark_data: Optional[Dict[str, Any]] = Field(None, description="Benchmark data")
    trend_analysis: Optional[Dict[str, Any]] = Field(None, description="Trend analysis")
    forecast_data: Optional[Dict[str, Any]] = Field(None, description="Forecast data")
    report_data: Optional[Dict[str, Any]] = Field(None, description="Report data")
    charts_data: Optional[Dict[str, Any]] = Field(None, description="Charts data")


class OperationalReportCreate(OperationalReportBase):
    """Schema for creating an operational report"""
    pass


class OperationalReportResponse(OperationalReportBase):
    """Schema for operational report response"""
    id: str
    status: ReportStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# Report Schedule Schemas
class ScheduleFrequency(str, Enum):
    """Schedule frequency enumeration"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ReportScheduleBase(BaseModel):
    """Base report schedule schema"""
    report_id: str = Field(..., description="Report ID")
    name: str = Field(..., description="Schedule name")
    frequency: ScheduleFrequency = Field(..., description="Schedule frequency")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="Day of week (0=Monday, 6=Sunday)")
    day_of_month: Optional[int] = Field(None, ge=1, le=31, description="Day of month")
    month: Optional[int] = Field(None, ge=1, le=12, description="Month")
    time: str = Field(..., description="Time in HH:MM format")
    recipients: Optional[List[str]] = Field(None, description="List of email recipients")
    delivery_method: str = Field("email", description="Delivery method")


class ReportScheduleCreate(ReportScheduleBase):
    """Schema for creating a report schedule"""
    pass


class ReportScheduleUpdate(BaseModel):
    """Schema for updating a report schedule"""
    name: Optional[str] = None
    frequency: Optional[ScheduleFrequency] = None
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    month: Optional[int] = None
    time: Optional[str] = None
    recipients: Optional[List[str]] = None
    delivery_method: Optional[str] = None
    active: Optional[bool] = None


# IFRS Compliance Schemas
class IFRSComplianceStatus(BaseModel):
    """IFRS compliance status schema"""
    report_id: str
    report_name: str
    ifrs_compliant: bool
    compliance_score: float
    missing_requirements: List[str]
    recommendations: List[str]
    last_validated: datetime


class IFRSValidationResult(BaseModel):
    """IFRS validation result schema"""
    is_compliant: bool
    compliance_score: float
    missing_requirements: List[str]
    recommendations: List[str]
    validation_date: datetime
    validator: str


# Analytics Schemas
class ReportAnalytics(BaseModel):
    """Report analytics schema"""
    total_reports: int
    reports_by_type: Dict[str, int]
    reports_by_status: Dict[str, int]
    average_generation_time: float
    most_used_templates: List[Dict[str, Any]]
    ifrs_compliance_rate: float
    period_start: date
    period_end: date


class ReportTrends(BaseModel):
    """Report trends schema"""
    period: str
    report_type: Optional[str]
    trends_data: List[Dict[str, Any]]
    growth_rate: float
    peak_periods: List[Dict[str, Any]]
    seasonal_patterns: Dict[str, Any] 