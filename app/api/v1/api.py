from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, users, branches, accounting, inventory, sales,
    purchases, banking, billing, vat, pos, notifications, app_setting, reports, branch_stock, invoices, documents, asset_management, budgeting, backup, roles, receipts, general_ledger, credit_notes, invoice_designer, printer_settings, inventory_allocation, cogs, manufacturing, quotations, job_cards, excel_templates, unit_of_measure, business_intelligence, weight_products, system_health, branch_sales_realtime, workflows, logging_viewer,
    # ifrs_accounting temporarily disabled due to syntax errors
)
from app.api.v1.endpoints import procurement as procurement_endpoints
from app.api.accounting_codes import router as accounting_codes_router

api_router = APIRouter()


# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(roles.router, prefix="/roles", tags=["Roles & Permissions"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflows"])
api_router.include_router(branches.router, prefix="/branches", tags=["Branches"])
api_router.include_router(accounting.router, prefix="/accounting", tags=["Accounting"])
api_router.include_router(general_ledger.router, prefix="/general-ledger", tags=["General Ledger"])
# api_router.include_router(ifrs_accounting.router, prefix="/ifrs-accounting", tags=["IFRS Accounting"])  # Temporarily disabled
api_router.include_router(accounting_codes_router, prefix="/accounting-codes", tags=["Accounting Codes"])
# Legacy underscore variant (some pages may still request /accounting_codes)
api_router.include_router(accounting_codes_router, prefix="/accounting_codes", tags=["Accounting Codes (legacy)"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"])
api_router.include_router(sales.router, prefix="/sales", tags=["Sales"])
api_router.include_router(purchases.router, prefix="/purchases", tags=["Purchases"])
api_router.include_router(banking.router, prefix="/banking", tags=["Banking"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
api_router.include_router(vat.router, prefix="/vat", tags=["VAT"])
api_router.include_router(pos.router, prefix="/pos", tags=["POS"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(app_setting.router, prefix="/settings", tags=["App Settings"])
# Backwards compatibility aliases (older frontend expected /app-setting/ and /app-settings/)
api_router.include_router(app_setting.router, prefix="/app-setting", tags=["App Settings (legacy)"])
api_router.include_router(app_setting.router, prefix="/app-settings", tags=["App Settings (legacy)"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(branch_stock.router, prefix="/branch-stock", tags=["Branch Stock Management"])
api_router.include_router(inventory_allocation.router, prefix="/inventory-allocation", tags=["Inventory Allocation"])
api_router.include_router(invoices.router, prefix="/invoices", tags=["Invoices"])
api_router.include_router(documents.router, prefix="/documents", tags=["Document Printing"])
api_router.include_router(asset_management.router, prefix="/asset-management", tags=["Asset Management"])
api_router.include_router(procurement_endpoints.router, prefix="/procurement", tags=["Procurement"])
api_router.include_router(budgeting.router, prefix="/budgeting", tags=["Budgeting"])
api_router.include_router(backup.router, prefix="/backup", tags=["Backup Management"])
api_router.include_router(receipts.router, prefix="/receipts", tags=["Receipts"])
api_router.include_router(credit_notes.router, prefix="/credit-notes", tags=["Credit Notes"])
api_router.include_router(invoice_designer.router, prefix="/invoice-designer", tags=["Invoice Designer"])
api_router.include_router(printer_settings.router, prefix="/settings", tags=["Printer Settings"])
api_router.include_router(excel_templates.router, prefix="/excel-templates", tags=["Excel Templates"])
api_router.include_router(cogs.router, prefix="/cogs", tags=["Cost of Goods Sold"])
api_router.include_router(manufacturing.router, prefix="/manufacturing", tags=["Manufacturing Costs"])
api_router.include_router(quotations.router, prefix="/quotations", tags=["Quotations"])
api_router.include_router(job_cards.router, prefix="/job-cards", tags=["Job Cards"])
api_router.include_router(unit_of_measure.router, prefix="/unit-of-measure", tags=["Units of Measure"])
api_router.include_router(unit_of_measure.router, prefix="/uom", tags=["Units of Measure (short)"])
api_router.include_router(business_intelligence.router, prefix="/bi", tags=["Business Intelligence"])
api_router.include_router(system_health.router, prefix="/system-health", tags=["System Health & Error Management"])
api_router.include_router(logging_viewer.router, prefix="/logs", tags=["Log Viewer & Monitoring"])
api_router.include_router(branch_sales_realtime.router, tags=["Branch Sales Realtime"])
