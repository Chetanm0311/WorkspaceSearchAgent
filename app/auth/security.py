"""
Security middleware combining Descope authentication and Cequence AI Gateway
"""

import os
import uuid
from typing import Optional, Callable
from datetime import datetime

from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from .descope_auth import authenticator, DescopeUser
from .cequence_gateway import gateway, SecurityEvent
from ..models.models import UserContext
from ..utils.logger import logger


class SecurityMiddleware(BaseHTTPMiddleware):
    """Security middleware for authentication and threat detection"""
    
    def __init__(self, app, skip_paths: Optional[list] = None):
        super().__init__(app)
        self.skip_paths = skip_paths or [
            "/health", "/docs", "/redoc", "/openapi.json", "/",
            "/auth/login", "/auth/signup", "/auth/callback", "/auth/user"
        ]
        self.bearer_scheme = HTTPBearer(auto_error=False)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security pipeline"""
        
        # Skip security for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)
        
        try:
            # Step 1: Cequence AI Gateway analysis
            await self._analyze_with_cequence(request)
            
            # Step 2: Descope authentication
            user_context = await self._authenticate_with_descope(request)
            
            # Add user context to request state
            request.state.user_context = user_context
            
            # Process the request
            response = await call_next(request)
            
            # Log successful request
            await self._log_successful_request(request, response, user_context)
            
            return response
            
        except HTTPException as e:
            # Log security event
            await self._log_security_event(request, e)
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            # Log unexpected error as security event
            await self._log_security_event(
                request, 
                HTTPException(status_code=500, detail="Internal security error")
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal security error"
            )
    
    async def _analyze_with_cequence(self, request: Request):
        """Analyze request with Cequence AI Gateway"""
        try:
            analysis_result = await gateway.analyze_request(request)
            
            # Store analysis results in request state
            request.state.security_analysis = analysis_result
            
            # Check if request should be blocked
            if not analysis_result.get("allowed", True):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Request blocked by security analysis"
                )
            
            # Log high-risk requests
            risk_score = analysis_result.get("risk_score", 0.0)
            if risk_score > 0.5:
                logger.warning(
                    f"High-risk request detected: {request.url.path} "
                    f"from {self._get_client_ip(request)} (risk: {risk_score})"
                )

        except Exception as e:
            logger.error(f"Cequence analysis failed: {e}")
            # Continue without blocking - fail open
            request.state.security_analysis = {"allowed": True, "risk_score": 0.0}
    
    async def _authenticate_with_descope(self, request: Request) -> UserContext:
        """Authenticate request with Descope"""
        
        # Extract authorization header
        authorization = request.headers.get("authorization")
        
        # Check if authentication is required
        if self._is_auth_required(request.url.path):
            if not authorization:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authorization header required",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Authenticate with Descope
        try:
            user_context = await authenticator.authenticate_request(authorization)
            
            # Log successful authentication
            if user_context.user_id != "anonymous":
                logger.info(f"User authenticated: {user_context.email}")
            
            return user_context
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication service error"
            )
    
    def _is_auth_required(self, path: str) -> bool:
        """Check if authentication is required for the given path"""
        # Paths that don't require authentication
        public_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/login",
            "/auth/signup",
            "/auth/callback",
            "/auth/user"
        ]
        
        # Check if authentication is globally disabled for development
        if os.getenv("DISABLE_AUTH", "false").lower() == "true":
            return False
        
        # If Descope is not configured, don't require auth
        if not authenticator.enabled:
            return False
        
        return path not in public_paths
    
    async def _log_successful_request(self, request: Request, response: Response, user_context: UserContext):
        """Log successful request for analytics"""
        if gateway.config.analytics_enabled:
            try:
                # Create a low-severity event for successful requests
                event = SecurityEvent(
                    event_id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    event_type="successful_request",
                    severity="info",
                    source_ip=self._get_client_ip(request),
                    user_agent=request.headers.get("user-agent", ""),
                    description=f"Successful {request.method} {request.url.path}",
                    risk_score=getattr(request.state, 'security_analysis', {}).get('risk_score', 0.0),
                    recommended_action="none"
                )
                
                await gateway.log_security_event(event)
                
            except Exception as e:
                logger.error(f"Failed to log successful request: {e}")
    
    async def _log_security_event(self, request: Request, exception: HTTPException):
        """Log security event for failed requests"""
        try:
            # Determine severity based on status code
            severity = "low"
            if exception.status_code >= 500:
                severity = "high"
            elif exception.status_code >= 400:
                severity = "medium"
            
            # Create security event
            event = SecurityEvent(
                event_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                event_type="security_violation",
                severity=severity,
                source_ip=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
                description=f"{exception.status_code}: {exception.detail}",
                risk_score=1.0 if exception.status_code == 403 else 0.5,
                recommended_action="monitor" if severity == "low" else "investigate"
            )
            
            await gateway.log_security_event(event)
            
            # Auto-block IPs with repeated violations
            if exception.status_code == 403:
                await self._handle_security_violation(request)
                
        except Exception as e:
            logger.error(f"Failed to log security event: {e}")
    
    async def _handle_security_violation(self, request: Request):
        """Handle security violations (e.g., auto-blocking)"""
        client_ip = self._get_client_ip(request)
        
        # TODO: Implement IP reputation tracking
        # For now, just log the violation
        logger.warning(f"Security violation from IP: {client_ip}")
        
        # In a production system, you might:
        # 1. Track repeated violations per IP
        # 2. Auto-block IPs with too many violations
        # 3. Send alerts to security team
        # 4. Update threat intelligence
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if hasattr(request, "client") and request.client:
            return request.client.host
        
        return "unknown"


def get_current_user(request: Request) -> UserContext:
    """Get current user from request state"""
    if hasattr(request.state, 'user_context'):
        return request.state.user_context
    
    # Fallback for requests that bypassed middleware
    return UserContext(
        user_id="anonymous",
        email="anonymous@example.com",
        access_token=None
    )
