"""
Authentication module for Google Drive MCP Server
"""

from app.auth.descope_auth import DescopeAuthenticator
from app.auth.cequence_gateway import CequenceGateway
from app.auth.security import SecurityMiddleware

__all__ = [
    "DescopeAuthenticator",
    "authenticator",
    "CequenceGateway",
    "SecurityMiddleware"
]
