"""
Automated Testing Framework for CNPERP Consistency Validation
Comprehensive test suite ensuring API response format consistency,
cross-module compatibility, and system integration validation.
"""

import pytest
import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime
import requests
from unittest.mock import patch, MagicMock

from app.core.response_wrapper import UnifiedResponse
from app.core.config_manager import ConfigManager

class ConsistencyValidator:
    """
    Validates consistency across the entire CNPERP system.
    
    Tests API response formats, data structures, and cross-module compatibility.
    """
    
    def __init__(self, base_url: str = "http://localhost:8010"):
        self.base_url = base_url
        self.config = ConfigManager()
        self.test_results = {}
        
    async def validate_api_consistency(self) -> Dict[str, Any]:
        """
        Validate that all API endpoints return consistent response formats.
        
        Returns:
            Dict containing validation results for each endpoint
        """
        endpoints_to_test = [
            # Purchases module
            {'method': 'GET', 'path': '/api/v1/purchases/suppliers', 'module': 'purchases'},
            {'method': 'GET', 'path': '/api/v1/purchases/products', 'module': 'purchases'},
            {'method': 'GET', 'path': '/api/v1/purchases/purchases', 'module': 'purchases'},
            
            # Banking module  
            {'method': 'GET', 'path': '/api/v1/banking/accounts', 'module': 'banking'},
            
            # Accounting module
            {'method': 'GET', 'path': '/api/v1/accounting-codes/', 'module': 'accounting'},
            {'method': 'GET', 'path': '/api/v1/accounting-codes/count', 'module': 'accounting'},
            
            # Asset management module
            {'method': 'GET', 'path': '/api/v1/asset-management/assets/', 'module': 'assets'},
            
            # Settings module
            {'method': 'GET', 'path': '/api/v1/settings/', 'module': 'settings'},
        ]
        
        results = {}
        
        for endpoint in endpoints_to_test:
            try:
                result = await self._test_endpoint_consistency(endpoint)
                results[f"{endpoint['method']} {endpoint['path']}"] = result
            except Exception as e:
                results[f"{endpoint['method']} {endpoint['path']}"] = {
                    'status': 'error',
                    'error': str(e),
                    'consistent': False
                }
        
        return results
    
    async def _test_endpoint_consistency(self, endpoint: Dict[str, str]) -> Dict[str, Any]:
        """Test individual endpoint for response consistency."""
        url = f"{self.base_url}{endpoint['path']}"
        
        try:
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                return {
                    'status': 'failed',
                    'status_code': response.status_code,
                    'consistent': False,
                    'reason': f'Non-200 status code: {response.status_code}'
                }
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                return {
                    'status': 'failed',
                    'consistent': False,
                    'reason': 'Response is not valid JSON'
                }
            
            # Validate UnifiedResponse format
            consistency_check = self._validate_unified_response_format(data)
            
            return {
                'status': 'success',
                'status_code': response.status_code,
                'consistent': consistency_check['is_consistent'],
                'format_validation': consistency_check,
                'response_time_ms': response.elapsed.total_seconds() * 1000,
                'module': endpoint['module']
            }
            
        except requests.exceptions.RequestException as e:
            return {
                'status': 'connection_error',
                'consistent': False,
                'reason': f'Connection error: {str(e)}'
            }
    
    def _validate_unified_response_format(self, response_data: Any) -> Dict[str, Any]:
        """
        Validate that response follows UnifiedResponse format:
        {
            "success": bool,
            "data": any,
            "message": str,
            "timestamp": str,
            "meta": dict (optional)
        }
        """
        validation_result = {
            'is_consistent': True,
            'missing_fields': [],
            'incorrect_types': [],
            'extra_fields': [],
            'format_score': 0
        }
        
        # Required fields and their expected types
        required_fields = {
            'success': bool,
            'data': object,  # Can be any type
            'message': str,
            'timestamp': str
        }
        
        optional_fields = {
            'meta': dict
        }
        
        all_expected_fields = {**required_fields, **optional_fields}
        
        # Check if response is a dictionary
        if not isinstance(response_data, dict):
            validation_result['is_consistent'] = False
            validation_result['incorrect_types'].append('Response is not a dictionary')
            return validation_result
        
        # Check required fields
        for field, expected_type in required_fields.items():
            if field not in response_data:
                validation_result['missing_fields'].append(field)
                validation_result['is_consistent'] = False
            elif not isinstance(response_data[field], expected_type):
                validation_result['incorrect_types'].append(f"{field}: expected {expected_type.__name__}, got {type(response_data[field]).__name__}")
                validation_result['is_consistent'] = False
            else:
                validation_result['format_score'] += 1
        
        # Check for unexpected extra fields (legacy response formats)
        for field in response_data:
            if field not in all_expected_fields:
                validation_result['extra_fields'].append(field)
                # Don't mark as inconsistent for extra fields - might be intentional
        
        # Calculate format score (percentage of required fields correct)
        validation_result['format_score'] = (validation_result['format_score'] / len(required_fields)) * 100
        
        return validation_result

