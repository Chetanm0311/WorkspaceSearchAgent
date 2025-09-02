from typing import List, Dict, Any
import os
import hashlib
from app.models.models import UserContext, DocumentSource, SearchResult, DocumentContent, SummaryResult, RecentUpdate, SourceDocument
from app.utils.logger import logger
from app.utils.auth import has_required_scopes
from app.adapters.google_drive_adapter import GoogleDriveAdapter
from app.adapters.notion_adapter import NotionAdapter
from app.adapters.slack_adapter import SlackAdapter
from app.adapters.confluence_adapter import ConfluenceAdapter
from cachetools import TTLCache

# Cache settings from environment
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
SEARCH_CACHE_TTL = int(os.getenv("SEARCH_CACHE_TTL", "300"))
DOCUMENT_CACHE_TTL = int(os.getenv("DOCUMENT_CACHE_TTL", "600"))
UPDATES_CACHE_TTL = int(os.getenv("UPDATES_CACHE_TTL", "300"))

# Cache for search results
search_cache = TTLCache(maxsize=100, ttl=SEARCH_CACHE_TTL)
document_cache = TTLCache(maxsize=100, ttl=DOCUMENT_CACHE_TTL)
update_cache = TTLCache(maxsize=50, ttl=UPDATES_CACHE_TTL)

def _get_cache_key(prefix, *args):
    """Generate a unique cache key based on provided arguments"""
    key_string = prefix + ":" + ":".join(str(arg) for arg in args)
    return hashlib.md5(key_string.encode()).hexdigest()

async def search_documents(
    query: str,
    sources: List[DocumentSource],
    max_results: int,
    user_context: UserContext
) -> List[SearchResult]:
    """
    Search documents across multiple sources.
    """
    # Generate cache key
    cache_key = _get_cache_key("search", query, ",".join(sorted([str(s) for s in sources])), 
                             max_results, user_context.user_id)
    
    # Check if result in cache
    if CACHE_ENABLED and cache_key in search_cache:
        logger.info(f"Returning cached results for query: '{query}'")
        return search_cache[cache_key]
        
    logger.info(f"Searching for '{query}' in sources: {', '.join(str(s) for s in sources)}")
    
    if not user_context.authenticated:
        raise Exception("User is not authenticated")
    
    # Initialize adapters
    adapters = initialize_adapters(user_context)
    
    # Collect results from all requested sources
    results: List[SearchResult] = []
    
    # Check permissions and search each source
    for source in sources:
        required_scope = f"{source}:read"
        
        if not has_required_scopes(user_context, [required_scope]):
            logger.warning(f"User doesn't have permission to access {source}")
            continue
        
        try:
            adapter = adapters.get(source)
            if not adapter:
                logger.warning(f"No adapter available for {source}")
                continue
            
            source_results = await adapter.search(query, max_results)
            results.extend(source_results)
        except Exception as e:
            logger.error(f"Error searching {source}: {e}")
    
    # Sort by relevance (adapter-specific) and limit results
    results = results[:max_results]
    
    # Store in cache
    if CACHE_ENABLED:
        search_cache[cache_key] = results
    
    return results

