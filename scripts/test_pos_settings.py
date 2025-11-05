"""Test POS settings endpoints"""
import requests
import json

BASE_URL = "http://localhost:8010/api/v1"

def test_get_global_default():
    """Test GET global default card bank"""
    url = f"{BASE_URL}/pos/defaults/card-bank"
    print(f"\n1. Testing GET {url}")
    try:
        response = requests.get(url)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

def test_get_branches():
    """Test GET branches"""
    url = f"{BASE_URL}/branches/"
    print(f"\n2. Testing GET {url}")
    try:
        response = requests.get(url)
        print(f"   Status: {response.status_code}")
        branches = response.json()
        print(f"   Found {len(branches)} branches")
        if branches:
            print(f"   First branch: {branches[0].get('name')} (ID: {branches[0].get('id')})")
            return branches[0].get('id')
        return None
    except Exception as e:
        print(f"   ERROR: {e}")
        return None

def test_get_bank_accounts(branch_id):
    """Test GET bank accounts for branch"""
    url = f"{BASE_URL}/banking/accounts?branch_id={branch_id}"
    print(f"\n3. Testing GET {url}")
    try:
        response = requests.get(url)
        print(f"   Status: {response.status_code}")
        result = response.json()
        accounts = result.get('data', result.get('value', []))
        print(f"   Found {len(accounts)} bank accounts")
        if accounts:
            print(f"   First account: {accounts[0].get('name')} (ID: {accounts[0].get('id')})")
            return accounts[0].get('id')
        return None
    except Exception as e:
        print(f"   ERROR: {e}")
        return None

def test_set_global_default(bank_account_id):
    """Test POST global default card bank"""
    url = f"{BASE_URL}/pos/defaults/card-bank"
    print(f"\n4. Testing POST {url}")
    try:
        payload = {"bank_account_id": bank_account_id}
        response = requests.post(url, json=payload)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

def test_get_branch_default(branch_id):
    """Test GET branch default card bank"""
    url = f"{BASE_URL}/pos/branch-defaults/{branch_id}/card-bank"
    print(f"\n5. Testing GET {url}")
    try:
        response = requests.get(url)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

def test_set_branch_default(branch_id, bank_account_id):
    """Test POST branch default card bank"""
    url = f"{BASE_URL}/pos/branch-defaults/{branch_id}/card-bank"
    print(f"\n6. Testing POST {url}")
    try:
        payload = {"bank_account_id": bank_account_id}
        response = requests.post(url, json=payload)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

def test_clear_branch_default(branch_id):
    """Test DELETE branch default card bank"""
    url = f"{BASE_URL}/pos/branch-defaults/{branch_id}/card-bank"
    print(f"\n7. Testing DELETE {url}")
    try:
        response = requests.delete(url)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

if __name__ == "__main__":
    print("="*60)
    print("POS SETTINGS API ENDPOINT TESTS")
    print("="*60)

    # Test 1: Get global default
    test_get_global_default()

    # Test 2: Get branches
    branch_id = test_get_branches()

    if branch_id:
        # Test 3: Get bank accounts
        bank_account_id = test_get_bank_accounts(branch_id)

        if bank_account_id:
            # Test 4: Set global default
            test_set_global_default(bank_account_id)

            # Test 5: Get branch default (should be empty initially)
            test_get_branch_default(branch_id)

            # Test 6: Set branch default
            test_set_branch_default(branch_id, bank_account_id)

            # Test 7: Clear branch default
            test_clear_branch_default(branch_id)
        else:
            print("\n⚠️  No bank accounts found - cannot continue tests")
    else:
        print("\n⚠️  No branches found - cannot continue tests")

    print("\n" + "="*60)
    print("TESTS COMPLETE")
    print("="*60)