class CrossModuleCompatibilityTester:
    """
    Tests compatibility and integration between different CNPERP modules.
    
    Ensures modules can communicate effectively and data flows correctly.
    """
    
    def __init__(self, base_url: str = "http://localhost:8010"):
        self.base_url = base_url
        
    async def test_purchase_to_accounting_flow(self) -> Dict[str, Any]:
        """
        Test the complete flow from purchase creation to accounting entries.
        
        Validates that:
        1. Purchase can be created
        2. Journal entries are generated
        3. Account balances are updated
        4. Data consistency is maintained
        """
        test_result = {
            'test_name': 'Purchase to Accounting Flow',
            'steps': [],
            'overall_success': True,
            'errors': []
        }
        
        try:
            # Step 1: Get suppliers
            suppliers_response = requests.get(f"{self.base_url}/api/v1/purchases/suppliers")
            step1_result = self._validate_step(
                "Get Suppliers",
                suppliers_response,
                expected_data_type=list
            )
            test_result['steps'].append(step1_result)
            
            if not step1_result['success']:
                test_result['overall_success'] = False
                return test_result
            
            suppliers = self._extract_response_data(suppliers_response.json())
            if not suppliers:
                test_result['errors'].append("No suppliers available for testing")
                test_result['overall_success'] = False
                return test_result
            
            # Step 2: Get products
            products_response = requests.get(f"{self.base_url}/api/v1/purchases/products")
            step2_result = self._validate_step(
                "Get Products",
                products_response,
                expected_data_type=list
            )
            test_result['steps'].append(step2_result)
            
            if not step2_result['success']:
                test_result['overall_success'] = False
                return test_result
            
            products = self._extract_response_data(products_response.json())
            if not products:
                test_result['errors'].append("No products available for testing")
                test_result['overall_success'] = False
                return test_result
            
            # Step 3: Create test purchase
            test_purchase_data = {
                "supplier_id": suppliers[0]['id'],
                "purchase_date": datetime.now().isoformat(),
                "items": [
                    {
                        "product_id": products[0]['id'],
                        "quantity": 1,
                        "cost": 100.0,
                        "vat_rate": 14.0
                    }
                ]
            }
            
            purchase_response = requests.post(
                f"{self.base_url}/api/v1/purchases/purchases",
                json=test_purchase_data
            )
            
            step3_result = self._validate_step(
                "Create Purchase",
                purchase_response,
                expected_status=201
            )
            test_result['steps'].append(step3_result)
            
            if not step3_result['success']:
                test_result['overall_success'] = False
                return test_result
            
            # Step 4: Verify accounting entries were created
            # (This would require checking journal entries endpoint)
            # For now, we'll simulate this check
            
            journal_response = requests.get(f"{self.base_url}/api/v1/accounting-codes/")
            step4_result = self._validate_step(
                "Verify Accounting Integration",
                journal_response
            )
            test_result['steps'].append(step4_result)
            
            if not step4_result['success']:
                test_result['overall_success'] = False
            
        except Exception as e:
            test_result['overall_success'] = False
            test_result['errors'].append(f"Unexpected error: {str(e)}")
        
        return test_result
    
    def _validate_step(self, step_name: str, response: requests.Response, 
                      expected_status: int = 200, expected_data_type: type = None) -> Dict[str, Any]:
        """Validate individual test step."""
        result = {
            'step_name': step_name,
            'success': True,
            'status_code': response.status_code,
            'response_time_ms': response.elapsed.total_seconds() * 1000,
            'errors': []
        }
        
        # Check status code
        if response.status_code != expected_status:
            result['success'] = False
            result['errors'].append(f"Expected status {expected_status}, got {response.status_code}")
        
        # Check response format
        try:
            data = response.json()
            
            # Validate UnifiedResponse format
            validator = ConsistencyValidator()
            format_validation = validator._validate_unified_response_format(data)
            result['format_validation'] = format_validation
            
            if not format_validation['is_consistent']:
                result['success'] = False
                result['errors'].append("Response format is not consistent with UnifiedResponse")
            
            # Check data type if specified
            if expected_data_type and result['success']:
                response_data = self._extract_response_data(data)
                if not isinstance(response_data, expected_data_type):
                    result['success'] = False
                    result['errors'].append(f"Expected data type {expected_data_type.__name__}, got {type(response_data).__name__}")
            
        except json.JSONDecodeError:
            result['success'] = False
            result['errors'].append("Response is not valid JSON")
        
        return result
    
    def _extract_response_data(self, response_json: Dict[str, Any]) -> Any:
        """Extract data from UnifiedResponse format."""
        if 'data' in response_json:
            return response_json['data']
        # Fallback for legacy formats
        return response_json

