"""
Claude MCP Client for Remote HTTP Server
Connects Claude Desktop to the remote Workplace Search MCP Server
"""

import os
import json
import asyncio
import httpx
from typing import Any, Dict, List, Optional
from datetime import datetime

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.lowlevel.server import NotificationOptions
from mcp.types import (
    Tool, TextContent, CallToolRequest, CallToolResult,
    ListResourcesResult, ListToolsResult
)
from app.utils.logger import logger

class ClaudeMCPClient:
    """MCP Client that connects Claude Desktop to remote HTTP server"""
    
    def __init__(self):
        self.server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000")
        self.server_token = os.getenv("MCP_SERVER_TOKEN", "")
        self.session_token = None
        self.user_context = None
        
        # Initialize MCP server for Claude Desktop
        self.mcp_server = Server("workplace-search-remote-client")
        self.setup_mcp_handlers()
          # HTTP client for remote server
        headers = {"Content-Type": "application/json"}
        if self.server_token:
            headers["Authorization"] = f"Bearer {self.server_token}"
        
        self.http_client = httpx.AsyncClient(
            base_url=self.server_url,
            timeout=30.0,
            headers=headers
        )
    
    def setup_mcp_handlers(self):
        """Setup MCP server handlers"""
        
        @self.mcp_server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List tools from remote server"""
            try:
                # response = await self.http_client.get("/mcp/tools")
                # if response.status_code == 200:
                #     data = response.json()
                #     tools = []
                #     for tool_data in data.get("tools", []):
                #         tools.append(Tool(
                #             name=tool_data["name"],
                #             description=tool_data["description"],
                #             inputSchema=tool_data["inputSchema"]
                #         ))
                tools = [
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

                return tools
                # else:
                #     return []
            except Exception as e:
                logger.error(f"Error listing tools: {e}")
                return []
        
        @self.mcp_server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Call tool on remote server"""
            try:
                # Special handling for authentication
                if name == "authenticate_user":
                    return await self._handle_authentication(arguments)
                
                # Add session token to arguments if available
                if self.session_token and "user_token" not in arguments:
                    arguments["user_token"] = self.session_token
                
                # Call remote server
                tool_request = {
                    "name": name,
                    "arguments": arguments
                }
                
                response = await self.http_client.post("/mcp/call-tool", json=tool_request)
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("success", False):
                        results = data.get("result", [])
                        return [TextContent(type="text", text=result) for result in results]
                    else:
                        error_msg = data.get("error", "Unknown error")
                        return [TextContent(type="text", text=f"Error: {error_msg}")]
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    return [TextContent(type="text", text=f"Server error: {error_msg}")]
                    
            except Exception as e:
                return [TextContent(type="text", text=f"Error calling tool {name}: {str(e)}")]
    
    async def _handle_authentication(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle authentication with remote server"""
        try:
            auth_data = {
                "email": arguments.get("email"),
                "password": arguments.get("password"),
                "token": arguments.get("token"),
                "auth_method": arguments.get("auth_method", "token")
            }
            
            response = await self.http_client.post("/auth/login", json=auth_data)
            
            if response.status_code == 200:
                data = response.json()
                self.session_token = data.get("token")
                self.user_context = data.get("user")
                
                result = {
                    "success": True,
                    "message": "Authentication successful",
                    "user": self.user_context,
                    "token": self.session_token
                }
                
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            else:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"detail": response.text}
                result = {
                    "success": False,
                    "error": error_data.get("detail", "Authentication failed"),
                    "status_code": response.status_code
                }
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
                
        except Exception as e:
            result = {
                "success": False,
                "error": f"Authentication request failed: {str(e)}"
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
    
    async def run_stdio(self):
        """Run MCP server over stdio for Claude Desktop"""
        from mcp.server.stdio import stdio_server
        
        async with stdio_server() as (read_stream, write_stream):
            await self.mcp_server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="workplace-search-remote-client",
                    server_version="1.0.0",
                    capabilities=self.mcp_server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )
    
    def run(self):
        """Run the client"""
        asyncio.run(self.run_stdio())
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.http_client.aclose()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode - check connection to remote server
        async def test_connection():
            client = ClaudeMCPClient()
            try:
                print(f"Testing connection to: {client.server_url}")
                response = await client.http_client.get("/health")
                if response.status_code == 200:
                    print("✓ Server is reachable and healthy")
                    data = response.json()
                    print(f"  Server status: {data.get('status', 'unknown')}")
                    print(f"  Services: {data.get('services', {})}")
                else:
                    print(f"✗ Server returned status {response.status_code}")
            except Exception as e:
                print(f"✗ Connection failed: {e}")
            finally:
                await client.http_client.aclose()
        
        asyncio.run(test_connection())
    else:
        # Normal mode - run as MCP client for Claude Desktop
        client = ClaudeMCPClient()
        client.run()
