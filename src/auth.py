import os
from fastapi import Header, HTTPException, status
from src.config import settings

class AuthenticationError(HTTPException):
    def __init__(self, detail: str = "Invalid API key"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "message": detail,
                    "type": "invalid_request_error",
                    "param": None,
                    "code": "invalid_api_key",
                }
            },
        )

async def verify_api_key(authorization: str = Header(None)) -> None:
    expected_key = settings.API_KEY
    if not expected_key:
        return
    if not authorization:
        raise AuthenticationError("Missing Authorization header.")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AuthenticationError("Invalid Authorization format. Expected 'Bearer <key>'.")
    if parts[1] != expected_key:
        raise AuthenticationError("Invalid or unauthorized API key.")
