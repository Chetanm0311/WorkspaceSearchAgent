# MCP stdio server for Workplace Search Agent
import asyncio
from typing import List, Optional

from mcp.server.fastmcp import FastMCP

# Reuse existing app logic
from app.services.search_service import (
    search_documents as svc_search_documents,
    summarize_content as svc_summarize_content,
    get_recent_updates as svc_get_recent_updates,
)
from app.models.models import DocumentSource
from app.utils.auth import authenticate_user
from app.utils.logger import logger

mcp = FastMCP("workplace-search")


def _parse_sources(sources: Optional[List[str]]) -> List[DocumentSource]:
    if not sources:
        return [
            DocumentSource.gdrive,
        ]
    mapped: List[DocumentSource] = []
    for s in sources:
        try:
            mapped.append(DocumentSource(s))
        except Exception:
            # Ignore unknown sources
            logger.warning(f"Unknown source '{s}' ignored")
    return mapped


@mcp.tool()
async def search_documents(
    query: str,
    sources: Optional[List[str]] = None,
    max_results: int = 10,
    auth_token: Optional[str] = None,
):
    """Search for documents, messages, and knowledge base entries across multiple sources."""
    user_context = await authenticate_user(auth_token or "auth")
    results = await svc_search_documents(
        query=query,
        sources=_parse_sources(sources),
        max_results=max_results,
        user_context=user_context,
    )
    # Pydantic models are JSON-serializable via .model_dump() in v2
    return {"results": [r.model_dump() for r in results]}


@mcp.tool()
async def summarize_content(
    document_ids: List[str],
    max_length: int = 500,
    auth_token: Optional[str] = None,
):
    """Summarize or extract key points from retrieved content."""
    user_context = await authenticate_user(auth_token or "")
    summary = await svc_summarize_content(
        document_ids=document_ids,
        max_length=max_length,
        user_context=user_context,
    )
    return {"summary": summary.model_dump()}


@mcp.tool()
async def get_recent_updates(
    sources: Optional[List[str]] = None,
    days: int = 7,
    max_results: int = 10,
    auth_token: Optional[str] = None,
):
    """Get recent updates from documents, messages, and knowledge base entries."""
    user_context = await authenticate_user(auth_token or "")
    updates = await svc_get_recent_updates(
        sources=_parse_sources(sources),
        days=days,
        max_results=max_results,
        user_context=user_context,
    )
    return {"updates": [u.model_dump() for u in updates]}


# Remove manual stdio plumbing; let FastMCP manage stdio

def main():
    try:
        mcp.run()  # defaults to stdio transport
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
