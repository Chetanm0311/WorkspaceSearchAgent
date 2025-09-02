import os
import json
import sys
import traceback
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from typing import List, Optional, Dict, Any
import uvicorn
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

# Import models and services
from app.services.search_service import search_documents, summarize_content, get_recent_updates
from app.models.models import (
    DocumentSource, 
    SearchResult, 
    DocumentContent, 
    SummaryResult, 
    RecentUpdate,
    UserContext
)
from app.utils.auth import authenticate_user, secure_mcp_request
from app.utils.logger import logger

# Create FastAPI app
app = FastAPI(
    title="Workplace Search Agent",
    description="MCP server for workplace search that integrates with Google Drive, Notion, Slack, and Confluence",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query")
    sources: Optional[List[DocumentSource]] = Field(None, description="Sources to search from (gdrive, notion, slack, confluence)")
    max_results: Optional[int] = Field(10, description="Maximum number of results to return")

class SummarizeRequest(BaseModel):
    document_ids: List[str] = Field(..., description="IDs of documents to summarize")
    max_length: Optional[int] = Field(500, description="Maximum length of the summary")

class UpdatesRequest(BaseModel):
    sources: Optional[List[DocumentSource]] = Field(None, description="Sources to get updates from (gdrive, notion, slack, confluence)")
    days: Optional[int] = Field(7, description="Number of days to look back")
    max_results: Optional[int] = Field(10, description="Maximum number of results to return")

# Response models
class SearchResponse(BaseModel):
    results: List[SearchResult]

class SummarizeResponse(BaseModel):
    summary: SummaryResult

class UpdatesResponse(BaseModel):
    updates: List[RecentUpdate]

# MCP Schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Workplace Search Agent MCP",
        version="1.0.0",
        description="Model Context Protocol server for workplace search",
        routes=app.routes,
    )    # Read MCP schema from file
    try:
        with open("mcp_schema.json", "r") as f:
            mcp_schema = json.load(f)
            
        # Add MCP-specific schema information
        openapi_schema["info"]["x-mcp-schema"] = mcp_schema["info"]["x-mcp-schema"]
    except Exception as e:
        logger.error(f"Error loading MCP schema: {e}")
        # Fallback to inline schema
        openapi_schema["info"]["x-mcp-schema"] = {
            "functions": [
                {
                    "name": "search_documents",
                    "description": "Search for documents, messages, and knowledge base entries across multiple sources",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query"
                            },
                            "sources": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["gdrive", "notion", "slack", "confluence"]
                                },
                                "description": "Sources to search from"
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "summarize_content",
                    "description": "Summarize or extract key points from retrieved content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "document_ids": {
                                "type": "array",
                                "items": {
                                    "type": "string"
                                },
                                "description": "IDs of documents to summarize"
                            },
                            "max_length": {
                                "type": "integer",
                                "description": "Maximum length of the summary",
                                "default": 500
                            }
                        },                        "required": ["document_ids"]
                    }
                },
                {
                    "name": "get_recent_updates",
                    "description": "Get recent updates from documents, messages, and knowledge base entries",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sources": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ["gdrive", "notion", "slack", "confluence"]
                                },
                                "description": "Sources to get updates from"
                            },
                            "days": {
                                "type": "integer",
                                "description": "Number of days to look back",
                                "default": 7
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 10
                            }
                        }
                    }
                }
            ]
        }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Dependencies
async def get_user_context(request: Request) -> UserContext:
    auth_token = request.headers.get("Authorization", "").replace("Bearer ", "")
    return await authenticate_user(auth_token)

# Routes
@app.post("/mcp/search", response_model=SearchResponse)
async def search_route(
    request: SearchRequest, 
    user_context: UserContext = Depends(get_user_context)
):
    if not user_context.authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Apply security measures to request
    secure_request = secure_mcp_request(request.dict(), user_context)
    
    results = await search_documents(
        query=secure_request["query"],
        sources=secure_request["sources"] or ["gdrive", "notion", "slack", "confluence"],
        max_results=secure_request["max_results"],
        user_context=user_context
    )
    
    return {"results": results}

@app.post("/mcp/summarize", response_model=SummarizeResponse)
async def summarize_route(
    request: SummarizeRequest, 
    user_context: UserContext = Depends(get_user_context)
):
    if not user_context.authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Apply security measures to request
    secure_request = secure_mcp_request(request.dict(), user_context)
    
    summary = await summarize_content(
        document_ids=secure_request["document_ids"],
        max_length=secure_request["max_length"],
        user_context=user_context
    )
    
    return {"summary": summary}

@app.post("/mcp/updates", response_model=UpdatesResponse)
async def updates_route(
    request: UpdatesRequest, 
    user_context: UserContext = Depends(get_user_context)
):
    if not user_context.authenticated:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Apply security measures to request
    secure_request = secure_mcp_request(request.dict(), user_context)
    
    updates = await get_recent_updates(
        sources=secure_request["sources"] or ["gdrive", "notion", "slack", "confluence"],
        days=secure_request["days"],
        max_results=secure_request["max_results"],
        user_context=user_context
    )
    
    return {"updates": updates}

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# MCP endpoint that provides JSON schema
@app.get("/mcp")
async def mcp_schema():
    return app.openapi()

