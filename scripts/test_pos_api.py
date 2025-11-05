"""Test POS settings API endpoints"""
import requests
import json

BASE_URL = "http://localhost:8010/api/v1"

def test_endpoints():
    print("=" * 60)
    print("Testing POS Settings API Endpoints")
    print("=" * 60)

    # Test 1: Get branches
    print("\n1. GET /branches/")
    try:
        r = requests.get(f"{BASE_URL}/branches/")
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            branches = r.json()
            print(f"   Found {len(branches)} branches")
            if branches:
                print(f"   First branch: {branches[0].get('name')} (ID: {branches[0].get('id')})")
                first_branch_id = branches[0].get('id')

                # Test 2: Get bank accounts for first branch
                print(f"\n2. GET /banking/accounts?branch_id={first_branch_id}")
                r2 = requests.get(f"{BASE_URL}/banking/accounts?branch_id={first_branch_id}")
                print(f"   Status: {r2.status_code}")
                if r2.status_code == 200:
                    response_data = r2.json()
                    # Handle both list and dict responses
                    if isinstance(response_data, dict):
                        accounts = response_data.get('data', []) if 'data' in response_data else []
                    else:
                        accounts = response_data
                    print(f"   Found {len(accounts)} bank accounts for this branch")
                    if accounts and len(accounts) > 0:
                        print(f"   First account: {accounts[0].get('name')} ({accounts[0].get('account_number')})")
                        first_account_id = accounts[0].get('id')

                        # Test 3: Get global default
                        print(f"\n3. GET /pos/defaults/card-bank")
                        r3 = requests.get(f"{BASE_URL}/pos/defaults/card-bank")
                        print(f"   Status: {r3.status_code}")
                        print(f"   Response: {r3.json()}")

                        # Test 4: Set global default
                        print(f"\n4. POST /pos/defaults/card-bank")
                        r4 = requests.post(
                            f"{BASE_URL}/pos/defaults/card-bank",
                            json={"bank_account_id": first_account_id}
                        )
                        print(f"   Status: {r4.status_code}")
                        print(f"   Response: {r4.json()}")

                        # Test 5: Get branch default
                        print(f"\n5. GET /pos/branch-defaults/{first_branch_id}/card-bank")
                        r5 = requests.get(f"{BASE_URL}/pos/branch-defaults/{first_branch_id}/card-bank")
                        print(f"   Status: {r5.status_code}")
                        print(f"   Response: {r5.json()}")

                        # Test 6: Set branch default
                        print(f"\n6. POST /pos/branch-defaults/{first_branch_id}/card-bank")
                        r6 = requests.post(
                            f"{BASE_URL}/pos/branch-defaults/{first_branch_id}/card-bank",
                            json={"bank_account_id": first_account_id}
                        )
                        print(f"   Status: {r6.status_code}")
                        print(f"   Response: {r6.json()}")

                        # Test 7: Get branch default again
                        print(f"\n7. GET /pos/branch-defaults/{first_branch_id}/card-bank (after setting)")
                        r7 = requests.get(f"{BASE_URL}/pos/branch-defaults/{first_branch_id}/card-bank")
                        print(f"   Status: {r7.status_code}")
                        print(f"   Response: {r7.json()}")

    except Exception as e:
        print(f"   ERROR: {e}")

    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_endpoints()
