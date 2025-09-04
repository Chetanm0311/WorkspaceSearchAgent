"""
Descope authentication integration for Google Drive MCP Server
"""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from descope import AuthException, DescopeClient
from fastapi import HTTPException, status
from pydantic import BaseModel

from ..models.models import UserContext
from ..utils.logger import logger


class DescopeUser(BaseModel):
    """Descope user model"""
    user_id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    verified_email: bool = False
    custom_attributes: list[str] = []
    permissions: list[str] = []
    roles: list[str] = []


class DescopeAuthenticator:
    """Handles authentication using Descope"""
    
    def __init__(self):
        self.project_id = os.getenv("DESCOPE_PROJECT_ID")
        self.management_key = os.getenv("DESCOPE_MANAGEMENT_KEY")
        
        if not self.project_id:
            logger.warning("DESCOPE_PROJECT_ID not set - Descope authentication disabled")
            self.enabled = False
            self.client = None
        else:
            self.enabled = True
            try:
                self.client = DescopeClient(
                    project_id=self.project_id,
                    management_key=self.management_key
                )
                logger.info("Descope authentication initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Descope client: {e}")
                self.enabled = False
                self.client = None
    
    async def verify_token(self, token: str) -> Optional[DescopeUser]:
        """Verify a Descope JWT token and return user info"""
        if not self.enabled or not self.client:
            logger.warning("Descope not enabled - skipping token verification")
            return None
        
        try:
            # Verify the JWT token
            jwt_response = self.client.validate_session(token)
            print(jwt_response)
            if not jwt_response:
                logger.warning("Invalid Descope JWT token")
                return None
            
            # Extract user information from the JWT claims
            claims = jwt_response.get("sessionToken")
            
            user = DescopeUser(
                user_id=claims.get("sub", ""),
                email=claims.get("email", ""),
                name=claims.get("name"),
                picture=claims.get("picture"),
                verified_email=claims.get("email_verified", False),
                custom_attributes=claims.get("custom_attributes", []),
                permissions=claims.get("permissions", []),
                roles=claims.get("roles", [])
            )
            
            logger.info(f"Successfully verified Descope token for user: {user.email}")
            return user
            
        except AuthException as e:
            logger.warning(f"Descope authentication failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error verifying Descope token: {e}")
            return None
    
    async def authenticate_request(self, authorization_header: Optional[str]) -> UserContext:
        """Authenticate a request and return user context"""
        
        # Check if we have an authorization header
        if not authorization_header:
            # Return anonymous user context
            return UserContext(
                user_id="anonymous",
                email="anonymous@example.com",
                access_token=None
            )
        
        # Extract Bearer token
        if not authorization_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format"
            )
        
        token = authorization_header[7:]  # Remove "Bearer " prefix
        
        # Verify token with Descope
        descope_user = await self.verify_token(token)
        
        if not descope_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
        
        # Check if user has required permissions for Google Drive access
        if not self._has_google_drive_permission(descope_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for Google Drive access"
            )
        
        # Create user context
        user_context = UserContext(
            user_id=descope_user.user_id,
            email=descope_user.email,
            access_token=token,
            metadata={
                "name": descope_user.name,
                "picture": descope_user.picture,
                "verified_email": descope_user.verified_email,
                "permissions": descope_user.permissions,
                "roles": descope_user.roles,
                "custom_attributes": descope_user.custom_attributes
            }
        )
        
        logger.info(f"Authenticated user: {user_context.email}")
        return user_context
    
    def _has_google_drive_permission(self, user: DescopeUser) -> bool:
        """Check if user has permission to access Google Drive"""
        required_permissions = os.getenv("REQUIRED_PERMISSIONS", "google-drive:read").split(",")
        required_roles = os.getenv("REQUIRED_ROLES", "").split(",")
        
        # Check permissions
        if required_permissions and required_permissions != [""]:
            for permission in required_permissions:
                if permission.strip() in user.permissions:
                    return True
        
        # Check roles
        if required_roles and required_roles != [""]:
            for role in required_roles:
                if role.strip() in user.roles:
                    return True
        
        # If no specific permissions/roles required, allow all verified users
        if not required_permissions and not required_roles:
            return user.verified_email
        
        return False
    
    async def generate_magic_link(self, email: str, redirect_url: str) -> Optional[str]:
        """Generate a magic link for passwordless authentication"""
        if not self.enabled or not self.client:
            return None
        
        try:
            response = self.client.magiclink.sign_in_or_up(
                email=email,
                redirect_url=redirect_url
            )
            logger.info(f"Generated magic link for {email}")
            return response.link_id
        except Exception as e:
            logger.error(f"Failed to generate magic link: {e}")
            return None
    
    async def create_user(self, email: str, name: Optional[str] = None) -> Optional[DescopeUser]:
        """Create a new user in Descope"""
        if not self.enabled or not self.client:
            return None
        
        try:
            user_request = {
                "email": email,
                "verified_email": False
            }
            if name:
                user_request["name"] = name
            
            response = self.client.mgmt.user.create(**user_request)
            
            user = DescopeUser(
                user_id=response["user"]["userId"],
                email=response["user"]["email"],
                name=response["user"].get("name"),
                verified_email=response["user"].get("verifiedEmail", False)
            )
            
            logger.info(f"Created new user: {email}")
            return user
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None
    
    async def get_user_info(self, user_id: str) -> Optional[DescopeUser]:
        """Get user information by user ID"""
        if not self.enabled or not self.client:
            return None
        
        try:
            response = self.client.mgmt.user.load(user_id)
            
            user = DescopeUser(
                user_id=response["userId"],
                email=response["email"],
                name=response.get("name"),
                picture=response.get("picture"),
                verified_email=response.get("verifiedEmail", False),
                custom_attributes=response.get("customAttributes", {}),
                permissions=response.get("permissions", []),
                roles=response.get("roles", [])
            )
            
            return user
            
        except Exception as e:
            logger.error(f"Failed to get user info: {e}")
            return None

    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user with email and password"""
        if not self.enabled or not self.client:
            logger.warning("Descope not enabled - using mock authentication")
            # Return mock result for development
            return {
                "token": f"mock_token_{datetime.now().timestamp()}",
                "user": {
                    "email": email,
                    "name": "Mock User",
                    "user_id": "mock_user"
                },
                "expires_in": 3600
            }
        
        try:
            # Authenticate with Descope
            response = self.client.password.sign_in(
                login_id=email,
                password=password
            )
            print(response)
            if response.get('sessionToken').get("email") != email:
                raise AuthException("Authentication failed")
            
            user_info = {
                "email": response.get("sessionToken").get("email", email),
                "name": response.get("sessionToken").get("name", ""),
                "user_id": response.get("sessionToken").get("userId", ""),
                "verified_email": response.get("sessionToken").get("verifiedEmail", False)
            }
            
            result = {
                "token": response.get("sessionToken").get("jwt"),
                "user": user_info,
                "expires_in": 3600,  # 1 hour
                "refresh_token": response.get("refreshSessionToken").get("jwt")
            }
            
            logger.info(f"Successfully authenticated user: {email}")
            return result
            
        except AuthException as e:
            logger.warning(f"Descope authentication failed for {email}: {e}")
            raise Exception(f"Authentication failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error authenticating user {email}: {e}")
            raise Exception(f"Authentication error: {str(e)}")


# Global authenticator instance
authenticator = DescopeAuthenticator()
