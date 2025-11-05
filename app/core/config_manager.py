from typing import Dict, Any, Optional
from datetime import datetime
import os
from pydantic import BaseModel

class APIResponseConfig(BaseModel):
    """Configuration for API response standardization"""
    success_format: str = "unified"
    include_timestamp: bool = True
    include_meta: bool = True
    error_detail_level: str = "detailed"

class DatabaseConfig(BaseModel):
    """Configuration for database standardization"""
    id_field_type: str = "uuid"
    timestamp_format: str = "iso8601"
    currency_precision: int = 2
    audit_trail_enabled: bool = True

class UIConfig(BaseModel):
    """Configuration for UI consistency"""
    date_format: str = "YYYY-MM-DD"
    currency_symbol: str = "P"
    page_size: int = 25
    error_display_duration: int = 5000

class ConfigManager:
    """Centralized configuration management for CNPERP system"""
    
    # Core System Settings
    API_VERSION = "v1"
    BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8010")
    DATABASE_VERSION = "1.0.0"
    SYSTEM_NAME = "CNPERP ERP"
    
    # Component Configurations
    api_response = APIResponseConfig()
    database = DatabaseConfig()
    ui = UIConfig()
    
    # API Endpoints Mapping
    ENDPOINTS = {
        "auth": "/auth",
        "purchases": "/purchases",
        "banking": "/banking", 
        "accounting": "/accounting",
        "accounting_codes": "/accounting-codes",
        "assets": "/asset-management",
        "inventory": "/inventory",
        "sales": "/sales",
        "reports": "/reports"
    }
    
    @classmethod
    def get_api_url(cls, endpoint: str) -> str:
        """Get full API URL for an endpoint"""
        base = cls.ENDPOINTS.get(endpoint, "")
        return f"{cls.BASE_URL}/api/{cls.API_VERSION}{base}"
    
    @classmethod
    def get_frontend_config(cls) -> Dict[str, Any]:
        """Get configuration for frontend JavaScript"""
        return {
            "API_BASE": f"{cls.BASE_URL}/api/{cls.API_VERSION}",
            "ENDPOINTS": cls.ENDPOINTS,
            "UI": cls.ui.dict(),
            "SYSTEM_NAME": cls.SYSTEM_NAME
        }
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """Get database configuration"""
        return cls.database.dict()

config_manager = ConfigManager()