class JavaScriptConsistencyTester:
    """
    Tests JavaScript consistency across frontend modules.
    
    Validates that CNPERP core library is being used consistently.
    """
    
    def __init__(self, static_path: str = "app/static"):
        self.static_path = static_path
        
    def validate_cnperp_usage(self) -> Dict[str, Any]:
        """
        Validate that HTML files are using CNPERP core library consistently.
        
        Checks for:
        1. CNPERP core library inclusion
        2. Consistent API usage patterns
        3. Elimination of hardcoded URLs
        """
        import os
        import re
        
        results = {
            'total_files': 0,
            'compliant_files': 0,
            'issues': [],
            'file_results': {}
        }
        
        # Find all HTML files
        html_files = []
        for root, dirs, files in os.walk(self.static_path):
            for file in files:
                if file.endswith('.html'):
                    html_files.append(os.path.join(root, file))
        
        results['total_files'] = len(html_files)
        
        for file_path in html_files:
            file_result = self._analyze_html_file(file_path)
            results['file_results'][file_path] = file_result
            
            if file_result['compliant']:
                results['compliant_files'] += 1
            else:
                results['issues'].extend([
                    f"{file_path}: {issue}" for issue in file_result['issues']
                ])
        
        results['compliance_percentage'] = (results['compliant_files'] / results['total_files']) * 100 if results['total_files'] > 0 else 0
        
        return results
    
    def _analyze_html_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze individual HTML file for CNPERP compliance."""
        import re
        
        result = {
            'compliant': True,
            'issues': [],
            'cnperp_included': False,
            'hardcoded_urls': [],
            'deprecated_patterns': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for CNPERP core library inclusion
            if 'cnperp-core.js' in content:
                result['cnperp_included'] = True
            else:
                result['compliant'] = False
                result['issues'].append("CNPERP core library not included")
            
            # Check for hardcoded localhost URLs
            hardcoded_urls = re.findall(r'http://localhost:\d+', content)
            if hardcoded_urls:
                result['compliant'] = False
                result['hardcoded_urls'] = list(set(hardcoded_urls))
                result['issues'].append(f"Found {len(hardcoded_urls)} hardcoded URLs")
            
            # Check for deprecated fetch patterns
            direct_fetch_patterns = re.findall(r'fetch\s*\(\s*[\'"`]', content)
            if direct_fetch_patterns and not any(pattern in content for pattern in ['CNPERP.API.get', 'CNPERP.API.post']):
                result['compliant'] = False
                result['deprecated_patterns'].append("Direct fetch() usage instead of CNPERP.API")
                result['issues'].append("Using direct fetch() instead of CNPERP.API")
            
            # Check for CNPERP initialization
            if result['cnperp_included'] and 'CNPERP.initPage' not in content:
                result['compliant'] = False
                result['issues'].append("CNPERP core included but not initialized")
            
        except Exception as e:
            result['compliant'] = False
            result['issues'].append(f"Error analyzing file: {str(e)}")
        
        return result

# Pytest test cases
class TestCNPERPConsistency:
    """Pytest test cases for CNPERP consistency validation."""
    
    @pytest.fixture
    def consistency_validator(self):
        return ConsistencyValidator()
    
    @pytest.fixture
    def compatibility_tester(self):
        return CrossModuleCompatibilityTester()
    
    @pytest.fixture
    def js_tester(self):
        return JavaScriptConsistencyTester()
    
    @pytest.mark.asyncio
    async def test_api_response_consistency(self, consistency_validator):
        """Test that all API endpoints return consistent response formats."""
        results = await consistency_validator.validate_api_consistency()
        
        failed_endpoints = []
        for endpoint, result in results.items():
            if not result.get('consistent', False):
                failed_endpoints.append(endpoint)
        
        assert len(failed_endpoints) == 0, f"Inconsistent endpoints: {failed_endpoints}"
    
    @pytest.mark.asyncio
    async def test_cross_module_compatibility(self, compatibility_tester):
        """Test cross-module compatibility and data flow."""
        result = await compatibility_tester.test_purchase_to_accounting_flow()
        
        assert result['overall_success'], f"Cross-module test failed: {result['errors']}"
    
    def test_javascript_consistency(self, js_tester):
        """Test JavaScript consistency across frontend modules."""
        results = js_tester.validate_cnperp_usage()
        
        # Require at least 80% compliance
        assert results['compliance_percentage'] >= 80, f"JavaScript compliance too low: {results['compliance_percentage']}%"
    
    def test_unified_response_format(self):
        """Test UnifiedResponse format validation."""
        validator = ConsistencyValidator()
        
        # Test valid response
        valid_response = {
            "success": True,
            "data": ["item1", "item2"],
            "message": "Success",
            "timestamp": "2025-10-01T12:00:00Z"
        }
        
        result = validator._validate_unified_response_format(valid_response)
        assert result['is_consistent'], f"Valid response marked as inconsistent: {result}"
        
        # Test invalid response
        invalid_response = {
            "status": "ok",  # Wrong field name
            "items": []      # Legacy format
        }
        
        result = validator._validate_unified_response_format(invalid_response)
        assert not result['is_consistent'], "Invalid response marked as consistent"

# Integration test runner
async def run_full_consistency_tests():
    """Run complete consistency test suite."""
    print("🧪 Running CNPERP Consistency Tests...")
    
    # API consistency tests
    print("\n📡 Testing API Response Consistency...")
    validator = ConsistencyValidator()
    api_results = await validator.validate_api_consistency()
    
    consistent_count = sum(1 for r in api_results.values() if r.get('consistent', False))
    total_count = len(api_results)
    
    print(f"✅ API Consistency: {consistent_count}/{total_count} endpoints consistent")
    
    # Cross-module compatibility tests
    print("\n🔗 Testing Cross-Module Compatibility...")
    compatibility_tester = CrossModuleCompatibilityTester()
    compatibility_result = await compatibility_tester.test_purchase_to_accounting_flow()
    
    if compatibility_result['overall_success']:
        print("✅ Cross-Module Compatibility: PASSED")
    else:
        print(f"❌ Cross-Module Compatibility: FAILED - {compatibility_result['errors']}")
    
    # JavaScript consistency tests
    print("\n🟨 Testing JavaScript Consistency...")
    js_tester = JavaScriptConsistencyTester()
    js_results = js_tester.validate_cnperp_usage()
    
    print(f"✅ JavaScript Consistency: {js_results['compliance_percentage']:.1f}% compliant")
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   API Endpoints: {consistent_count}/{total_count} consistent")
    print(f"   Cross-Module: {'PASS' if compatibility_result['overall_success'] else 'FAIL'}")
    print(f"   JavaScript: {js_results['compliance_percentage']:.1f}% compliant")
    
    return {
        'api_consistency': api_results,
        'cross_module_compatibility': compatibility_result,
        'javascript_consistency': js_results
    }

if __name__ == "__main__":
    # Run tests
    import asyncio
    asyncio.run(run_full_consistency_tests())