"""
Enhanced Remote MCP Server for Workplace Search
Integrates with Descope authentication, Cequence security, and Google Drive API
"""

import os
import json
import asyncio
from typing import Any, Dict, List, Optional, Sequence
from datetime import datetime, timedelta
import logging

from fastapi import FastAPI, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn

# MCP imports
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import ( Tool, TextContent
)

# Internal imports
from app.auth.descope_auth import DescopeAuthenticator
from app.auth.cequence_gateway import CequenceGateway
from app.adapters.google_drive_adapter import GoogleDriveAdapter
from app.models.models import UserContext, DocumentSource
from app.utils.logger import logger


# FastAPI app for HTTP endpoints
app = FastAPI(
    title="Workplace Search MCP Server",
    description="Model Context Protocol server with authentication and Google Drive integration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)

# Global instances
descope_auth = DescopeAuthenticator()
cequence_gateway = CequenceGateway()
authenticated_users: Dict[str, UserContext] = {}

# MCP Server instance
mcp_server = Server("workplace-search-mcp")


class AuthRequest(BaseModel):
    """Authentication request model"""
    token: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    auth_method: str = "token"  # "token", "email_password", "oauth"


class SearchRequest(BaseModel):
    """Search request model"""
    query: str
    max_results: int = 10
    source: Optional[DocumentSource] = None
    user_token: str


class DocumentRequest(BaseModel):
    """Document content request model"""
    document_id: str
    user_token: str


async def verify_authentication(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserContext:
    """Verify user authentication through Descope and Cequence"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    token = credentials.credentials
    
    # Check if user is already authenticated
    if token in authenticated_users:
        user_context = authenticated_users[token]
        logger.info(f"User {user_context.email} already authenticated")
        return user_context
    
    # Verify token with Descope
    if not descope_auth.enabled:
        logger.warning("Descope authentication disabled - using mock authentication")
        # Mock user for development
        user_context = UserContext(
            user_id="mock_user",
            email="mock@example.com",
            access_token=token,
            scopes=["drive.readonly"],
            permissions={"google_drive": True}
        )
        authenticated_users[token] = user_context
        return user_context
    
    try:
        # Verify token with Descope
        descope_user = await descope_auth.verify_token(token)
        if not descope_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        
        # Create user context
        user_context = UserContext(
            user_id=descope_user.user_id,
            email=descope_user.email,
            access_token=token,
            scopes=["drive.readonly"],
            permissions={"google_drive": True},
            metadata={
                "name": descope_user.name,
                "verified_email": descope_user.verified_email,
                "roles": descope_user.roles
            }
        )
        
        # Cache authenticated user
        authenticated_users[token] = user_context
        logger.info(f"User {user_context.email} authenticated successfully")
        
        return user_context
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


async def security_check(request: Request) -> Dict[str, Any]:
    """Perform security analysis with Cequence"""
    if not cequence_gateway.config.enabled:
        logger.debug("Cequence security disabled")
        return {"allowed": True, "risk_score": 0.0}
    
    try:
        analysis_result = await cequence_gateway.analyze_request(request)
        
        if not analysis_result.get("allowed", True):
            logger.warning(f"Request blocked by Cequence: {analysis_result}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request blocked by security policy"
            )
        
        risk_score = analysis_result.get("risk_score", 0.0)
        if risk_score > 0.7:
            logger.warning(f"High risk request detected: {risk_score}")
        
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Security analysis failed: {e}")
        # Allow request if security analysis fails
        return {"allowed": True, "risk_score": 0.0, "error": str(e)}


# FastAPI Routes

@app.post("/auth/login")
async def login(auth_request: AuthRequest, request: Request):
    """Authenticate user with Descope"""
    
    # Security check
    await security_check(request)
    
    if not descope_auth.enabled:
        # Mock authentication for development
        mock_token = f"mock_token_{datetime.now().timestamp()}"
        return {
            "token": mock_token,
            "user": {
                "email": "mock@example.com",
                "name": "Mock User"
            },
            "expires_in": 3600
        }
    
    try:
        if auth_request.auth_method == "email_password":
            # Email/password authentication
            result = await descope_auth.authenticate_user(
                auth_request.email,
                auth_request.password
            )
        elif auth_request.auth_method == "token":
            # Token verification
            descope_user = await descope_auth.verify_token(auth_request.token)
            if not descope_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            result = {
                "token": auth_request.token,
                "user": descope_user.dict(),
                "expires_in": 3600
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported authentication method"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )


@app.post("/search")
async def search_documents(
    search_request: SearchRequest,
    request: Request,
    user_context: UserContext = Depends(verify_authentication)
):
    """Search documents in Google Drive"""
    
    # Security check
    security_result = await security_check(request)
    
    try:
        # Initialize Google Drive adapter
        drive_adapter = GoogleDriveAdapter(user_context)
        
        # Perform search
        results = await drive_adapter.search(
            query=search_request.query,
            max_results=search_request.max_results
        )
        
        # Log security analytics
        if cequence_gateway.config.enabled:
            await cequence_gateway.log_analytics({
                "event_type": "search",
                "user_id": user_context.user_id,
                "query": search_request.query,
                "results_count": len(results),
                "risk_score": security_result.get("risk_score", 0.0)
            })
        
        return {
            "results": [result.dict() for result in results],
            "total_count": len(results),
            "query": search_request.query
        }
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@app.post("/document")
async def get_document_content(
    doc_request: DocumentRequest,
    request: Request,
    user_context: UserContext = Depends(verify_authentication)
):
    """Get document content from Google Drive"""
    
    # Security check
    security_result = await security_check(request)
    
    try:
        # Initialize Google Drive adapter
        drive_adapter = GoogleDriveAdapter(user_context)
        
        # Get document content
        document = await drive_adapter.get_document(doc_request.document_id)
        
        # Log security analytics
        if cequence_gateway.config.enabled:
            await cequence_gateway.log_analytics({
                "event_type": "document_access",
                "user_id": user_context.user_id,
                "document_id": doc_request.document_id,
                "risk_score": security_result.get("risk_score", 0.0)
            })
        
        return document.dict()
        
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document retrieval failed: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "descope_auth": descope_auth.enabled,
            "cequence_security": cequence_gateway.config.enabled,
            "google_drive": True
        }
    }


# MCP Server Implementation

@mcp_server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """List available MCP tools"""
    return [
        Tool(
            name="search_workplace",
            description="Search for documents in workplace systems (Google Drive, Notion, Slack, Confluence)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10
                    },
                    "source": {
                        "type": "string",
                        "enum": ["gdrive", "notion", "slack", "confluence"],
                        "description": "Specific source to search (optional)"
                    },
                    "user_token": {
                        "type": "string",
                        "description": "User authentication token"
                    }
                },
                "required": ["query", "user_token"]
            }
        ),
        Tool(
            name="get_document_content",
            description="Get the full content of a specific document",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "string",
                        "description": "ID of the document to retrieve"
                    },
                    "user_token": {
                        "type": "string",
                        "description": "User authentication token"
                    }
                },
                "required": ["document_id", "user_token"]
            }
        ),
        Tool(
            name="authenticate_user",
            description="Authenticate user with Descope",
            inputSchema={
                "type": "object",
                "properties": {
                    "email": {
                        "type": "string",
                        "description": "User email"
                    },
                    "password": {
                        "type": "string",
                        "description": "User password"
                    },
                    "token": {
                        "type": "string",
                        "description": "Authentication token (alternative to email/password)"
                    },
                    "auth_method": {
                        "type": "string",
                        "enum": ["email_password", "token"],
                        "default": "token",
                        "description": "Authentication method"
                    }
                }
            }
        )
    ]


@mcp_server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle MCP tool calls"""
    
    try:
        if name == "authenticate_user":
            return await handle_authenticate_tool(arguments)
        elif name == "search_workplace":
            return await handle_search_tool(arguments)
        elif name == "get_document_content":
            return await handle_document_tool(arguments)
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        logger.error(f"Tool execution failed for {name}: {e}")
        return [TextContent(
            type="text",
            text=f"Error executing tool {name}: {str(e)}"
        )]


async def handle_authenticate_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle authentication tool"""
    
    if not descope_auth.enabled:
        # Mock authentication for development
        mock_token = f"mock_token_{datetime.now().timestamp()}"
        result = {
            "success": True,
            "token": mock_token,
            "user": {
                "email": arguments.get("email", "mock@example.com"),
                "name": "Mock User"
            },
            "message": "Authentication successful (mock mode)"
        }
    else:
        try:
            auth_method = arguments.get("auth_method", "token")
            
            if auth_method == "email_password":
                email = arguments.get("email")
                password = arguments.get("password")
                if not email or not password:
                    raise ValueError("Email and password required for email_password authentication")
                
                auth_result = await descope_auth.authenticate_user(email, password)
                result = {
                    "success": True,
                    "token": auth_result["token"],
                    "user": auth_result["user"],
                    "message": "Authentication successful"
                }
            elif auth_method == "token":
                token = arguments.get("token")
                if not token:
                    raise ValueError("Token required for token authentication")
                
                descope_user = await descope_auth.verify_token(token)
                if not descope_user:
                    raise ValueError("Invalid token")
                
                result = {
                    "success": True,
                    "token": token,
                    "user": descope_user.dict(),
                    "message": "Token verification successful"
                }
            else:
                raise ValueError(f"Unsupported authentication method: {auth_method}")
                
        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "message": "Authentication failed"
            }
    
    return [TextContent(
        type="text",
        text=json.dumps(result, indent=2)
    )]


async def handle_search_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle search tool"""
    
    query = arguments.get("query")
    max_results = arguments.get("max_results", 10)
    user_token = arguments.get("user_token")
    
    if not query:
        return [TextContent(
            type="text",
            text="Error: Query parameter is required"
        )]
    
    if not user_token:
        return [TextContent(
            type="text",
            text="Error: User token is required for authentication"
        )]
    
    try:
        # Get user context
        if user_token not in authenticated_users:
            # Try to authenticate with the token
            if descope_auth.enabled:
                descope_user = await descope_auth.verify_token(user_token)
                if not descope_user:
                    return [TextContent(
                        type="text",
                        text="Error: Invalid authentication token"
                    )]
                
                user_context = UserContext(
                    user_id=descope_user.user_id,
                    email=descope_user.email,
                    access_token=user_token,
                    scopes=["drive.readonly"],
                    permissions={"google_drive": True}
                )
                authenticated_users[user_token] = user_context
            else:
                # Mock user for development
                user_context = UserContext(
                    user_id="mock_user",
                    email="mock@example.com",
                    access_token=user_token,
                    scopes=["drive.readonly"],
                    permissions={"google_drive": True}
                )
                authenticated_users[user_token] = user_context
        else:
            user_context = authenticated_users[user_token]
        
        # Initialize Google Drive adapter
        drive_adapter = GoogleDriveAdapter(user_context)
        
        # Perform search
        results = await drive_adapter.search(
            query=query,
            max_results=max_results
        )
        
        # Format results
        search_results = {
            "query": query,
            "total_results": len(results),
            "results": [result.dict() for result in results]
        }
        
        return [TextContent(
            type="text",
            text=json.dumps(search_results, indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return [TextContent(
            type="text",
            text=f"Search failed: {str(e)}"
        )]


async def handle_document_tool(arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle document content tool"""
    
    document_id = arguments.get("document_id")
    user_token = arguments.get("user_token")
    
    if not document_id:
        return [TextContent(
            type="text",
            text="Error: Document ID is required"
        )]
    
    if not user_token:
        return [TextContent(
            type="text",
            text="Error: User token is required for authentication"
        )]
    
    try:
        # Get user context
        if user_token not in authenticated_users:
            # Try to authenticate with the token
            if descope_auth.enabled:
                descope_user = await descope_auth.verify_token(user_token)
                if not descope_user:
                    return [TextContent(
                        type="text",
                        text="Error: Invalid authentication token"
                    )]
                
                user_context = UserContext(
                    user_id=descope_user.user_id,
                    email=descope_user.email,
                    access_token=user_token,
                    scopes=["drive.readonly"],
                    permissions={"google_drive": True}
                )
                authenticated_users[user_token] = user_context
            else:
                # Mock user for development
                user_context = UserContext(
                    user_id="mock_user",
                    email="mock@example.com",
                    access_token=user_token,
                    scopes=["drive.readonly"],
                    permissions={"google_drive": True}
                )
                authenticated_users[user_token] = user_context
        else:
            user_context = authenticated_users[user_token]
        
        # Initialize Google Drive adapter
        drive_adapter = GoogleDriveAdapter(user_context)
        
        # Get document content
        document = await drive_adapter.get_document(document_id)
        
        return [TextContent(
            type="text",
            text=json.dumps(document.dict(), indent=2)
        )]
        
    except Exception as e:
        logger.error(f"Document retrieval failed: {e}")
        return [TextContent(
            type="text",
            text=f"Document retrieval failed: {str(e)}"
        )]


# MCP over HTTP endpoints for remote access
@app.post("/mcp/tools")
async def list_mcp_tools(request: Request):
    """List available MCP tools via HTTP"""
    await security_check(request)
    
    tools = await handle_list_tools()
    return {
        "tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            }
            for tool in tools
        ]
    }


@app.post("/mcp/call-tool")
async def call_mcp_tool(request: Request, tool_request: dict):
    """Call MCP tool via HTTP"""
    await security_check(request)
    
    tool_name = tool_request.get("name")
    arguments = tool_request.get("arguments", {})
    
    if not tool_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tool name is required"
        )
    
    try:
        result = await handle_call_tool(tool_name, arguments)
        return {
            "success": True,
            "result": [content.text for content in result],
            "tool_name": tool_name
        }
    except Exception as e:
        logger.error(f"Tool call failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Tool execution failed: {str(e)}"
        )


@app.get("/mcp/info")
async def get_mcp_info():
    """Get MCP server information"""
    return {
        "name": "workplace-search-mcp",
        "version": "1.0.0",
        "description": "Workplace Search MCP Server with Descope auth and Google Drive",
        "capabilities": {
            "tools": True,
            "authentication": True,
            "security": True
        },
        "endpoints": {
            "tools": "/mcp/tools",
            "call_tool": "/mcp/call-tool",
            "auth": "/auth/login",
            "search": "/search",
            "document": "/document",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    # Always run as HTTP server
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    logger.info(f"Starting Workplace Search MCP HTTP Server on {host}:{port}")
    logger.info("Server will be accessible via HTTP endpoints for remote Claude access")
    
    uvicorn.run(
        app, 
        host=host, 
        port=port,
        reload=False,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
