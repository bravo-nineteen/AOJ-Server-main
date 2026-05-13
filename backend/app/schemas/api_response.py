"""Standardized API response models for consistent error handling."""

from typing import Generic, TypeVar, Optional, Any
from pydantic import BaseModel, Field

T = TypeVar('T')


class APIError(BaseModel):
    """Standardized error response structure."""
    code: str = Field(..., description="Error code (e.g., 'VALIDATION_ERROR', 'NOT_FOUND')")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[dict[str, Any]] = Field(None, description="Additional error context")
    request_id: Optional[str] = Field(None, description="Request ID for tracing")


class APIResponse(BaseModel, Generic[T]):
    """Standardized API response wrapper for all endpoints."""
    success: bool = Field(..., description="Whether the request succeeded")
    data: Optional[T] = Field(None, description="Response payload (present on success)")
    error: Optional[APIError] = Field(None, description="Error details (present on failure)")
    meta: Optional[dict[str, Any]] = Field(None, description="Metadata (pagination, timing, etc)")

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "success": True,
                    "data": {"id": 1, "name": "Example"},
                    "error": None,
                    "meta": {"request_id": "abc123"}
                },
                {
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Mission not found",
                        "details": {"mission_id": 999},
                        "request_id": "abc123"
                    },
                    "meta": None
                }
            ]
        }


def success_response(
    data: Any,
    meta: Optional[dict[str, Any]] = None,
    request_id: Optional[str] = None
) -> dict:
    """Create a successful API response.
    
    Args:
        data: Response payload
        meta: Optional metadata (pagination, timing, etc)
        request_id: Optional request ID for tracing
    
    Returns:
        APIResponse dict
    """
    meta = meta or {}
    if request_id:
        meta["request_id"] = request_id
    return {
        "success": True,
        "data": data,
        "error": None,
        "meta": meta if meta else None
    }


def error_response(
    code: str,
    message: str,
    details: Optional[dict] = None,
    request_id: Optional[str] = None,
    status_code: int = 400
) -> tuple[dict, int]:
    """Create an error API response.
    
    Args:
        code: Error code
        message: Human-readable error message
        details: Optional error context
        request_id: Optional request ID for tracing
        status_code: HTTP status code
    
    Returns:
        Tuple of (response dict, HTTP status code)
    """
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details,
            "request_id": request_id
        },
        "meta": None
    }, status_code


# Common error codes
class ErrorCode:
    """Standard error codes used throughout the API."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    CONFLICT = "CONFLICT"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INVALID_STATE = "INVALID_STATE"
    LORA_TIMEOUT = "LORA_TIMEOUT"
    LORA_UNREACHABLE = "LORA_UNREACHABLE"
