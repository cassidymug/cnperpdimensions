# Dealership Accounts Payable Modeling (Parent/Sub-Accounts with GL Control)

This guide documents how to model brands and dealerships under Accounts Payable using a GL control account with brand-level parent accounts and dealership-level sub-accounts, while staying aligned with IFRS and keeping supplier subledger as the source of truth for aging and detailed audit trails.

## Scope and goals
- Enable brand-level rollup (e.g., TOYOTA) and dealership-level auditability (e.g., Toyota Gaborone).
- Keep the GL clean with a single AP control summary; keep detailed transactions in the supplier subledger.
- Support IFRS-compliant recognition of assets (IAS 16), inventory (IAS 2), revenue (IFRS 15), and expenses.

## IFRS alignment (high level)
- IAS 16 Property, Plant and Equipment: capitalize own-use vehicles and qualifying improvements; depreciate over useful life.
- IAS 2 Inventories: vehicles/parts held for resale are inventory; expense as COGS on sale.
- IFRS 15 Revenue: recognize revenue on transfer of control for sales.
- IAS 37 Provisions (if applicable) for warranties/major overhauls.

## Chart of Accounts structure
- AP Control (summary): `2110 Accounts Payable – Trade Suppliers` (control; no supplier detail here)
- Brand parent (rollup only):
  - Example: `2110-TY Accounts Payable – TOYOTA`
  - `account_type`: Liability
  - `category`: Trade Payables (Current Liabilities)
  - `is_parent`: true (no direct postings)
  - `parent_id`: points to AP control (if modeled hierarchically), or sits under the AP control section
- Dealership sub-accounts (posting):
  - Examples:
    - `2110-TY-01 AP – Toyota Gaborone`
    - `2110-TY-02 AP – Toyota Francistown`
  - `account_type`: Liability
  - `category`: Trade Payables (Current Liabilities)
  - `is_parent`: false
  - `parent_id`: the brand parent (e.g., `2110-TY`)

Notes:
- The AP control (`2110`) rolls up the total AP. The brand parent (`2110-TY`) rolls up all Toyota sub-accounts. All postings occur on dealership sub-accounts.
- If you prefer, the brand parent can be a non-posting group account with the roll-up aggregation only.

## Supplier subledger linkage (authoritative for aging)
- Each dealership is a Supplier record.
- Suppliers have `accounting_code_id` that points to their specific GL sub-account (e.g., `2110-TY-01`).
- All AP documents (invoices/credits/payments) for the supplier post to that sub-account.
- Aging, statements, and detailed audit are driven by the supplier subledger. The GL mirrors totals and provides period financial reporting and control reconciliation.

## Posting patterns (examples)

Own-use vehicle purchase (IAS 16):
```
Dr 1210 Motor Vehicles (cost)
Dr 1410 VAT Input (if recoverable)
Cr 2110-TY-01 AP – Toyota Gaborone
```

Routine service/repairs (expense):
```
Dr 5231 Repairs & Maintenance – Vehicles
Dr 1410 VAT Input (if recoverable)
Cr 2110-TY-01 AP – Toyota Gaborone
```

Capital improvement (extends life/significant component):
```
Dr 1210 Motor Vehicles
Cr 2110-TY-01 AP – Toyota Gaborone
```

Vehicles held for resale (IAS 2):
```
Dr 1140 Inventory – Vehicles
Dr 1410 VAT Input (if recoverable)
Cr 2110-TY-01 AP – Toyota Gaborone
```

Sale of inventory vehicle:
```
Dr AR/Bank
Cr Revenue – Vehicle Sales
Cr Output VAT (if applicable)

Dr 6110 Cost of Goods Sold – Vehicles
Cr 1140 Inventory – Vehicles
```

Payment to dealership:
```
Dr 2110-TY-01 AP – Toyota Gaborone
Cr 1111 Cash in Hand / 1120 Bank
```

