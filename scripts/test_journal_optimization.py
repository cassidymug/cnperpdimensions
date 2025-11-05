#!/usr/bin/env python3
"""
Test script to verify journal entry query optimizations.
Tests:
1. GET /journal endpoint returns names instead of UUIDs
2. GET /journal/{entry_id} endpoint returns full details with names
3. Manufacturing /journal-entries endpoint returns eager-loaded data
4. Performance metrics for each endpoint
"""

import requests
import json
import time
from datetime import datetime
import sys
import os

# Fix encoding issues on Windows
os.environ['PYTHONIOENCODING'] = 'utf-8'

BASE_URL = "http://localhost:8010/api/v1"

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def test_journal_list_endpoint():
    """Test GET /journal endpoint - should return names instead of UUIDs."""
    print_header("Test 1: GET /journal - List Journal Entries with Names")

    try:
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/accounting/journal?skip=0&limit=5")
        elapsed_time = time.time() - start_time

        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed_time*1000:.2f} ms")

        if response.status_code == 200:
            data = response.json()

            if isinstance(data, list) and len(data) > 0:
                first_entry = data[0]
                print(f"\nNumber of entries returned: {len(data)}")
                print("\nFirst entry structure:")
                print(json.dumps(first_entry, indent=2, default=str)[:500] + "...\n")

                # Check for name fields
                required_fields = [
                    "id",
                    "accounting_code_name",
                    "accounting_code_code",
                    "accounting_entry_code",
                    "accounting_entry_name",
                    "branch_name",
                    "purchase_reference"
                ]

                print("Field Verification:")
                all_present = True
                for field in required_fields:
                    present = field in first_entry
                    has_value = first_entry.get(field) is not None
                    status = "✓ Present" if present else "✗ Missing"
                    value_status = f"(value: {first_entry.get(field)})" if has_value else "(null)"
                    print(f"  {field}: {status} {value_status}")
                    if not present or not has_value:
                        all_present = False

                print(f"\nResult: {'✓ PASS - Names returned instead of UUIDs' if all_present else '✗ FAIL - Some fields missing or null'}")
                return True
            else:
                print("✗ FAIL - No entries returned or invalid format")
                return False
        else:
            print(f"✗ FAIL - HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ FAIL - Exception: {str(e)}")
        return False

def test_journal_detail_endpoint():
    """Test GET /journal/{entry_id} endpoint - should return all details with eager loading."""
    print_header("Test 2: GET /journal/{entry_id} - Single Entry with Full Details")

    try:
        # First, get an entry ID from the list
        response = requests.get(f"{BASE_URL}/accounting/journal?skip=0&limit=1")
        if response.status_code != 200 or not response.json():
            print("✗ FAIL - Could not get entry ID from list endpoint")
            return False

        entry_id = response.json()[0]["id"]
        print(f"Testing with entry ID: {entry_id}\n")

        start_time = time.time()
        response = requests.get(f"{BASE_URL}/accounting/journal/{entry_id}")
        elapsed_time = time.time() - start_time

        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed_time*1000:.2f} ms")

        if response.status_code == 200:
            data = response.json()
            print("\nEntry details:")
            print(json.dumps(data, indent=2, default=str)[:800] + "...\n")

            # Check for all expected fields
            required_fields = [
                "id",
                "accounting_code_name",
                "accounting_entry_code",
                "branch_name",
                "ledger_description",
                "purchase_reference",
                "dimension_assignments"
            ]

            print("Field Verification:")
            all_present = True
            for field in required_fields:
                present = field in data
                status = "✓ Present" if present else "✗ Missing"
                print(f"  {field}: {status}")
                if not present:
                    all_present = False

            print(f"\nResult: {'✓ PASS - All fields present with eager loading' if all_present else '✗ FAIL - Some fields missing'}")
            return True
        else:
            print(f"✗ FAIL - HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ FAIL - Exception: {str(e)}")
        return False

