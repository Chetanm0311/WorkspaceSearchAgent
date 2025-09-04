from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class DocumentSource(str, Enum):
    """Source types for documents"""
    gdrive = "gdrive"
    notion = "notion"
    slack = "slack"
    confluence = "confluence"


class UserContext(BaseModel):
    """User context for authentication and authorization"""
    user_id: str
    email: str
    access_token: Optional[str] = None
    scopes: List[str] = Field(default_factory=list)
    organization_id: Optional[str] = None
    permissions: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Search result from any document source"""
    id: str
    title: str
    snippet: str
    url: str
    source: DocumentSource
    last_modified: str
    author: str
    access_level: Literal["owner", "editor", "viewer", "restricted"] = "viewer"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentContent(BaseModel):
    """Full document content"""
    id: str
    title: str
    content: str
    source: DocumentSource
    url: str
    last_modified: str
    author: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RecentUpdate(BaseModel):
    """Recent update information"""
    id: str
    title: str
    snippet: str
    url: str
    source: DocumentSource
    last_modified: str
    author: str
    update_type: Literal["created", "modified", "shared", "commented"] = "modified"
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    """Request for document search"""
    query: str
    sources: Optional[List[DocumentSource]] = None
    max_results: int = Field(default=10, ge=1, le=100)
    filters: Dict[str, Any] = Field(default_factory=dict)


class DocumentRequest(BaseModel):
    """Request for document content"""
    document_id: str
    source: DocumentSource


class RecentUpdatesRequest(BaseModel):
    """Request for recent updates"""
    days: int = Field(default=7, ge=1, le=30)
    sources: Optional[List[DocumentSource]] = None
    max_results: int = Field(default=20, ge=1, le=100)


class SummaryRequest(BaseModel):
    """Request for document summarization"""
    document_id: str
    source: DocumentSource
    summary_type: Literal["brief", "detailed", "key_points"] = "brief"


class MCPToolResponse(BaseModel):
    """Standard MCP tool response"""
    content: List[Dict[str, Any]]
    isError: bool = False


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    code: str
    details: Optional[Dict[str, Any]] = None
