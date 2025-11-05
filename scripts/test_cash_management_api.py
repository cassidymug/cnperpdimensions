"""
Test script for cash management endpoints.
This script demonstrates how to use the new cash submission and float allocation APIs.

Make sure the FastAPI server is running on http://localhost:8010
"""

import requests
import json
from datetime import date, datetime
from decimal import Decimal

BASE_URL = "http://localhost:8010/api/v1/sales"

def test_cash_submission():
    """Test cash submission endpoint"""
    print("\n=== Testing Cash Submission ===")

    # You'll need to replace these with actual IDs from your database
    submission_data = {
        "salesperson_id": "USER_ID_HERE",  # Replace with actual user ID
        "amount": 7410.00,
        "submission_date": date.today().isoformat(),
        "notes": "End of day cash submission - test"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/cash-submissions",
            json=submission_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 201:
            print("✅ Cash submission created successfully!")
            result = response.json()
            print(f"   Submission ID: {result['id']}")
            print(f"   Amount: P {result['amount']:,.2f}")
            print(f"   Status: {result['status']}")
            print(f"   Journal Entry: {result['journal_entry_id']}")
            return result['id']
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return None

    except requests.exceptions.ConnectionError:
        print("❌ Error: Cannot connect to server. Is it running on http://localhost:8010?")
        return None
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


def test_get_cash_submissions():
    """Test getting cash submissions"""
    print("\n=== Testing Get Cash Submissions ===")

    try:
        response = requests.get(f"{BASE_URL}/cash-submissions")

        if response.status_code == 200:
            submissions = response.json()
            print(f"✅ Found {len(submissions)} cash submissions")

            for sub in submissions[:5]:  # Show first 5
                print(f"\n   ID: {sub['id'][:8]}...")
                print(f"   Salesperson: {sub['salesperson_name'] or 'Unknown'}")
                print(f"   Amount: P {sub['amount']:,.2f}")
                print(f"   Date: {sub['submission_date']}")
                print(f"   Status: {sub['status']}")

        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


def test_float_allocation():
    """Test float allocation endpoint"""
    print("\n=== Testing Float Allocation ===")

    # You'll need to replace these with actual IDs from your database
    allocation_data = {
        "cashier_id": "USER_ID_HERE",  # Replace with actual user ID
        "float_amount": 1000.00,
        "allocation_date": date.today().isoformat(),
        "notes": "Morning float for cashier - test"
    }

    try:
        response = requests.post(
            f"{BASE_URL}/float-allocations",
            json=allocation_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 201:
            print("✅ Float allocation created successfully!")
            result = response.json()
            print(f"   Allocation ID: {result['id']}")
            print(f"   Float Amount: P {result['float_amount']:,.2f}")
            print(f"   Status: {result['status']}")
            print(f"   Journal Entry: {result['allocation_journal_entry_id']}")
            return result['id']
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")
            return None

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None


def test_get_float_allocations():
    """Test getting float allocations"""
    print("\n=== Testing Get Float Allocations ===")

    try:
        response = requests.get(f"{BASE_URL}/float-allocations")

        if response.status_code == 200:
            allocations = response.json()
            print(f"✅ Found {len(allocations)} float allocations")

            for alloc in allocations[:5]:  # Show first 5
                print(f"\n   ID: {alloc['id'][:8]}...")
                print(f"   Cashier: {alloc['cashier_name'] or 'Unknown'}")
                print(f"   Float: P {alloc['float_amount']:,.2f}")
                print(f"   Returned: P {alloc['amount_returned']:,.2f}")
                print(f"   Date: {alloc['allocation_date']}")
                print(f"   Status: {alloc['status']}")

        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


def test_return_float(allocation_id):
    """Test float return endpoint"""
    print("\n=== Testing Float Return ===")

    return_data = {
        "amount_returned": 1000.00,
        "return_date": date.today().isoformat(),
        "notes": "End of day float return - test"
    }

    try:
        response = requests.put(
            f"{BASE_URL}/float-allocations/{allocation_id}/return",
            json=return_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 200:
            print("✅ Float return recorded successfully!")
            result = response.json()
            print(f"   Allocation ID: {result['id']}")
            print(f"   Total Returned: P {result['amount_returned']:,.2f}")
            print(f"   Status: {result['status']}")
            print(f"   Return Journal Entry: {result['return_journal_entry_id']}")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"   {response.text}")

    except Exception as e:
        print(f"❌ Error: {str(e)}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Cash Management API Test Suite")
    print("=" * 60)
    print("\nNOTE: You need to update USER_ID_HERE with actual user IDs")
    print("      from your database before running these tests.")
    print("\nMake sure the FastAPI server is running on http://localhost:8010")

    # Test getting existing records (should work even without creating new ones)
    test_get_cash_submissions()
    test_get_float_allocations()

    # Uncomment these after updating the user IDs:
    # submission_id = test_cash_submission()
    # allocation_id = test_float_allocation()
    # if allocation_id:
    #     test_return_float(allocation_id)

    print("\n" + "=" * 60)
    print("✅ API Endpoints Available:")
    print("   POST   /api/v1/sales/cash-submissions")
    print("   GET    /api/v1/sales/cash-submissions")
    print("   POST   /api/v1/sales/float-allocations")
    print("   GET    /api/v1/sales/float-allocations")
    print("   PUT    /api/v1/sales/float-allocations/{id}/return")
    print("=" * 60)


if __name__ == "__main__":
    main()
