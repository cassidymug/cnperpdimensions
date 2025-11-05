-- IFRS Compliant Database Views
-- These views provide IFRS-compliant financial reporting data

-- =============================================================================
-- View: IFRS Trial Balance View
-- Standard: IAS 1 - Presentation of Financial Statements
-- =============================================================================
CREATE OR REPLACE VIEW ifrs_trial_balance_view AS
SELECT 
    ac.id,
    ac.code,
    ac.name,
    ac.account_type,
    ac.ifrs_category,
    ac.reporting_tag,
    ac.parent_id,
    COALESCE(SUM(ae.debit_amount), 0) as total_debits,
    COALESCE(SUM(ae.credit_amount), 0) as total_credits,
    CASE 
        WHEN ac.account_type IN ('ASSET', 'EXPENSE') THEN 
            COALESCE(SUM(ae.debit_amount), 0) - COALESCE(SUM(ae.credit_amount), 0)
        ELSE 
            COALESCE(SUM(ae.credit_amount), 0) - COALESCE(SUM(ae.debit_amount), 0)
    END as balance,
    ac.created_at,
    ac.updated_at
FROM accounting_codes ac
LEFT JOIN accounting_entries ae ON ac.id = ae.accounting_code_id
LEFT JOIN journal_entries je ON ae.journal_entry_id = je.id
WHERE ac.is_active = true
GROUP BY ac.id, ac.code, ac.name, ac.account_type, ac.ifrs_category, 
         ac.reporting_tag, ac.parent_id, ac.created_at, ac.updated_at;

-- =============================================================================
-- View: IFRS Balance Sheet View  
-- Standard: IAS 1 - Presentation of Financial Statements
-- =============================================================================
CREATE OR REPLACE VIEW ifrs_balance_sheet_view AS
WITH account_balances AS (
    SELECT 
        ac.id,
        ac.code,
        ac.name,
        ac.account_type,
        ac.ifrs_category,
        ac.reporting_tag,
        ac.note_reference,
        CASE 
            WHEN ac.account_type IN ('ASSET', 'EXPENSE') THEN 
                COALESCE(SUM(ae.debit_amount), 0) - COALESCE(SUM(ae.credit_amount), 0)
            ELSE 
                COALESCE(SUM(ae.credit_amount), 0) - COALESCE(SUM(ae.debit_amount), 0)
        END as balance
    FROM accounting_codes ac
    LEFT JOIN accounting_entries ae ON ac.id = ae.accounting_code_id
    LEFT JOIN journal_entries je ON ae.journal_entry_id = je.id
    WHERE ac.is_active = true
    AND ac.ifrs_category IN ('CURRENT_ASSET', 'NON_CURRENT_ASSET', 'CURRENT_LIABILITY', 'NON_CURRENT_LIABILITY', 'EQUITY')
    GROUP BY ac.id, ac.code, ac.name, ac.account_type, ac.ifrs_category, ac.reporting_tag, ac.note_reference
)
SELECT 
    id,
    code,
    name,
    account_type,
    ifrs_category,
    reporting_tag,
    note_reference,
    ABS(balance) as amount,
    CASE 
        WHEN ifrs_category = 'CURRENT_ASSET' THEN 'Assets - Current'
        WHEN ifrs_category = 'NON_CURRENT_ASSET' THEN 'Assets - Non-Current'
        WHEN ifrs_category = 'CURRENT_LIABILITY' THEN 'Liabilities - Current'
        WHEN ifrs_category = 'NON_CURRENT_LIABILITY' THEN 'Liabilities - Non-Current'
        WHEN ifrs_category = 'EQUITY' THEN 'Equity'
        ELSE 'Other'
    END as balance_sheet_section,
    -- Ordering for proper balance sheet presentation
    CASE 
        WHEN ifrs_category = 'CURRENT_ASSET' THEN 1
        WHEN ifrs_category = 'NON_CURRENT_ASSET' THEN 2
        WHEN ifrs_category = 'CURRENT_LIABILITY' THEN 3
        WHEN ifrs_category = 'NON_CURRENT_LIABILITY' THEN 4
        WHEN ifrs_category = 'EQUITY' THEN 5
        ELSE 9
    END as section_order
FROM account_balances
WHERE balance != 0
ORDER BY section_order, code;