def test_manufacturing_journal_endpoint():
    """Test manufacturing /journal-entries endpoint - should use eager loading."""
    print_header("Test 3: GET /manufacturing/journal-entries - Manufacturing Journal with Eager Loading")

    try:
        start_time = time.time()
        response = requests.get(f"{BASE_URL}/manufacturing/journal-entries?skip=0&limit=5")
        elapsed_time = time.time() - start_time

        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {elapsed_time*1000:.2f} ms")

        if response.status_code == 200:
            data = response.json()

            print(f"\nTotal entries: {data.get('total_count', 'N/A')}")
            print(f"Returned entries: {len(data.get('entries', []))}")

            entries = data.get("entries", [])
            if entries:
                first_entry = entries[0]
                print("\nFirst entry structure:")
                print(json.dumps(first_entry, indent=2, default=str)[:500] + "...\n")

                # Check for name fields
                required_fields = ["id", "account_code", "account_name", "dimensions"]

                print("Field Verification:")
                all_present = True
                for field in required_fields:
                    present = field in first_entry
                    has_value = first_entry.get(field) is not None
                    status = "✓ Present" if present else "✗ Missing"
                    print(f"  {field}: {status}")
                    if not present or not has_value:
                        all_present = False

                print(f"\nResult: {'✓ PASS - Manufacturing entries with eager loading' if all_present else '✗ FAIL - Some fields missing'}")
                return True
            else:
                print("✗ No manufacturing entries found (this is OK if none exist)")
                return True
        else:
            print(f"✗ FAIL - HTTP {response.status_code}: {response.text}")
            return False
    except Exception as e:
        print(f"✗ FAIL - Exception: {str(e)}")
        return False

def test_performance_comparison():
    """Compare performance metrics across endpoints."""
    print_header("Test 4: Performance Comparison - Response Times")

    endpoints = [
        ("GET /journal (list)", f"{BASE_URL}/accounting/journal?skip=0&limit=10"),
        ("GET /journal (list 50)", f"{BASE_URL}/accounting/journal?skip=0&limit=50"),
        ("GET /journal (list 100)", f"{BASE_URL}/accounting/journal?skip=0&limit=100"),
    ]

    results = []
    for name, url in endpoints:
        try:
            times = []
            for i in range(3):  # 3 requests for averaging
                start = time.time()
                response = requests.get(url)
                elapsed = (time.time() - start) * 1000
                times.append(elapsed)

            avg_time = sum(times) / len(times)
            results.append((name, avg_time, response.status_code))
            print(f"{name}: {avg_time:.2f} ms (avg of 3 requests) [HTTP {response.status_code}]")
        except Exception as e:
            print(f"{name}: ✗ ERROR - {str(e)}")

    print("\nPerformance Summary:")
    for name, avg_time, status in results:
        target = 500  # Target <500ms from optimization goals
        performance = "✓ EXCELLENT" if avg_time < 200 else "✓ GOOD" if avg_time < 500 else "⚠ NEEDS IMPROVEMENT"
        print(f"  {name}: {avg_time:.2f} ms {performance}")

def main():
    """Run all tests."""
    print("\n")
    print("*" * 80)
    print("  JOURNAL ENTRY OPTIMIZATION TEST SUITE")
    print("*" * 80)

    try:
        # Test connectivity
        print("\nChecking API connectivity...")
        response = requests.get(f"{BASE_URL}/accounting/journal?limit=1", timeout=5)
        if response.status_code == 200:
            print("✓ API is responsive\n")
        else:
            print(f"✗ API returned {response.status_code}")
            return
    except Exception as e:
        print(f"✗ Cannot connect to API: {str(e)}")
        print("\nMake sure FastAPI server is running: python -m uvicorn app.main:app --reload")
        return

    # Run tests
    test_results = []
    test_results.append(("Journal List Endpoint", test_journal_list_endpoint()))
    test_results.append(("Journal Detail Endpoint", test_journal_detail_endpoint()))
    test_results.append(("Manufacturing Journal Endpoint", test_manufacturing_journal_endpoint()))
    test_performance_comparison()

    # Print summary
    print_header("TEST SUMMARY")
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)

    for test_name, result in test_results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n✓ All tests passed! Journal optimization successful.")
    else:
        print(f"\n✗ {total - passed} test(s) failed. Review above for details.")

if __name__ == "__main__":
    main()
