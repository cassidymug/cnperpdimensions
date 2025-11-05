#!/usr/bin/env python3
"""
Setup Dimensional Accounting - Cost Centers and Projects

This script creates initial Cost Centers and Projects for the dimensional accounting system.
Run this after the system is set up to populate basic dimensional data.
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
API_BASE_URL = "http://localhost:8010/api/v1"
HEADERS = {"Content-Type": "application/json"}

def create_dimension(dimension_data):
    """Create a new dimension"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/accounting/dimensions",
            headers=HEADERS,
            json=dimension_data
        )
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Created dimension: {dimension_data['name']} (ID: {data['id']})")
            return data['id']
        else:
            print(f"❌ Failed to create dimension {dimension_data['name']}: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error creating dimension {dimension_data['name']}: {str(e)}")
        return None

def create_dimension_value(dimension_id, value_data):
    """Create a new dimension value"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/accounting/dimensions/{dimension_id}/values",
            headers=HEADERS,
            json=value_data
        )
        if response.status_code == 201:
            data = response.json()
            print(f"  ✅ Created value: {value_data['name']} ({value_data['code']})")
            return data['id']
        else:
            print(f"  ❌ Failed to create value {value_data['name']}: {response.text}")
            return None
    except Exception as e:
        print(f"  ❌ Error creating value {value_data['name']}: {str(e)}")
        return None

def setup_cost_centers():
    """Set up Cost Centers dimension and values"""
    print("\n🏢 Setting up Cost Centers...")

    # Create Cost Center dimension
    cost_center_dimension = {
        "code": "COST_CENTER",
        "name": "Cost Centers",
        "description": "Organizational cost centers for expense tracking and analysis",
        "dimension_type": "functional",
        "scope": "global",
        "is_active": True,
        "is_required": False,
        "supports_hierarchy": True,
        "max_hierarchy_levels": 3,
        "display_order": 1
    }

    dimension_id = create_dimension(cost_center_dimension)
    if not dimension_id:
        return None

    # Create Cost Center values
    cost_centers = [
        {
            "code": "ADMIN",
            "name": "Administration",
            "description": "General administrative expenses and overhead",
            "display_order": 1
        },
        {
            "code": "SALES",
            "name": "Sales Department",
            "description": "Sales activities and customer acquisition",
            "display_order": 2
        },
        {
            "code": "MARKETING",
            "name": "Marketing",
            "description": "Marketing campaigns and brand promotion",
            "display_order": 3
        },
        {
            "code": "IT",
            "name": "Information Technology",
            "description": "IT infrastructure, software, and technical support",
            "display_order": 4
        },
        {
            "code": "HR",
            "name": "Human Resources",
            "description": "HR operations and employee-related expenses",
            "display_order": 5
        },
        {
            "code": "FINANCE",
            "name": "Finance & Accounting",
            "description": "Financial operations and accounting activities",
            "display_order": 6
        },
        {
            "code": "OPERATIONS",
            "name": "Operations",
            "description": "Day-to-day operational activities",
            "display_order": 7
        },
        {
            "code": "R&D",
            "name": "Research & Development",
            "description": "Research and product development activities",
            "display_order": 8
        }
    ]

    for cost_center in cost_centers:
        create_dimension_value(dimension_id, cost_center)

    return dimension_id

def setup_projects():
    """Set up Projects dimension and values"""
    print("\n📊 Setting up Projects...")

    # Create Project dimension
    project_dimension = {
        "code": "PROJECT",
        "name": "Projects",
        "description": "Business projects for revenue and expense tracking across initiatives",
        "dimension_type": "project",
        "scope": "global",
        "is_active": True,
        "is_required": False,
        "supports_hierarchy": True,
        "max_hierarchy_levels": 2,
        "display_order": 2
    }

    dimension_id = create_dimension(project_dimension)
    if not dimension_id:
        return None

    # Create Project values
    projects = [
        {
            "code": "WEBSITE2024",
            "name": "Website Redesign 2024",
            "description": "Complete website overhaul and modernization project",
            "display_order": 1
        },
        {
            "code": "ERP2024",
            "name": "ERP Implementation",
            "description": "Enterprise resource planning system deployment",
            "display_order": 2
        },
        {
            "code": "EXPANSION2024",
            "name": "Market Expansion",
            "description": "Expansion into new geographical markets",
            "display_order": 3
        },
        {
            "code": "TRAINING2024",
            "name": "Staff Training Program",
            "description": "Comprehensive employee training and development initiative",
            "display_order": 4
        },
        {
            "code": "DIGITAL2024",
            "name": "Digital Transformation",
            "description": "Company-wide digital transformation initiative",
            "display_order": 5
        },
        {
            "code": "QUALITY2024",
            "name": "Quality Improvement",
            "description": "Process quality improvement and optimization project",
            "display_order": 6
        },
        {
            "code": "CUSTOMER2024",
            "name": "Customer Experience Enhancement",
            "description": "Improving customer service and experience across touchpoints",
            "display_order": 7
        },
        {
            "code": "GENERAL",
            "name": "General Operations",
            "description": "Non-project specific operational activities",
            "display_order": 8
        }
    ]

    for project in projects:
        create_dimension_value(dimension_id, project)

    return dimension_id

def main():
    """Main setup function"""
    print("🚀 CNPERP Dimensional Accounting Setup")
    print("=====================================")
    print(f"Setting up Cost Centers and Projects at {datetime.now()}")

    try:
        # Test API connectivity
        response = requests.get(f"{API_BASE_URL}/accounting/dimensions")
        if response.status_code != 200:
            print(f"❌ Cannot connect to API at {API_BASE_URL}")
            print("Please ensure the FastAPI server is running on port 8010")
            sys.exit(1)

        print("✅ API connection successful")

        # Setup dimensions
        cost_center_id = setup_cost_centers()
        project_id = setup_projects()

        print("\n🎉 Setup Complete!")
        print("==================")

        if cost_center_id:
            print(f"✅ Cost Centers dimension created (ID: {cost_center_id})")
        if project_id:
            print(f"✅ Projects dimension created (ID: {project_id})")

        print("\n📝 Next Steps:")
        print("1. Visit http://localhost:8010/static/purchases.html to test dimensional purchasing")
        print("2. Visit http://localhost:8010/static/accounting-codes.html to manage dimensions")
        print("3. Check the dimensional reports at /frontend/dimensional-reports.html")

    except KeyboardInterrupt:
        print("\n❌ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
