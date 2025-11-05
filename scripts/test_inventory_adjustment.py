"""
Test script for inventory adjustment endpoint
"""
import requests
import json

BASE_URL = "http://localhost:8010/api/v1/inventory"

def test_create_adjustment():
    """Test creating an inventory adjustment"""

    # First, get a product to adjust
    response = requests.get(f"{BASE_URL}/products")
    if response.status_code != 200:
        print(f"❌ Failed to fetch products: {response.status_code}")
        return

    products = response.json()
    if not products:
        print("❌ No products found in inventory")
        return

    # Use the first product
    product = products[0]
    product_id = product['id']
    product_name = product['name']
    current_qty = product['quantity']

    print(f"📦 Testing with product: {product_name}")
    print(f"   Current quantity: {current_qty}")

    # Test 1: Increase inventory (gain)
    print("\n🔼 Test 1: Increasing inventory by 10 units...")
    adjustment_data = {
        "product_id": product_id,
        "quantity_change": 10,
        "adjustment_type": "gain",
        "reason": "Test inventory gain - found extra stock"
    }

    response = requests.post(
        f"{BASE_URL}/adjustments",
        json=adjustment_data,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Adjustment created successfully!")
        print(f"   Adjustment ID: {result['id']}")
        print(f"   Previous qty: {result['previous_quantity']}")
        print(f"   New qty: {result['new_quantity']}")
        print(f"   Total amount: ${result['total_amount']}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return

    # Test 2: Decrease inventory (damage)
    print("\n🔽 Test 2: Decreasing inventory by 5 units (damage)...")
    adjustment_data = {
        "product_id": product_id,
        "quantity_change": -5,
        "adjustment_type": "damage",
        "reason": "Test inventory loss - damaged goods",
        "notes": "Items damaged during handling"
    }

    response = requests.post(
        f"{BASE_URL}/adjustments",
        json=adjustment_data,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code == 200:
        result = response.json()
        print(f"✅ Adjustment created successfully!")
        print(f"   Adjustment ID: {result['id']}")
        print(f"   Previous qty: {result['previous_quantity']}")
        print(f"   New qty: {result['new_quantity']}")
        print(f"   Total amount: ${result['total_amount']}")
    else:
        print(f"❌ Failed: {response.status_code}")
        print(f"   Error: {response.text}")
        return

    # Test 3: Get adjustments for this product
    print("\n📋 Test 3: Fetching adjustment history...")
    response = requests.get(f"{BASE_URL}/adjustments?product_id={product_id}")

    if response.status_code == 200:
        adjustments = response.json()
        print(f"✅ Found {len(adjustments)} adjustments for this product:")
        for adj in adjustments[:5]:  # Show last 5
            print(f"   - {adj['adjustment_date']}: {adj['adjustment_type']} - {adj['reason']}")
            print(f"     Qty change: {adj['quantity']}, Amount: ${adj['total_amount']}")
    else:
        print(f"❌ Failed to fetch adjustments: {response.status_code}")

    # Verify final quantity
    print("\n🔍 Verifying final product quantity...")
    response = requests.get(f"{BASE_URL}/products")
    products = response.json()
    updated_product = next((p for p in products if p['id'] == product_id), None)

    if updated_product:
        final_qty = updated_product['quantity']
        expected_qty = current_qty + 10 - 5
        print(f"   Expected quantity: {expected_qty}")
        print(f"   Actual quantity: {final_qty}")

        if final_qty == expected_qty:
            print("   ✅ Quantity matches!")
        else:
            print(f"   ❌ Quantity mismatch! Difference: {final_qty - expected_qty}")


if __name__ == "__main__":
    print("=" * 80)
    print("INVENTORY ADJUSTMENT API TEST")
    print("=" * 80)

    try:
        test_create_adjustment()
        print("\n" + "=" * 80)
        print("✅ All tests completed!")
        print("=" * 80)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
