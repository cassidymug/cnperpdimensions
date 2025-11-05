# Branch Sales - Real-Time Detail View

**Date**: October 26, 2025
**Feature**: Click-to-View Real-Time Branch Sales
**Module**: Branch Sales Monitoring (`branch-sales.html`)

---

## 🎯 Feature Overview

Added interactive functionality to the Branch Sales page that allows users to **click on any branch** to view its **real-time sales transactions** as they happen.

### Key Capabilities

✅ **Clickable Branch Rows** - Click any branch in the table to view detailed sales
✅ **Real-Time Transaction Feed** - See actual sales as they occur
✅ **Auto-Refresh** - Detail view updates every 10 seconds automatically
✅ **Hourly Breakdown** - Visual chart showing sales distribution by hour
✅ **Payment Method Tracking** - See breakdown of cash, card, mobile payments
✅ **Recent Transactions List** - Complete list of recent sales with receipt numbers
✅ **Live Metrics** - Total sales, transaction count, average transaction, last sale

---

## 📱 User Interface

### Main Page Enhancement

**Before**: Table showing branch summary data
**After**: Table rows are now **clickable** with hover effects

**Visual Indicators**:
- 🏪 Shop icon next to branch name
- Hover effect: Light blue background highlight
- Cursor changes to pointer on row hover
- Subtle scale animation on interaction

### Branch Detail Modal

When you click a branch, a large modal appears showing:

#### Top Metrics (4 Cards)
```
┌─────────────────┬─────────────────┬─────────────────┬─────────────────┐
│ Total Sales     │ Transactions    │ Last Sale       │ Payment Methods │
│ P45,230.50      │ 127             │ P350.00         │ Cash: P25,000   │
│ Last 24 hours   │ Avg: P356.35    │ 5 min ago       │ Card: P15,000   │
│                 │                 │                 │ Mobile: P5,230  │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
```

#### Recent Transactions Table
Live-updating table showing:
- Time (e.g., "2:35 PM")
- Receipt Number (e.g., "RCP-20251026-A1B2C3D4")
- Customer Name
- Item Count
- Payment Method (badge)
- Amount (right-aligned)

**Example**:
```
Time     Receipt #         Customer           Items  Payment   Amount
----------------------------------------------------------------------
2:35 PM  RCP-2025-A1B2    John Smith         3      Cash      P350.00
2:32 PM  RCP-2025-A1B1    Walk-in Customer   1      Card      P125.50
2:28 PM  RCP-2025-A1B0    ABC Company        12     Mobile    P5,250.00
```

#### Hourly Sales Chart
Dual-axis chart showing:
- **Bars**: Sales amount per hour (left axis)
- **Line**: Transaction count per hour (right axis)
- **X-axis**: Time (e.g., "12:00 PM", "1:00 PM", "2:00 PM")

---

## 🔄 Real-Time Features

### Auto-Refresh Mechanism

**Modal Open**:
1. Initial data load when branch is clicked
2. Auto-refresh starts immediately
3. Refreshes every **10 seconds**
4. Visual indicator: Pulsing green dot in modal title

**Modal Close**:
1. Auto-refresh stops
2. Resources cleaned up
3. Chart destroyed to prevent memory leaks

### Manual Refresh

Users can click the **"Refresh"** button in modal footer to:
- Force immediate data update
- Useful when waiting for a specific transaction
- No need to close and reopen modal

---

## 🛠️ Technical Implementation

### Frontend Changes

**File**: `app/static/branch-sales.html`

#### 1. Made Table Rows Clickable

**Before**:
```html
<tr>
    <td>
        <span class="branch-name">Gaborone HQ</span>
    </td>
    ...
</tr>
```

**After**:
```html
<tr class="branch-row"
    style="cursor: pointer;"
    onclick="showBranchDetail('branch-123', 'Gaborone HQ')">
    <td>
        <span class="branch-name">
            <i class="bi bi-shop me-2 text-primary"></i>Gaborone HQ
        </span>
    </td>
    ...
</tr>
```

**CSS Added**:
```css
.branch-row {
    transition: background-color 0.2s ease, transform 0.2s ease;
}

.branch-row:hover {
    background-color: rgba(13, 110, 253, 0.05) !important;
    transform: scale(1.01);
}

.branch-row:active {
    transform: scale(0.99);
}
```

#### 2. Created Branch Detail Modal

**Structure**:
- Bootstrap 5 Modal XL (1200px wide)
- Scrollable content
- Sticky header with branch name
- Live data indicator (pulsing green dot)

**Components**:
1. **Metrics Row**: 4 cards showing key stats
2. **Transactions Table**: Recent sales with scrollable area (max 400px)
3. **Hourly Chart**: Bar+Line combo chart using Chart.js

#### 3. JavaScript Functions Added

**Main Functions**:

