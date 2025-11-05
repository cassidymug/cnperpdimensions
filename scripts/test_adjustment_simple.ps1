# Test Inventory Adjustment API
# Usage: .\test_adjustment_simple.ps1

$BaseUrl = "http://localhost:8010/api/v1/inventory"

Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "INVENTORY ADJUSTMENT API TEST" -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Cyan

# Step 1: Get a product to test with
Write-Host "`nStep 1: Fetching products..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/products" -Method Get
    $product = $response[0]
    $productId = $product.id
    $productName = $product.name
    $currentQty = $product.quantity

    Write-Host "   Product: $productName" -ForegroundColor Green
    Write-Host "   Current Quantity: $currentQty" -ForegroundColor Green
} catch {
    Write-Host "   [ERROR] Failed to fetch products: $_" -ForegroundColor Red
    exit 1
}

# Step 2: Test inventory increase (gain)
Write-Host "`nStep 2: Testing inventory increase by 10 units..." -ForegroundColor Cyan
$adjustmentData = @{
    product_id = $productId
    quantity_change = 10
    adjustment_type = "gain"
    reason = "PowerShell test - found extra stock"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/adjustments" -Method Post `
        -Body $adjustmentData -ContentType "application/json"

    Write-Host "   [SUCCESS] Adjustment created!" -ForegroundColor Green
    Write-Host "   Adjustment ID: $($response.id)" -ForegroundColor White
    Write-Host "   Previous qty: $($response.previous_quantity)" -ForegroundColor White
    Write-Host "   New qty: $($response.new_quantity)" -ForegroundColor White
    Write-Host "   Total amount: $($response.total_amount)" -ForegroundColor White
} catch {
    Write-Host "   [ERROR] Failed: $_" -ForegroundColor Red
    Write-Host "   Response: $($_.ErrorDetails.Message)" -ForegroundColor Red
    exit 1
}

# Step 3: Test inventory decrease (damage)
Write-Host "`nStep 3: Testing inventory decrease by 5 units (damage)..." -ForegroundColor Cyan
$adjustmentData = @{
    product_id = $productId
    quantity_change = -5
    adjustment_type = "damage"
    reason = "PowerShell test - damaged goods"
    notes = "Test adjustment from PowerShell"
} | ConvertTo-Json

try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/adjustments" -Method Post `
        -Body $adjustmentData -ContentType "application/json"

    Write-Host "   [SUCCESS] Adjustment created!" -ForegroundColor Green
    Write-Host "   Adjustment ID: $($response.id)" -ForegroundColor White
    Write-Host "   Previous qty: $($response.previous_quantity)" -ForegroundColor White
    Write-Host "   New qty: $($response.new_quantity)" -ForegroundColor White
    Write-Host "   Total amount: $($response.total_amount)" -ForegroundColor White
} catch {
    Write-Host "   [ERROR] Failed: $_" -ForegroundColor Red
    Write-Host "   Response: $($_.ErrorDetails.Message)" -ForegroundColor Red
    exit 1
}

# Step 4: Get adjustment history
Write-Host "`nStep 4: Fetching adjustment history..." -ForegroundColor Cyan
try {
    $adjustments = Invoke-RestMethod -Uri "$BaseUrl/adjustments?product_id=$productId&limit=5" -Method Get

    Write-Host "   [SUCCESS] Found $($adjustments.Count) recent adjustments:" -ForegroundColor Green
    foreach ($adj in $adjustments) {
        Write-Host "   - $($adj.adjustment_date): $($adj.adjustment_type) - $($adj.reason)" -ForegroundColor White
        Write-Host "     Qty: $($adj.quantity), Amount: $($adj.total_amount)" -ForegroundColor Gray
    }
} catch {
    Write-Host "   [ERROR] Failed to fetch adjustments: $_" -ForegroundColor Red
}

# Step 5: Verify final quantity
Write-Host "`nStep 5: Verifying final product quantity..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "$BaseUrl/products" -Method Get
    $updatedProduct = $response | Where-Object { $_.id -eq $productId }

    $finalQty = $updatedProduct.quantity
    $expectedQty = $currentQty + 10 - 5

    Write-Host "   Expected quantity: $expectedQty" -ForegroundColor White
    Write-Host "   Actual quantity: $finalQty" -ForegroundColor White

    if ($finalQty -eq $expectedQty) {
        Write-Host "   [SUCCESS] Quantity matches!" -ForegroundColor Green
    } else {
        Write-Host "   [ERROR] Quantity mismatch! Difference: $($finalQty - $expectedQty)" -ForegroundColor Red
    }
} catch {
    Write-Host "   [ERROR] Failed to verify quantity: $_" -ForegroundColor Red
}

Write-Host "`n================================================================================" -ForegroundColor Cyan
Write-Host "[SUCCESS] ALL TESTS COMPLETED!" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
