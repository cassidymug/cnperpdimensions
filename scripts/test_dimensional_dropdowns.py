"""
Test script to verify dimensional accounting dropdowns populate correctly in purchases modal
"""
import requests
import json

BASE_URL = "http://localhost:8010/api/v1"

def test_dimensional_data_endpoints():
    print("=" * 60)
    print("Testing Dimensional Accounting Data Endpoints")
    print("=" * 60)

    # Test 1: Get dimensions with values
    print("\n1. GET /accounting/dimensions?include_values=true")
    try:
        r = requests.get(f"{BASE_URL}/accounting/dimensions?include_values=true")
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            dimensions = data.get('data', data) if isinstance(data, dict) else data
            print(f"   Found {len(dimensions)} dimensions")

            for dim in dimensions:
                print(f"\n   Dimension: {dim.get('name')} ({dim.get('code')})")
                print(f"   Type: {dim.get('dimension_type')}")
                values = dim.get('dimension_values', [])
                active_values = [v for v in values if v.get('is_active')]
                print(f"   Active Values: {len(active_values)}")

                if active_values:
                    print(f"   Sample values:")
                    for v in active_values[:3]:
                        print(f"     - {v.get('code')}: {v.get('name')}")
        else:
            print(f"   Error: {r.text}")
    except Exception as e:
        print(f"   ERROR: {e}")

    # Test 2: Get specific dimension types
    print("\n2. Testing dimension type filtering")
    for dim_type in ['functional', 'project']:
        print(f"\n   GET /accounting/dimensions?dimension_type={dim_type}")
        try:
            r = requests.get(f"{BASE_URL}/accounting/dimensions?dimension_type={dim_type}")
            print(f"   Status: {r.status_code}")
            if r.status_code == 200:
                data = r.json()
                dimensions = data.get('data', data) if isinstance(data, dict) else data
                print(f"   Found {len(dimensions)} {dim_type} dimensions")
        except Exception as e:
            print(f"   ERROR: {e}")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)
    print("\nExpected behavior:")
    print("- Dimensions endpoint should return dimensions with dimension_values")
    print("- FUNCTIONAL type dimension contains Cost Centers (DEPT)")
    print("- PROJECT type dimension contains Projects (PROJ)")
    print("- Each dimension_value should have: id, code, name, is_active")
    print("\nIn purchases.html:")
    print("- loadDimensionalData() fetches dimensions with include_values=true")
    print("- Filters by dimension_type to find FUNCTIONAL and PROJECT")
    print("- Extracts dimension_values and filters for is_active=true")
    print("- populateDimensionalOptions() populates the dropdowns")
    print("- Modal shown event re-populates to ensure fresh data")

if __name__ == "__main__":
    test_dimensional_data_endpoints()