async def summarize_content(
    document_ids: List[str],
    max_length: int,
    user_context: UserContext
) -> SummaryResult:
    """
    Summarize content from multiple documents.
    """
    # Generate cache key
    cache_key = _get_cache_key("summarize", ",".join(sorted(document_ids)), 
                             max_length, user_context.user_id)
                             
    # Check if result in cache
    if CACHE_ENABLED and cache_key in document_cache:
        logger.info(f"Returning cached summary for documents: {document_ids}")
        return document_cache[cache_key]
    
    logger.info(f"Summarizing {len(document_ids)} documents")
    
    if not user_context.authenticated:
        raise Exception("User is not authenticated")
    
    # Initialize adapters
    adapters = initialize_adapters(user_context)
    
    # Fetch document content from appropriate sources
    documents: List[DocumentContent] = []
    
    for doc_id in document_ids:
        # Parse document ID to determine the source
        # Format: source:id (e.g., gdrive:1234, notion:5678)
        parts = doc_id.split(":", 1)
        if len(parts) != 2:
            logger.warning(f"Invalid document ID format: {doc_id}")
            continue
        
        source, doc_id = parts
        
        required_scope = f"{source}:read"
        
        if not has_required_scopes(user_context, [required_scope]):
            logger.warning(f"User doesn't have permission to access {source}")
            continue
        
        try:
            adapter = adapters.get(source)
            if not adapter:
                logger.warning(f"No adapter available for {source}")
                continue
            
            document = await adapter.get_document(doc_id)
            documents.append(document)
        except Exception as e:
            logger.error(f"Error fetching document {doc_id}: {e}")
    
    # Generate summary using collected documents
    # In a real implementation, this might use an LLM or other summarization service
    summary = generate_summary(documents, max_length)
    
    # Store in cache
    if CACHE_ENABLED:
        document_cache[cache_key] = summary
    
    return summary

async def get_recent_updates(
    sources: List[DocumentSource],
    days: int,
    max_results: int,
    user_context: UserContext
) -> List[RecentUpdate]:
    """
    Get recent updates from multiple sources.
    """
    # Generate cache key
    cache_key = _get_cache_key("updates", ",".join(sorted([str(s) for s in sources])), 
                             days, max_results, user_context.user_id)
                             
    # Check if result in cache
    if CACHE_ENABLED and cache_key in update_cache:
        logger.info(f"Returning cached updates for last {days} days")
        return update_cache[cache_key]
    
    logger.info(f"Getting updates from the last {days} days from sources: {', '.join(str(s) for s in sources)}")
    
    if not user_context.authenticated:
        raise Exception("User is not authenticated")
    
    # Initialize adapters
    adapters = initialize_adapters(user_context)
    
    # Collect updates from all requested sources
    updates: List[RecentUpdate] = []
    
    # Check permissions and get updates from each source
    for source in sources:
        required_scope = f"{source}:read"
        
        if not has_required_scopes(user_context, [required_scope]):
            logger.warning(f"User doesn't have permission to access {source}")
            continue
        
        try:
            adapter = adapters.get(source)
            if not adapter:
                logger.warning(f"No adapter available for {source}")
                continue
            
            source_updates = await adapter.get_recent_updates(days)
            updates.extend(source_updates)
        except Exception as e:
            logger.error(f"Error getting updates from {source}: {e}")
    
    # Sort by date (newest first) and limit results
    sorted_updates = sorted(
        updates,
        key=lambda x: x.last_modified,
        reverse=True
    )
    
    result = sorted_updates[:max_results]
    
    # Store in cache
    if CACHE_ENABLED:
        update_cache[cache_key] = result
    
    return result

def initialize_adapters(user_context: UserContext) -> Dict[str, Any]:
    """
    Initialize adapters for different sources.
    """
    return {
        DocumentSource.gdrive: GoogleDriveAdapter(user_context),
        # DocumentSource.notion: NotionAdapter(user_context),
        # DocumentSource.slack: SlackAdapter(user_context),
        # DocumentSource.confluence: ConfluenceAdapter(user_context)
    }

def generate_summary(documents: List[DocumentContent], max_length: int) -> SummaryResult:
    """
    Generate a summary from multiple documents.
    
    In a real implementation, this would use an LLM or other summarization service.
    """
    # This is a simple placeholder implementation
    combined_text = " ".join(doc.content for doc in documents)
    truncated_summary = combined_text[:max_length]
    
    return SummaryResult(
        summary=truncated_summary,
        key_points=["Key point 1", "Key point 2", "Key point 3"],
        source_documents=[
            SourceDocument(
                id=doc.id,
                title=doc.title,
                source=doc.source
            )
            for doc in documents
        ]
    )