-- =============================================================================
-- View: IFRS Profit & Loss View
-- Standard: IAS 1 - Presentation of Financial Statements  
-- Standards: IFRS 15 - Revenue from Contracts with Customers
-- =============================================================================
CREATE OR REPLACE VIEW ifrs_profit_loss_view AS
WITH period_balances AS (
    SELECT 
        ac.id,
        ac.code,
        ac.name,
        ac.account_type,
        ac.ifrs_category,
        ac.reporting_tag,
        je.entry_date,
        CASE 
            WHEN ac.account_type IN ('EXPENSE', 'COST_OF_SALES', 'FINANCE_COST', 'TAX') THEN 
                COALESCE(SUM(ae.debit_amount), 0) - COALESCE(SUM(ae.credit_amount), 0)
            ELSE -- REVENUE, OTHER_INCOME
                COALESCE(SUM(ae.credit_amount), 0) - COALESCE(SUM(ae.debit_amount), 0)
        END as period_amount
    FROM accounting_codes ac
    LEFT JOIN accounting_entries ae ON ac.id = ae.accounting_code_id
    LEFT JOIN journal_entries je ON ae.journal_entry_id = je.id
    WHERE ac.is_active = true
    AND ac.account_type IN ('REVENUE', 'COST_OF_SALES', 'EXPENSE', 'OTHER_INCOME', 'OTHER_EXPENSE', 'FINANCE_COST', 'TAX')
    GROUP BY ac.id, ac.code, ac.name, ac.account_type, ac.ifrs_category, ac.reporting_tag, je.entry_date
)
SELECT 
    id,
    code,
    name,
    account_type,
    ifrs_category,
    reporting_tag,
    entry_date,
    period_amount,
    -- P&L Section Classification
    CASE 
        WHEN account_type = 'REVENUE' THEN 'Revenue'
        WHEN account_type = 'COST_OF_SALES' THEN 'Cost of Sales'
        WHEN account_type = 'EXPENSE' THEN 'Operating Expenses'
        WHEN account_type = 'OTHER_INCOME' THEN 'Other Income'
        WHEN account_type = 'OTHER_EXPENSE' THEN 'Other Expenses'
        WHEN account_type = 'FINANCE_COST' THEN 'Finance Costs'
        WHEN account_type = 'TAX' THEN 'Tax Expense'
        ELSE 'Other'
    END as pnl_section,
    -- Ordering for proper P&L presentation
    CASE 
        WHEN account_type = 'REVENUE' THEN 1
        WHEN account_type = 'COST_OF_SALES' THEN 2
        WHEN account_type = 'EXPENSE' THEN 3
        WHEN account_type = 'OTHER_INCOME' THEN 4
        WHEN account_type = 'OTHER_EXPENSE' THEN 5
        WHEN account_type = 'FINANCE_COST' THEN 6
        WHEN account_type = 'TAX' THEN 7
        ELSE 9
    END as section_order
FROM period_balances
WHERE period_amount != 0
ORDER BY section_order, code, entry_date;

-- =============================================================================
-- View: IFRS Debtors Aging View
-- Standard: IFRS 9 - Financial Instruments (Expected Credit Losses)
-- =============================================================================
CREATE OR REPLACE VIEW ifrs_debtors_aging_view AS
WITH outstanding_sales AS (
    SELECT 
        s.id as sale_id,
        s.customer_id,
        c.name as customer_name,
        c.credit_limit,
        s.invoice_number,
        s.sale_date,
        s.due_date,
        s.total_amount,
        COALESCE(s.paid_amount, 0) as paid_amount,
        s.total_amount - COALESCE(s.paid_amount, 0) as outstanding_amount,
        s.currency,
        s.payment_status,
        CURRENT_DATE - s.sale_date as days_outstanding
    FROM sales s
    LEFT JOIN customers c ON s.customer_id = c.id
    WHERE s.payment_status IN ('pending', 'partial')
    AND s.total_amount - COALESCE(s.paid_amount, 0) > 0
)
SELECT 
    sale_id,
    customer_id,
    customer_name,
    credit_limit,
    invoice_number,
    sale_date,
    due_date,
    total_amount,
    paid_amount,
    outstanding_amount,
    currency,
    payment_status,
    days_outstanding,
    -- Aging Buckets
    CASE 
        WHEN days_outstanding <= 30 THEN '0-30'
        WHEN days_outstanding <= 60 THEN '31-60'
        WHEN days_outstanding <= 90 THEN '61-90'
        WHEN days_outstanding <= 120 THEN '91-120'
        ELSE '120+'
    END as aging_bucket,
    -- IFRS 9 Expected Credit Loss Rates (simplified approach)
    CASE 
        WHEN days_outstanding <= 30 THEN 0.01 -- 1%
        WHEN days_outstanding <= 60 THEN 0.03 -- 3%
        WHEN days_outstanding <= 90 THEN 0.05 -- 5%
        WHEN days_outstanding <= 120 THEN 0.10 -- 10%
        ELSE 0.25 -- 25%
    END as ecl_rate,
    -- Expected Credit Loss Amount
    outstanding_amount * 
    CASE 
        WHEN days_outstanding <= 30 THEN 0.01
        WHEN days_outstanding <= 60 THEN 0.03
        WHEN days_outstanding <= 90 THEN 0.05
        WHEN days_outstanding <= 120 THEN 0.10
        ELSE 0.25
    END as expected_credit_loss,
    -- Risk Rating
    CASE 
        WHEN days_outstanding > 120 THEN 'HIGH'
        WHEN days_outstanding > 90 THEN 'MEDIUM'
        WHEN days_outstanding > 60 THEN 'LOW'
        ELSE 'CURRENT'
    END as risk_rating
