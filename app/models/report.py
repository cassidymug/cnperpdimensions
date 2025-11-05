from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.base import BaseModel
import uuid
from datetime import datetime
from typing import Optional, Dict, Any


class Report(BaseModel):
    """Report model for generating and storing financial reports"""
    __tablename__ = "reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    report_type = Column(String(50), nullable=False)  # financial, sales, inventory, operational
    category = Column(String(100), nullable=False)  # balance_sheet, income_statement, cash_flow, etc.
    description = Column(Text)
    
    # Report configuration
    parameters = Column(JSON)  # Report parameters (date ranges, filters, etc.)
    template = Column(String(100))  # Report template name
    format = Column(String(20), default="pdf")  # pdf, excel, csv, html
    
    # IFRS Compliance
    ifrs_compliant = Column(Boolean, default=True)
    reporting_period = Column(String(20))  # monthly, quarterly, yearly
    currency = Column(String(3), default="BWP")
    exchange_rate = Column(Float, default=1.0)
    
    # Generation status
    status = Column(String(20), default="draft")  # draft, generated, archived
    generated_at = Column(DateTime)
    generated_by = Column(String(36), ForeignKey("users.id"))
    
    # File storage
    file_path = Column(String(500))
    file_size = Column(Integer)
    checksum = Column(String(64))
    
    # Metadata
    version = Column(String(20), default="1.0")
    notes = Column(Text)
    
    # Relationships
    generated_by_user = relationship("User", back_populates="generated_reports")
    report_schedules = relationship("ReportSchedule", back_populates="report")


class ReportSchedule(BaseModel):
    """Model for scheduling automated report generation"""
    __tablename__ = "report_schedules"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False)
    name = Column(String(255), nullable=False)
    
    # Schedule configuration
    frequency = Column(String(20), nullable=False)  # daily, weekly, monthly, quarterly, yearly
    day_of_week = Column(Integer)  # 0=Monday, 6=Sunday
    day_of_month = Column(Integer)  # 1-31
    month = Column(Integer)  # 1-12
    time = Column(String(5))  # HH:MM format
    
    # Recipients
    recipients = Column(JSON)  # List of email addresses
    delivery_method = Column(String(20), default="email")  # email, file, api
    
    # Status
    active = Column(Boolean, default=True)
    last_run = Column(DateTime)
    next_run = Column(DateTime)
    
    # Relationships
    report = relationship("Report", back_populates="report_schedules")


class ReportTemplate(BaseModel):
    """Model for report templates"""
    __tablename__ = "report_templates"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    
    # Template configuration
    template_type = Column(String(50))  # html, pdf, excel
    template_data = Column(JSON)  # Template configuration
    css_styles = Column(Text)
    header_template = Column(Text)
    footer_template = Column(Text)
    
    # IFRS Compliance
    ifrs_compliant = Column(Boolean, default=True)
    required_sections = Column(JSON)  # Required sections for IFRS compliance
    
    # Metadata
    version = Column(String(20), default="1.0")
    description = Column(Text)
    is_default = Column(Boolean, default=False)