```javascript
// Show modal with branch data
async function showBranchDetail(branchId, branchName)

// Load detail data from API
async function loadBranchDetail()

// Update recent transactions table
function updateRecentTransactions(sales)

// Update hourly breakdown chart
function updateBranchHourlyChart(hourlyData)

// Auto-refresh controls
function startBranchDetailRefresh()
function stopBranchDetailRefresh()
function refreshBranchDetail()

// Helper: Format date/time with "ago" format
function formatDateTime(dateString)
```

**Auto-Refresh Logic**:
```javascript
// Modal shown event
modalElement.addEventListener('shown.bs.modal', () => {
    startBranchDetailRefresh(); // Start 10-second interval
});

// Modal hidden event
modalElement.addEventListener('hidden.bs.modal', () => {
    stopBranchDetailRefresh(); // Clear interval
    if (branchHourlyChart) {
        branchHourlyChart.destroy(); // Clean up chart
    }
});
```

### Backend API (Already Exists)

**Endpoint**: `GET /api/v1/v1/branch-sales/{branch_id}/detail`

**Query Parameters**:
- `hours`: Number of hours to look back (1-168, default: 24)

**Response**:
```json
{
  "branch_id": "branch-123",
  "branch_name": "Gaborone HQ",
  "total_sales": 45230.50,
  "transaction_count": 127,
  "avg_transaction": 356.35,
  "last_sale_amount": 350.00,
  "last_sale_time": "2025-10-26T14:35:00",
  "payment_breakdown": {
    "cash": 25000.00,
    "card": 15000.00,
    "mobile": 5230.50
  },
  "hourly_data": [
    {
      "hour": "2025-10-26T13:00:00",
      "sales_count": 15,
      "sales_amount": 5250.00
    },
    ...
  ],
  "recent_sales": [
    {
      "id": "sale-123",
      "date": "2025-10-26T14:35:00",
      "receipt_number": "RCP-2025-A1B2",
      "customer_name": "John Smith",
      "item_count": 3,
      "payment_method": "cash",
      "total_amount": 350.00
    },
    ...
  ]
}
```

---

## 📊 Data Flow

```
User Action: Click Branch Row
    ↓
JavaScript: showBranchDetail(branchId, branchName)
    ↓
Modal: Show with loading spinner
    ↓
API Call: GET /api/v1/v1/branch-sales/{branchId}/detail?hours=24
    ↓
Response: Branch detail data (JSON)
    ↓
Update Modal:
    ├─ Metrics cards (total, count, avg, last sale)
    ├─ Payment methods breakdown
    ├─ Recent transactions table
    └─ Hourly chart (Chart.js)
    ↓
Auto-Refresh: setInterval(10000ms)
    ↓
Modal Still Open? → Repeat API call every 10 seconds
    ↓
User Closes Modal → clearInterval, destroy chart
```

---

## 🎨 Visual Enhancements

### Hover Effects

**Branch Rows**:
- Light blue background on hover
- Slight scale-up animation (1.01)
- Cursor pointer
- Active state: scale-down (0.99)

**Transaction Rows** (in modal):
- Light blue background on hover
- Smooth transition

### Status Indicators

**Real-Time Badge**:
```html
<span class="real-time-indicator"></span>
```
- Pulsing green dot
- CSS animation: opacity 1 → 0.5 → 1 (1.5s loop)
- Glowing shadow effect

**Payment Method Badges**:
- Bootstrap secondary badge
- Different colors possible for different methods

### Chart Styling