FROM outstanding_sales
ORDER BY days_outstanding DESC, outstanding_amount DESC;

-- =============================================================================
-- View: IFRS Creditors Aging View
-- Standard: IAS 1 - Presentation of Financial Statements
-- =============================================================================
CREATE OR REPLACE VIEW ifrs_creditors_aging_view AS
WITH outstanding_purchases AS (
    SELECT 
        p.id as purchase_id,
        p.supplier_id,
        s.name as supplier_name,
        s.payment_terms,
        p.invoice_number,
        p.purchase_date,
        p.due_date,
        p.total_amount,
        COALESCE(p.paid_amount, 0) as paid_amount,
        p.total_amount - COALESCE(p.paid_amount, 0) as outstanding_amount,
        p.currency,
        p.payment_status,
        CURRENT_DATE - p.purchase_date as days_outstanding
    FROM purchases p
    LEFT JOIN suppliers s ON p.supplier_id = s.id
    WHERE p.payment_status IN ('pending', 'partial')
    AND p.total_amount - COALESCE(p.paid_amount, 0) > 0
)
SELECT 
    purchase_id,
    supplier_id,
    supplier_name,
    payment_terms,
    invoice_number,
    purchase_date,
    due_date,
    total_amount,
    paid_amount,
    outstanding_amount,
    currency,
    payment_status,
    days_outstanding,
    -- Aging Buckets
    CASE 
        WHEN days_outstanding <= 30 THEN '0-30'
        WHEN days_outstanding <= 60 THEN '31-60'
        WHEN days_outstanding <= 90 THEN '61-90'
        WHEN days_outstanding <= 120 THEN '91-120'
        ELSE '120+'
    END as aging_bucket,
    -- Payment Priority
    CASE 
        WHEN days_outstanding > 120 THEN 'URGENT'
        WHEN days_outstanding > 90 THEN 'HIGH'
        WHEN days_outstanding > 60 THEN 'MEDIUM'
        ELSE 'LOW'
    END as payment_priority
FROM outstanding_purchases
ORDER BY days_outstanding DESC, outstanding_amount DESC;

-- =============================================================================
-- View: IFRS Cash Flow View
-- Standard: IAS 7 - Statement of Cash Flows
-- =============================================================================
CREATE OR REPLACE VIEW ifrs_cash_flow_view AS
WITH cash_transactions AS (
    SELECT 
        je.id as journal_entry_id,
        je.entry_date,
        je.reference,
        je.narration,
        ac.code as account_code,
        ac.name as account_name,
        ac.account_type,
        ac.ifrs_category,
        ae.debit_amount,
        ae.credit_amount,
        -- Cash Flow Classification
        CASE 
            WHEN ac.reporting_tag LIKE '%cash%' OR ac.reporting_tag LIKE '%bank%' THEN
                CASE
                    WHEN je.reference LIKE 'SALE-%' OR je.reference LIKE 'PURCHASE-%' THEN 'Operating'
                    WHEN je.reference LIKE 'ASSET-%' OR je.reference LIKE 'INVESTMENT-%' THEN 'Investing'
                    WHEN je.reference LIKE 'LOAN-%' OR je.reference LIKE 'EQUITY-%' THEN 'Financing'
                    ELSE 'Operating'
                END
            ELSE NULL
        END as cash_flow_category,
        -- Net Cash Effect
        CASE 
            WHEN ac.account_type = 'ASSET' THEN 
                COALESCE(ae.debit_amount, 0) - COALESCE(ae.credit_amount, 0)
            ELSE 
                COALESCE(ae.credit_amount, 0) - COALESCE(ae.debit_amount, 0)
        END as cash_effect
    FROM journal_entries je
    JOIN accounting_entries ae ON je.id = ae.journal_entry_id
    JOIN accounting_codes ac ON ae.accounting_code_id = ac.id
    WHERE ac.reporting_tag LIKE '%cash%' 
    OR ac.reporting_tag LIKE '%bank%'
    OR ac.code LIKE '1100%' -- Cash and cash equivalents accounts
)
SELECT 
    journal_entry_id,
    entry_date,
    reference,
    narration,
    account_code,
    account_name,
    cash_flow_category,
    cash_effect,
    -- Running cash balance
    SUM(cash_effect) OVER (ORDER BY entry_date, journal_entry_id) as running_cash_balance
