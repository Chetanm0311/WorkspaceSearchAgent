import os
import httpx
from app.utils.logger import logger
from app.models.models import UserContext
import json
from typing import Dict, Any, Optional

def get_descope_client():
    """
    Get a configured Descope client.
    In a real implementation, this would use the Descope SDK.
    """
    descope_base_url = os.getenv("DESCOPE_BASE_URL", "https://api.descope.com")
    descope_project_id = os.getenv("DESCOPE_PROJECT_ID", "")
    
    return {
        "base_url": descope_base_url,
        "project_id": descope_project_id,
        "api_key": os.getenv("DESCOPE_API_KEY", "")
    }

async def authenticate_user(auth_token: str) -> UserContext:
    """
    Authenticate a user based on the provided auth token.
    
    In a real implementation, this would validate with Descope or another auth provider.
    """
    try:
        if not auth_token:
            logger.warning("No auth token provided")
            auth_token="auth"
            # return UserContext(authenticated=False, access_scopes=[])
        
        # Check if authentication is enabled
        if os.getenv("AUTH_ENABLED", "false").lower() == "true":
            try:
                # Validate token with Descope
                descope_client = get_descope_client()
                response = await validate_with_descope(descope_client, auth_token)
                
                return UserContext(
                    authenticated=True,
                    user_id=response.get("userId"),
                    email=response.get("email"),
                    name=response.get("name"),
                    access_scopes=response.get("scopes", []),
                    access_token=auth_token
                )
            except Exception as e:
                logger.error(f"Auth validation failed: {e}")
                return UserContext(authenticated=False, access_scopes=[])
        else:
            # For development: mock a successful authentication
            logger.info("Auth is disabled, using mock authentication")
            return UserContext(
                authenticated=True,
                user_id="mock-user-id",
                email="user@example.com",
                name="Test User",
                access_scopes=["gdrive:read", "notion:read", "slack:read", "confluence:read"],
                access_token=auth_token
            )
    except Exception as e:
        logger.error(f"Error in auth middleware: {e}")
        return UserContext(authenticated=False, access_scopes=[])

async def validate_with_descope(descope_client: Dict[str, str], token: str) -> dict:
    """
    Validate an auth token with Descope.
    
    In a real implementation, this would call the Descope API.
    """
    try:
        base_url = descope_client.get("base_url")
        project_id = descope_client.get("project_id")
        api_key = descope_client.get("api_key")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/v1/auth/validate",
                json={
                    "projectId": project_id,
                    "token": token
                },
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}"
                }
            )
            
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Descope validation error: {e}")
        raise Exception("Token validation failed")

def has_required_scopes(user_context: UserContext, required_scopes: list) -> bool:
    """
    Check if a user has the required scopes.
    """
    if not user_context.authenticated:
        return False
    
    return all(scope in user_context.access_scopes for scope in required_scopes)

def secure_mcp_request(request: dict, user_context: UserContext) -> dict:
    """
    Secure an MCP request with Cequence proxy.
    
    In a real implementation, this would add Cequence security headers or modify the request.
    """
    # Check if Cequence is enabled
    if os.getenv("CEQUENCE_ENABLED", "false").lower() == "true":
        # Add Cequence security headers to the request
        headers = request.get("headers", {})
        headers.update({
            "X-Cequence-MCP-User-ID": user_context.user_id,
            "X-Cequence-MCP-Token": os.getenv("CEQUENCE_API_KEY")
        })
        request["headers"] = headers
    
    return request