**Hourly Chart**:
- **Bars**: Blue (#0d6efd) for sales amount
- **Line**: Green (#198754) for transaction count
- Dual Y-axes with proper labels
- Tooltip shows both metrics
- Responsive and maintains aspect ratio

---

## 🚀 User Workflow

### Scenario 1: Monitor Active Branch

1. **Open** Branch Sales page
2. **View** summary table showing all branches
3. **Click** on "Gaborone HQ" row
4. **Modal opens** showing:
   - Total sales today: P45,230.50
   - 127 transactions
   - Last sale: 5 min ago (P350.00)
   - Recent transactions updating live
5. **Watch** as new sales appear every 10 seconds
6. **See** hourly chart showing peak hours
7. **Close** modal when done

### Scenario 2: Check Specific Transaction

1. Click branch row
2. Modal shows recent transactions
3. Scroll through transaction list
4. Find specific receipt number
5. Note customer name, time, amount
6. Click "Refresh" to ensure latest data

### Scenario 3: Compare Payment Methods

1. Click branch row
2. View "Payment Methods" card
3. See breakdown:
   - Cash: P25,000 (55%)
   - Card: P15,000 (33%)
   - Mobile: P5,230 (12%)
4. Make business decisions based on data

---

## ⚡ Performance Optimizations

### Caching (Backend)

**File**: `app/api/v1/endpoints/branch_sales_realtime.py`

```python
cache_key = f"branch_detail_{branch_id}_{hours}"
cached = get_cached_data(cache_key, ttl=5)  # 5-second cache

if cached:
    return cached
```

**Benefits**:
- Reduces database queries
- Faster response times
- Lower server load
- 5-second TTL balances freshness and performance

### Resource Cleanup

**Chart Destruction**:
```javascript
if (branchHourlyChart) {
    branchHourlyChart.destroy();
    branchHourlyChart = null;
}
```

**Prevents**:
- Memory leaks
- Canvas rendering issues
- Multiple chart instances

### Efficient Updates

**Only Updates When Visible**:
- Auto-refresh only runs when modal is open
- Stops immediately when modal closes
- No background polling

---

## 📱 Responsive Design

### Desktop (>1200px)
- XL modal (1200px wide)
- 4-column metrics grid
- Full chart height

### Tablet (768px - 1199px)
- Modal scales to viewport
- 2-column metrics grid
- Responsive table with horizontal scroll

### Mobile (<768px)
- Full-width modal
- 1-column metrics grid (stacked)
- Simplified table view
- Touch-friendly interactions

---

## 🔒 Security & Validation

### Branch Access Control

**API Level**:
- Validates branch exists in database
- Returns 404 if branch not found
- User permissions checked (future enhancement)

**Frontend**:
- Sanitizes branch name display
- Uses `escapeHtml()` to prevent XSS
- Branch ID validated before API call

### Data Validation

**Null/Empty Checks**:
```javascript
if (!sales || sales.length === 0) {
    // Show "No transactions" message
}

if (data.payment_breakdown && Object.keys(data.payment_breakdown).length > 0) {
    // Render payment methods
} else {
    // Show "No data"
}
```

---

## 🧪 Testing Scenarios

### Test 1: Click Branch with Active Sales

**Steps**:
1. Open branch-sales.html
2. Click a branch with recent sales
3. Verify modal opens
4. Check all metrics display correctly
5. Verify transactions table populated
6. Check chart renders

**Expected**:
✅ Modal opens smoothly
✅ Metrics show correct values
✅ Transactions appear in reverse chronological order
✅ Chart displays hourly data
✅ Auto-refresh starts

### Test 2: Click Branch with No Sales

**Steps**:
1. Click a branch with 0 transactions
2. Verify modal shows gracefully

**Expected**:
✅ Total sales: P0.00
✅ Transaction count: 0
✅ "No transactions" message
✅ Chart shows empty state

### Test 3: Auto-Refresh

**Steps**:
1. Open branch detail modal
2. Wait 10 seconds
3. Observe data update

**Expected**:
✅ Data refreshes automatically
✅ No page flicker
✅ Scroll position maintained
✅ Chart updates smoothly

### Test 4: Manual Refresh

**Steps**:
1. Open modal
2. Click "Refresh" button
3. Verify immediate update

**Expected**:
✅ Loading indicator (if visible)
✅ Data updates immediately
✅ No errors in console

### Test 5: Close Modal

**Steps**:
1. Open modal
2. Wait for auto-refresh to start
3. Close modal
4. Wait 10 seconds

**Expected**:
✅ Auto-refresh stops
✅ No API calls after close
✅ Chart destroyed
✅ No console errors

---

## 📈 Future Enhancements

### Potential Improvements

1. **Export Transactions**
   - Download recent sales as CSV/Excel
   - Include filtering options

2. **Real-Time Notifications**
   - WebSocket connection for live updates
   - Sound alert on new sale
   - Desktop notifications

3. **Advanced Filtering**
   - Filter by payment method
   - Filter by customer
   - Filter by amount range
   - Date/time range selector

4. **Sales Analytics**
   - Top selling products in branch
   - Customer frequency chart
   - Staff performance (if tracked)
   - Hourly peak analysis

5. **Comparison Mode**
   - View multiple branches side-by-side
   - Compare performance metrics
   - Relative performance indicators

6. **Print/Share**
   - Print branch report
   - Email branch summary
   - Share link to specific branch view

---

## ✅ Summary

The Branch Sales page now provides **comprehensive real-time visibility** into individual branch performance:

### What's New
✅ **Clickable branch rows** with hover effects
✅ **Real-time sales detail modal** with auto-refresh
✅ **Live transaction feed** updating every 10 seconds
✅ **Hourly sales breakdown** chart
✅ **Payment method analysis**
✅ **Recent sales list** with full details
✅ **Responsive design** for all devices

### Benefits
- 📊 **Better visibility** into branch performance
- ⏱️ **Real-time monitoring** of sales as they happen
- 💡 **Data-driven decisions** with live metrics
- 🎯 **Quick access** to transaction details
- 🔄 **Automatic updates** every 10 seconds
- 🚀 **Optimized performance** with caching

### User Experience
- 🖱️ **Simple interaction**: Just click the branch
- 👁️ **Clear visualization**: Charts and tables
- ⚡ **Fast response**: Cached data, 5-second TTL
- 📱 **Mobile friendly**: Responsive layout
- ♻️ **Resource efficient**: Proper cleanup

**Status**: ✅ **PRODUCTION READY**

Users can now click any branch and see actual sales happening in real-time!
