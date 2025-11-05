from typing import Any, Dict, List, Optional, Union
from datetime import datetime
from fastapi import HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

class UnifiedResponse:
    """Unified API response wrapper for consistent response formats across all modules"""
    
    @staticmethod
    def success(
        data: Union[Dict, List, Any] = None,
        message: Optional[str] = None,
        meta: Optional[Dict] = None,
        status_code: int = 200
    ) -> Dict[str, Any]:
        """Create standardized success response"""
        response = {
            "success": True,
            "data": data,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if message:
            response["message"] = message
            
        if meta:
            response["meta"] = meta
        elif isinstance(data, list):
            response["meta"] = {
                "total": len(data),
                "count": len(data)
            }
            
        return response
    
    @staticmethod
    def error(
        message: str,
        code: str = "GENERAL_ERROR",
        details: Optional[str] = None,
        field_errors: Optional[Dict] = None,
        status_code: int = 400
    ) -> HTTPException:
        """Create standardized error response"""
        error_data = {
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or message
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if field_errors:
            error_data["error"]["field_errors"] = field_errors
            
        logger.error(f"API Error: {code} - {message}")
        return HTTPException(status_code=status_code, detail=error_data)
    
    @staticmethod
    def paginated(
        data: List[Any],
        total: int,
        page: int = 1,
        per_page: int = 25,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create paginated response"""
        meta = {
            "total": total,
            "count": len(data),
            "page": page,
            "per_page": per_page,
            "pages": (total + per_page - 1) // per_page,
            "has_next": page * per_page < total,
            "has_prev": page > 1
        }
        
        return UnifiedResponse.success(
            data=data,
            message=message,
            meta=meta
        )

def standardize_response(func):
    """Decorator to automatically wrap responses in unified format"""
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            
            # If already a proper response, return as-is
            if isinstance(result, dict) and "success" in result:
                return result
                
            # If it's a list or dict, wrap it
            return UnifiedResponse.success(data=result)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}")
            raise UnifiedResponse.error(
                message="An unexpected error occurred",
                code="INTERNAL_ERROR",
                details=str(e),
                status_code=500
            )
    return wrapper