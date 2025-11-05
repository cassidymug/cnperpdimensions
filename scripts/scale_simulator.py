"""
Scale Simulator - Test weight-based barcode system
Simulates a label printing scale for testing CNPERP integration
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from app.utils.weight_barcode import generate_weight_barcode, calculate_checksum
from decimal import Decimal
from datetime import datetime


API_BASE = "http://localhost:8010/api/v1"


def print_label(barcode, product_name, weight_kg, price_per_kg, total_price, tare):
    """Simulate printing a label"""
    print("\n" + "═" * 60)
    print("┌" + "─" * 58 + "┐")
    print(f"│  {product_name[:54].ljust(54)}  │")
    print("│" + " " * 58 + "│")
    print(f"│  {'█' * 50}  │")
    print(f"│  {barcode}  │")
    print("│" + " " * 58 + "│")
    print(f"│  Weight: {weight_kg:.3f} kg{' ' * 30}Price/kg: R{price_per_kg:.2f}  │")
    if tare > 0:
        print(f"│  Tare: {tare}g{' ' * 47}│")
    print(f"│  {' ' * 56}│")
    print(f"│  TOTAL: R {total_price:.2f}{' ' * 42}│")
    print(f"│  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{' ' * 34}│")
    print("└" + "─" * 58 + "┘")
    print("═" * 60)


def get_weight_products():
    """Fetch weight-based products from API"""
    try:
        response = requests.get(f"{API_BASE}/weight-products/weight-products")
        if response.status_code == 200:
            data = response.json()
            return data.get('products', [])
        else:
            print(f"❌ Error fetching products: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ API Error: {e}")
        print("⚠️  Make sure FastAPI server is running on http://localhost:8010")
        return []


def select_product(products):
    """Display products and let user select one"""
    if not products:
        print("❌ No weight-based products available")
        return None
    
    print("\n📦 Available Weight-Based Products:")
    print("─" * 80)
    print(f"{'#':<4} {'PLU':<8} {'Name':<30} {'Category':<12} {'Price/kg':<10}")
    print("─" * 80)
    
    for idx, p in enumerate(products, 1):
        print(f"{idx:<4} {p['barcode_sku']:<8} {p['name'][:28]:<30} "
              f"{p['category']:<12} R{p['price_per_kg']:<9.2f}")
    
    print("─" * 80)
    
    while True:
        try:
            choice = input("\n🔢 Select product number (or 'q' to quit): ").strip()
            if choice.lower() == 'q':
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(products):
                return products[idx]
            else:
                print("❌ Invalid selection. Try again.")
        except ValueError:
            print("❌ Please enter a valid number.")


def get_weight():
    """Simulate weighing - get weight from user"""
    while True:
        try:
            weight_input = input("\n⚖️  Enter weight in grams (or 'b' to go back): ").strip()
            if weight_input.lower() == 'b':
                return None
            
            weight = float(weight_input)
            if weight <= 0:
                print("❌ Weight must be positive")
                continue
            if weight > 99999:
                print("❌ Weight too large (max 99999g = 99.999kg)")
                continue
            
            return weight
        except ValueError:
            print("❌ Please enter a valid number")


def validate_barcode_api(barcode):
    """Validate barcode using API"""
    try:
        response = requests.post(
            f"{API_BASE}/weight-products/parse-weight-barcode",
            json={"barcode": barcode}
        )
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"⚠️  API validation failed: {e}")
        return None


def main():
    """Main scale simulator loop"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║  🏪 CNPERP SCALE SIMULATOR                                       ║
║  Simulating Label Printing Scale (Bizerba/CAS/Toledo)           ║
╚══════════════════════════════════════════════════════════════════╝
""")
    
    # Fetch products
    print("📡 Connecting to CNPERP API...")
    products = get_weight_products()
    
    if not products:
        print("\n⚠️  No products loaded. Please:")
        print("   1. Start FastAPI server: uvicorn app.main:app --reload")
        print("   2. Create weight-based products in the system")
        return
    
    print(f"✅ Loaded {len(products)} weight-based products")
    
    # Main loop
    while True:
        # Select product
        product = select_product(products)
        if not product:
            print("\n👋 Exiting scale simulator...")
            break
        
        print(f"\n✅ Selected: {product['name']}")
        print(f"   Category: {product['category']}")
        print(f"   Price/kg: R{product['price_per_kg']:.2f}")
        print(f"   Tare: {product['tare_weight']}g")
        if product['min_weight']:
            print(f"   Min weight: {product['min_weight']}g")
        if product['max_weight']:
            print(f"   Max weight: {product['max_weight']}g")
        
        # Get weight
        weight_grams = get_weight()
        if weight_grams is None:
            continue
        
        # Validate weight range
        if product['min_weight'] and weight_grams < product['min_weight']:
            print(f"⚠️  Warning: Weight below minimum ({product['min_weight']}g)")
            cont = input("   Continue anyway? (y/n): ")
            if cont.lower() != 'y':
                continue
        
        if product['max_weight'] and weight_grams > product['max_weight']:
            print(f"⚠️  Warning: Weight exceeds maximum ({product['max_weight']}g)")
            cont = input("   Continue anyway? (y/n): ")
            if cont.lower() != 'y':
                continue
        
        # Generate barcode
        barcode = generate_weight_barcode(
            product['barcode_prefix'],
            product['barcode_sku'],
            int(weight_grams)
        )
        
        print(f"\n🔖 Generated Barcode: {barcode}")
        
        # Calculate price
        weight_kg = weight_grams / 1000
        tare_kg = product['tare_weight'] / 1000
        net_weight_kg = max(0, weight_kg - tare_kg)
        total_price = net_weight_kg * product['price_per_kg']
        
        print(f"   Gross weight: {weight_kg:.3f} kg")
        print(f"   Net weight:   {net_weight_kg:.3f} kg (after {product['tare_weight']}g tare)")
        print(f"   Total price:  R{total_price:.2f}")
        
        # Simulate printing label
        print("\n🖨️  Printing label...")
        print_label(
            barcode,
            product['name'],
            weight_kg,
            product['price_per_kg'],
            total_price,
            product['tare_weight']
        )
        
        # Validate via API
        print("\n🔍 Validating barcode via CNPERP API...")
        validation = validate_barcode_api(barcode)
        
        if validation and validation.get('success'):
            print("✅ Barcode validated successfully!")
            print(f"   Product: {validation['product_name']}")
            print(f"   Category: {validation['category']}")
            print(f"   Calculated price: R{validation['unit_price']:.2f}")
            if abs(validation['unit_price'] - total_price) < 0.01:
                print("   ✅ Price matches scale calculation")
            else:
                print(f"   ⚠️  Price mismatch! API: R{validation['unit_price']:.2f} vs Scale: R{total_price:.2f}")
        else:
            error = validation.get('error', 'Unknown error') if validation else 'API request failed'
            print(f"❌ Validation failed: {error}")
        
        # Ask to continue
        print("\n" + "─" * 80)
        cont = input("🔄 Weigh another item? (y/n): ")
        if cont.lower() != 'y':
            print("\n👋 Exiting scale simulator...")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Scale simulator interrupted. Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