class FinancialReport(BaseModel):
    """Model for IFRS-compliant financial reports"""
    __tablename__ = "financial_reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_type = Column(String(50), nullable=False)  # balance_sheet, income_statement, cash_flow, trial_balance
    reporting_date = Column(DateTime, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # IFRS Compliance
    ifrs_version = Column(String(20), default="IFRS 9")
    presentation_currency = Column(String(3), default="BWP")
    functional_currency = Column(String(3), default="BWP")
    exchange_rate_date = Column(DateTime)
    exchange_rate = Column(Float, default=1.0)
    
    # Report data
    report_data = Column(JSON)  # Structured report data
    calculations = Column(JSON)  # Calculation details
    notes = Column(JSON)  # Financial statement notes
    
    # Audit trail
    prepared_by = Column(String(36), ForeignKey("users.id"))
    reviewed_by = Column(String(36), ForeignKey("users.id"))
    approved_by = Column(String(36), ForeignKey("users.id"))
    prepared_at = Column(DateTime, default=func.now())
    reviewed_at = Column(DateTime)
    approved_at = Column(DateTime)
    
    # Status
    status = Column(String(20), default="draft")  # draft, prepared, reviewed, approved, published
    
    # Relationships
    prepared_by_user = relationship("User", foreign_keys=[prepared_by])
    reviewed_by_user = relationship("User", foreign_keys=[reviewed_by])
    approved_by_user = relationship("User", foreign_keys=[approved_by])


class SalesReport(BaseModel):
    """Model for sales and revenue reports"""
    __tablename__ = "sales_reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_type = Column(String(50), nullable=False)  # daily, weekly, monthly, customer, product
    reporting_date = Column(DateTime, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Sales data
    total_sales = Column(Float, default=0.0)
    total_quantity = Column(Integer, default=0)
    total_transactions = Column(Integer, default=0)
    average_order_value = Column(Float, default=0.0)
    
    # Revenue breakdown
    cash_sales = Column(Float, default=0.0)
    credit_sales = Column(Float, default=0.0)
    online_sales = Column(Float, default=0.0)
    
    # Customer metrics
    new_customers = Column(Integer, default=0)
    returning_customers = Column(Integer, default=0)
    customer_retention_rate = Column(Float, default=0.0)
    
    # Product metrics
    top_products = Column(JSON)
    low_performing_products = Column(JSON)
    
    # Report data
    report_data = Column(JSON)
    charts_data = Column(JSON)
    
    # Status
    status = Column(String(20), default="generated")


class InventoryReport(BaseModel):
    """Model for inventory and stock reports"""
    __tablename__ = "inventory_reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_type = Column(String(50), nullable=False)  # stock_levels, movement, valuation, aging
    reporting_date = Column(DateTime, nullable=False)
    
    # Inventory metrics
    total_products = Column(Integer, default=0)
    total_value = Column(Float, default=0.0)
    low_stock_items = Column(Integer, default=0)
    out_of_stock_items = Column(Integer, default=0)
    overstocked_items = Column(Integer, default=0)
    
    # Movement data
    items_received = Column(Integer, default=0)
    items_sold = Column(Integer, default=0)
    items_adjusted = Column(Integer, default=0)
    
    # Valuation
    fifo_value = Column(Float, default=0.0)
    lifo_value = Column(Float, default=0.0)
    average_cost_value = Column(Float, default=0.0)
    
    # Aging analysis
    aging_data = Column(JSON)
    
    # Report data
    report_data = Column(JSON)
    charts_data = Column(JSON)
    
    # Status
    status = Column(String(20), default="generated")


class OperationalReport(BaseModel):
    """Model for operational and KPI reports"""
    __tablename__ = "operational_reports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_type = Column(String(50), nullable=False)  # performance, kpi, analytics
    reporting_date = Column(DateTime, nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    # Performance metrics
    revenue_growth = Column(Float, default=0.0)
    profit_margin = Column(Float, default=0.0)
    customer_satisfaction = Column(Float, default=0.0)
    employee_productivity = Column(Float, default=0.0)
    
    # KPI data
    kpi_data = Column(JSON)
    benchmark_data = Column(JSON)
    
    # Analytics
    trend_analysis = Column(JSON)
    forecast_data = Column(JSON)
    
    # Report data
    report_data = Column(JSON)
    charts_data = Column(JSON)
    
    # Status
    status = Column(String(20), default="generated")


class ReportExport(BaseModel):
    """Model for tracking report exports"""
    __tablename__ = "report_exports"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String(36), ForeignKey("reports.id"), nullable=False)
    export_type = Column(String(20), nullable=False)  # pdf, excel, csv, html
    file_path = Column(String(500))
    file_size = Column(Integer)
    checksum = Column(String(64))
    
    # Export metadata
    exported_at = Column(DateTime, default=func.now())
    exported_by = Column(String(36), ForeignKey("users.id"))
    download_count = Column(Integer, default=0)
    last_downloaded = Column(DateTime)
    
    # Status
    status = Column(String(20), default="completed")  # processing, completed, failed
    
    # Relationships
    report = relationship("Report")
    exported_by_user = relationship("User") 