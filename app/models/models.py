from typing import List, Optional, Literal
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

# Document source types
class DocumentSource(str, Enum):
    gdrive = "gdrive"
    notion = "notion"
    slack = "slack"
    confluence = "confluence"

# User context for authentication and authorization
class UserContext(BaseModel):
    authenticated: bool
    user_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    access_scopes: List[str] = []
    access_token: Optional[str] = None

# Search result model
class SearchResult(BaseModel):
    id: str
    title: str
    snippet: str
    url: str
    source: DocumentSource
    last_modified: str
    author: str
    access_level: str

# Document content model
class DocumentContent(BaseModel):
    id: str
    title: str
    content: str
    source: DocumentSource
    url: str
    last_modified: str
    author: str

# Summary result model
class SourceDocument(BaseModel):
    id: str
    title: str
    source: DocumentSource

class SummaryResult(BaseModel):
    summary: str
    key_points: List[str]
    source_documents: List[SourceDocument]

# Recent update model
class RecentUpdate(BaseModel):
    id: str
    title: str
    snippet: str
    url: str
    source: DocumentSource
    last_modified: str
    author: str
    update_type: Literal["created", "modified", "shared", "commented"]

# Error response model
class ErrorResponse(BaseModel):
    error: str
    code: Optional[str] = None
    details: Optional[str] = None