FROM cash_transactions
WHERE cash_flow_category IS NOT NULL
ORDER BY entry_date, journal_entry_id;

-- =============================================================================
-- View: IFRS Compliance Summary View
-- Multiple Standards Compliance Check
-- =============================================================================
CREATE OR REPLACE VIEW ifrs_compliance_summary_view AS
WITH trial_balance_check AS (
    SELECT 
        COUNT(*) as total_accounts,
        SUM(CASE WHEN ifrs_category IS NOT NULL AND ifrs_category != '' THEN 1 ELSE 0 END) as accounts_with_ifrs_category,
        ABS(SUM(CASE WHEN balance > 0 THEN balance ELSE 0 END) - 
            SUM(CASE WHEN balance < 0 THEN ABS(balance) ELSE 0 END)) as trial_balance_variance
    FROM ifrs_trial_balance_view
),
balance_sheet_check AS (
    SELECT 
        SUM(CASE WHEN balance_sheet_section LIKE 'Assets%' THEN amount ELSE 0 END) as total_assets,
        SUM(CASE WHEN balance_sheet_section LIKE 'Liabilities%' THEN amount ELSE 0 END) as total_liabilities,
        SUM(CASE WHEN balance_sheet_section = 'Equity' THEN amount ELSE 0 END) as total_equity
    FROM ifrs_balance_sheet_view
),
aging_check AS (
    SELECT 
        COUNT(*) as total_outstanding_invoices,
        SUM(outstanding_amount) as total_outstanding_amount,
        SUM(expected_credit_loss) as total_expected_credit_loss
    FROM ifrs_debtors_aging_view
)
SELECT 
    CURRENT_DATE as check_date,
    -- Trial Balance Compliance
    tb.total_accounts,
    tb.accounts_with_ifrs_category,
    ROUND((tb.accounts_with_ifrs_category::decimal / NULLIF(tb.total_accounts, 0)) * 100, 2) as ifrs_category_coverage_percent,
    tb.trial_balance_variance,
    CASE WHEN tb.trial_balance_variance = 0 THEN true ELSE false END as trial_balance_balanced,
    
    -- Balance Sheet Compliance
    bs.total_assets,
    bs.total_liabilities,
    bs.total_equity,
    ABS(bs.total_assets - (bs.total_liabilities + bs.total_equity)) as balance_sheet_variance,
    CASE WHEN ABS(bs.total_assets - (bs.total_liabilities + bs.total_equity)) < 0.01 THEN true ELSE false END as balance_sheet_balanced,
    
    -- IFRS 9 Compliance (Expected Credit Loss)
    ag.total_outstanding_invoices,
    ag.total_outstanding_amount,
    ag.total_expected_credit_loss,
    CASE WHEN ag.total_outstanding_amount > 0 THEN 
        ROUND((ag.total_expected_credit_loss / ag.total_outstanding_amount) * 100, 2) 
        ELSE 0 
    END as ecl_provision_rate,
    
    -- Overall Compliance Score
    ROUND(
        (
            (CASE WHEN tb.trial_balance_variance = 0 THEN 25 ELSE 0 END) +
            (CASE WHEN ABS(bs.total_assets - (bs.total_liabilities + bs.total_equity)) < 0.01 THEN 25 ELSE 0 END) +
            (CASE WHEN (tb.accounts_with_ifrs_category::decimal / NULLIF(tb.total_accounts, 0)) >= 0.8 THEN 25 ELSE 
                (tb.accounts_with_ifrs_category::decimal / NULLIF(tb.total_accounts, 0)) * 25 END) +
            (CASE WHEN ag.total_expected_credit_loss >= 0 THEN 25 ELSE 0 END)
        ), 2
    ) as overall_compliance_score
FROM trial_balance_check tb
CROSS JOIN balance_sheet_check bs
CROSS JOIN aging_check ag;

-- =============================================================================
-- Indexes for Performance Optimization
-- =============================================================================

-- Index on journal entry date for period reporting
CREATE INDEX IF NOT EXISTS idx_journal_entries_date ON journal_entries(entry_date);

-- Index on accounting entries for balance calculations
CREATE INDEX IF NOT EXISTS idx_accounting_entries_code_date ON accounting_entries(accounting_code_id);

-- Index on sales for aging calculations
CREATE INDEX IF NOT EXISTS idx_sales_aging ON sales(payment_status, sale_date) WHERE payment_status IN ('pending', 'partial');

-- Index on purchases for aging calculations  
CREATE INDEX IF NOT EXISTS idx_purchases_aging ON purchases(payment_status, purchase_date) WHERE payment_status IN ('pending', 'partial');

-- Index on accounting codes for IFRS categories
CREATE INDEX IF NOT EXISTS idx_accounting_codes_ifrs ON accounting_codes(ifrs_category, account_type) WHERE is_active = true;