Parts handling:
- If stocked: `1145 Inventory – Spare Parts` on purchase; expense when issued to jobs.
- If not stocked: expense directly to `5232 Parts & Consumables – Vehicles` on purchase.

## Naming and coding conventions
- AP control: `2110 Accounts Payable – Trade Suppliers`
- Brand parent (non-posting): `2110-XX Accounts Payable – BRAND`
- Dealership sub-accounts (posting): `2110-XX-YY AP – BRAND Location`
  - `XX` = brand code, `YY` = dealership sequence per brand.

## Reporting and reconciliation
- Subledger vs GL:
  - The supplier subledger total must equal the sum of AP GL sub-accounts (and equal the AP control account if you roll up to 2110).
  - Brand analysis: run balances/transactions for the brand parent to see roll-ups; per-dealership analysis via sub-accounts and the supplier subledger.
- Audit trail:
  - Retain `supplier_id` on journal lines along with `accounting_code_id` for traceability.
  - Tag with `branch_id`, `vehicle_id`, and cost center as needed for analytics.

## Application data model mapping

Accounting codes (`AccountingCode`):
- Fields: `id`, `code`, `name`, `account_type`, `category`, `is_parent`, `parent_id`, `branch_id`, etc.
- Brand parent: `is_parent=true`, `account_type=Liability`, `category=Trade Payables`.
- Dealership sub-account: `is_parent=false`, `parent_id` → brand parent.

Suppliers (`Supplier`):
- Add/ensure `accounting_code_id` (FK → dealership sub-account).
- Each supplier (dealership) is bound to exactly one posting GL sub-account for AP.

Journal entries (`JournalEntry` / `AccountingEntry`):
- Include `accounting_code_id` (which dealership sub-account), `supplier_id`, optional `branch_id`, `vehicle_id`, and `narration`.
- AP workflows auto-select the supplier’s bound `accounting_code_id` for credit lines.

Assets (Vehicles) (`Asset`):
- Use the Assets module for own-use vehicles.
- Depreciation posts: `Dr 5228 Depreciation Expense – Motor Vehicles` / `Cr 1219 Accumulated Depreciation – Motor Vehicles`.

## Validation rules (recommended)
- Prevent posting to brand parent accounts (`is_parent=true`).
- Require `supplier.accounting_code_id` for AP invoices/credits/payments and post to that sub-account.
- Enforce code formats:
  - Parent: `2110-XX`
  - Sub-account: `2110-XX-YY`
- Ensure `account_type=Liability` and `category=Trade Payables` for AP-related parent/sub-accounts.

## Setup checklist
1) Create/verify AP control: `2110 Accounts Payable – Trade Suppliers`.
2) For each brand (e.g., TOYOTA), create non-posting parent: `2110-TY` (Liability, Trade Payables, is_parent=true).
3) For each dealership, create posting sub-account under the brand parent (e.g., `2110-TY-01`).
4) Create suppliers for each dealership and set `accounting_code_id` to the dealership sub-account.
5) Update AP workflows to post credits/payments to the supplier-bound sub-account.
6) Train users: brand parent is roll-up only; all postings go to dealership sub-accounts.
7) Reconcile monthly: supplier subledger total = GL AP sub-accounts total = AP control balance.

## FAQ
**What is a GL control account?**
- A single GL account that summarizes the total of a detailed subledger (e.g., AP). The subledger holds supplier-level transactions and aging. The GL control shows the summarized balance for financial statements.

**Why not post directly to the AP control account?**
- You can, but you lose dealership-level GL visibility. Using brand parent + dealership sub-accounts improves auditability and analytics, while the supplier subledger remains authoritative for aging.

**Where do I store VAT?**
- Use separate VAT input/output accounts (e.g., `1410 VAT Input`, `2310 VAT Output`) according to local tax rules.

**How do I handle inventory vehicles vs own-use vehicles?**
- Inventory vehicles → IAS 2 (1140 Inventory; COGS on sale). Own-use vehicles → IAS 16 (1210/1219, depreciation 5228).

---
Last updated: YYYY-MM-DD

