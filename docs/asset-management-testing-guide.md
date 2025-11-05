# Asset Management - View & Depreciate Testing Guide

## Overview
This guide demonstrates how to view and depreciate assets in the following categories:
- **Furniture & Fixtures**
- **Electronics & IT Equipment**
- **Motor Vehicles**
- **Tools & Equipment**

## Test Assets Created

### Furniture (2 assets)
- AST-0001: Executive Office Desk (P15,000.00 → P12,300.00)
- AST-0002: Conference Table (P25,000.00 → P20,500.00)

### Electronics/IT (2 assets)
- AST-0003: Dell Latitude Laptop (P18,000.00 → P14,760.00)
- AST-0004: HP LaserJet Printer (P5,500.00 → P4,510.00)

### Motor Vehicles (2 assets)
- AST-0005: Toyota Hilux (P450,000.00 → P369,000.00)
- AST-0006: Ford Ranger (P520,000.00 → P426,400.00)

### Tools & Equipment (2 assets)
- AST-0007: Bosch Drill Set (P3,500.00 → P2,870.00)
- AST-0008: Makita Grinder (P2,800.00 → P2,296.00)

## Testing Instructions

### 1. Access the Asset Management Module
Navigate to: http://localhost:8010/static/asset-management.html

### 2. Test Each Category Tab

#### Furniture & Fixtures Tab
1. Click on the **"Furniture & Fixtures"** tab
2. You should see 2 furniture assets loaded
3. For each asset, verify:
   - ✅ **View button** (eye icon) is present
   - ✅ **Depreciate button** (calculator icon) is present

**Testing View:**
- Click the **View** button on "Executive Office Desk"
- Should navigate to: `/static/asset.html?id=<asset-id>`
- Should show full asset details

**Testing Depreciate:**
- Click the **Depreciate** button on "Executive Office Desk"
- Should show confirmation: "Record depreciation as of today for this asset?"
- Click **OK**
- Asset should depreciate further and current value should decrease

#### Electronics & IT Equipment Tab
1. Click on the **"Electronics & IT Equipment"** tab
2. You should see 2 computer assets loaded
3. Test View and Depreciate buttons on both assets

#### Motor Vehicles Tab
1. Click on the **"Motor Vehicles"** tab
2. You should see 2 vehicle assets loaded
3. Note: This tab shows **Registration Number** instead of Serial Number
4. Test View and Depreciate buttons on both vehicles

#### Tools & Equipment Tab
1. Click on the **"Tools & Equipment"** tab
2. You should see 2 equipment assets loaded
3. Test View and Depreciate buttons on both tools

### 3. All Assets Tab
1. Click on the **"All Assets"** tab
2. Should show all 8 assets combined
3. Each asset should have appropriate action buttons based on type
4. Test **Print Register** button - should open printable report
5. Test **Export CSV** button - should download CSV file

## Expected Behavior

### View Button
- Navigates to individual asset detail page
- Shows complete asset information
- URL format: `/static/asset.html?id=<uuid>`

### Depreciate Button
- Shows confirmation dialog
- Records depreciation as of today's date
- Calls API: `POST /api/v1/asset-management/assets/{id}/depreciation?depreciation_date=YYYY-MM-DD`
- Updates current value in the table automatically
- No page refresh required

## API Endpoints Used

### Get Assets by Category
```
GET /api/v1/asset-management/assets/?category=FURNITURE&limit=1000
GET /api/v1/asset-management/assets/?category=COMPUTER&limit=1000
GET /api/v1/asset-management/assets/?category=VEHICLE&limit=1000
GET /api/v1/asset-management/assets/?category=EQUIPMENT&limit=1000
```

### Record Depreciation
```
POST /api/v1/asset-management/assets/{id}/depreciation?depreciation_date=2025-10-26
```

## Verification Checklist

- [ ] Furniture tab loads correctly
- [ ] Electronics tab loads correctly
- [ ] Vehicles tab loads correctly
- [ ] Equipment tab loads correctly
- [ ] View button works on all tabs
- [ ] Depreciate button works on all tabs
- [ ] Confirmation dialog appears before depreciation
- [ ] Table refreshes after depreciation
- [ ] Current value decreases after depreciation
- [ ] All Assets tab shows all 8 assets
- [ ] Print Register generates PDF-ready output
- [ ] Export CSV downloads file successfully

## Troubleshooting

### Assets Not Showing
- Check browser console for errors
- Verify API is running on port 8010
- Check category filter value (should be uppercase: FURNITURE, COMPUTER, VEHICLE, EQUIPMENT)

### View Button Not Working
- Check asset.html file exists at `/static/asset.html`
- Verify asset ID is being passed correctly in URL

### Depreciate Button Not Working
- Check API endpoint: `/api/v1/asset-management/assets/{id}/depreciation`
- Verify depreciation service is implemented
- Check console for API errors

## Success Criteria

✅ **All 4 category tabs work properly**
✅ **View button opens asset detail page**
✅ **Depreciate button records depreciation**
✅ **Tables refresh automatically after depreciation**
✅ **Print and Export functions work in All Assets tab**

---

## Test Results Log

Date: October 26, 2025
Tester: _________________

| Category | View Works | Depreciate Works | Notes |
|----------|-----------|------------------|-------|
| Furniture | ☐ | ☐ | |
| Electronics | ☐ | ☐ | |
| Vehicles | ☐ | ☐ | |
| Equipment | ☐ | ☐ | |
| All Assets | ☐ | ☐ | |
