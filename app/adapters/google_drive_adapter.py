from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import os
import asyncio

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.models.models import UserContext, SearchResult, DocumentContent, RecentUpdate, DocumentSource
from app.utils.logger import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class GoogleDriveOAuthHandler:
    """Handles OAuth 2.0 authentication for Google Drive API"""
    
    def __init__(self, credentials_path: str = None, token_path: str = None):
        self.credentials_path = credentials_path or os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
        self.token_path = token_path or os.getenv("GOOGLE_TOKEN_PATH", "token.json")
        self.scopes = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
    
    def get_credentials(self) -> Optional[Credentials]:
        """Get valid credentials for Google Drive API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, self.scopes)
            except Exception as e:
                logger.error(f"Error loading saved credentials: {e}")
        
        # If there are no (valid) credentials available, let the user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed Google Drive credentials")
                except Exception as e:
                    logger.error(f"Error refreshing credentials: {e}")
                    creds = None
            
            if not creds and os.path.exists(self.credentials_path):
                try:
                    flow = Flow.from_client_secrets_file(self.credentials_path, self.scopes)
                    flow.redirect_uri = 'http://localhost:8080'
                    
                    # For production, implement proper OAuth flow
                    logger.warning("Google Drive credentials need to be authorized. Please run the OAuth setup.")
                    return None
                except Exception as e:
                    logger.error(f"Error setting up OAuth flow: {e}")
                    return None
        
        # Save the credentials for the next run
        if creds and creds.valid:
            try:
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
                logger.info("Saved Google Drive credentials")
            except Exception as e:
                logger.error(f"Error saving credentials: {e}")
        
        return creds


class GoogleDriveAdapter:
    """Production-level Google Drive adapter with real API integration"""
    
    SUPPORTED_MIME_TYPES = {
        'application/vnd.google-apps.document': 'text/plain',
        'application/vnd.google-apps.spreadsheet': 'text/csv',
        'application/vnd.google-apps.presentation': 'text/plain',
        'application/pdf': 'application/pdf',
        'text/plain': 'text/plain',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'text/plain',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'text/csv'
    }
    
    def __init__(self, user_context: UserContext):
        self.user_context = user_context
        self.api_base_url = "https://www.googleapis.com/drive/v3"
        self.oauth_handler = GoogleDriveOAuthHandler()
        self._service = None
        self._credentials = None
        
        # Use environment variables for production
        self.use_production_api = os.getenv("GOOGLE_DRIVE_PRODUCTION", "false").lower() == "true"
    
    async def _get_service(self):
        """Get authenticated Google Drive service"""
        if self._service is None:
            if self.use_production_api:
                self._credentials = self.oauth_handler.get_credentials()
                if self._credentials:
                    # Run in thread pool since Google API client is synchronous
                    loop = asyncio.get_event_loop()
                    self._service = await loop.run_in_executor(
                        None, 
                        lambda: build('drive', 'v3', credentials=self._credentials)
                    )
                else:
                    logger.warning("No valid Google Drive credentials available")
                    return None
            else:
                logger.info("Using mock Google Drive service for development")
                return None
        return self._service
    
    def _build_search_query(self, query: str, file_types: List[str] = None) -> str:
        """Build Google Drive search query with advanced filters"""
        # Escape special characters in query
        escaped_query = query.replace("'", "\\'")
        
        # Base search in content and name
        search_parts = [
            f"fullText contains '{escaped_query}'",
            f"name contains '{escaped_query}'"
        ]
        
        # Add file type filters
        if file_types:
            mime_type_conditions = []
            for file_type in file_types:
                if file_type in self.SUPPORTED_MIME_TYPES:
                    mime_type_conditions.append(f"mimeType='{file_type}'")
            if mime_type_conditions:
                search_parts.append(f"({' or '.join(mime_type_conditions)})")
        
        # Exclude trashed files
        search_parts.append("trashed=false")
        
        return " and ".join([f"({part})" for part in search_parts[:2]]) + " and " + " and ".join(search_parts[2:])
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((HttpError, Exception))
    )
    async def search(self, query: str, max_results: int) -> List[SearchResult]:
        """Search Google Drive for documents matching the query"""
        logger.info(f"Searching Google Drive for: '{query}' (max_results: {max_results})")
        
        try:
            service = await self._get_service()
            
            if not service and self.use_production_api:
                logger.error("Google Drive service not available")
                return []
            
            if service:
                # Production API call
                search_query = self._build_search_query(query)
                logger.debug(f"Google Drive search query: {search_query}")
                
                # Run in thread pool since Google API client is synchronous
                loop = asyncio.get_event_loop()
                
                def _search():
                    return service.files().list(
                        q=search_query,
                        fields="files(id,name,description,webViewLink,modifiedTime,owners,mimeType,size,thumbnailLink)",
                        pageSize=min(max_results, 100),
                        orderBy="modifiedTime desc"
                    ).execute()
                
                result = await loop.run_in_executor(None, _search)
                files = result.get('files', [])
                
                search_results = []
                for file in files:
                    try:
                        # Extract owner information
                        owners = file.get('owners', [])
                        author = owners[0].get('displayName', 'Unknown') if owners else 'Unknown'
                        
                        # Generate snippet from description or file name
                        snippet = file.get('description', '')
                        if not snippet:
                            snippet = f"Document: {file.get('name', 'Untitled')} - {file.get('mimeType', 'Unknown type')}"
                        
                        # Determine access level (simplified)
                        access_level = "viewer"  # Default to viewer
                        if owners and any(owner.get('me', False) for owner in owners):
                            access_level = "owner"
                        
                        search_results.append(SearchResult(
                            id=f"gdrive:{file['id']}",
                            title=file.get('name', 'Untitled'),
                            snippet=snippet[:200] + "..." if len(snippet) > 200 else snippet,
                            url=file.get('webViewLink', ''),
                            source=DocumentSource.gdrive,
                            last_modified=file.get('modifiedTime', datetime.now().isoformat()),
                            author=author,
                            access_level=access_level
                        ))
                    except Exception as e:
                        logger.warning(f"Error processing search result: {e}")
                        continue
                
                logger.info(f"Found {len(search_results)} results in Google Drive")
                return search_results
            
            else:
                # Mock response for development
                return await self._get_mock_search_results(query, max_results)
                
        except HttpError as e:
            logger.error(f"Google Drive API error during search: {e}")
            if e.resp.status == 403:
                raise Exception("Google Drive API quota exceeded or access denied")
            elif e.resp.status == 401:
                raise Exception("Google Drive authentication failed")
            else:
                raise Exception(f"Google Drive API error: {e}")
        except Exception as e:
            logger.error(f"Error searching Google Drive: {e}")
            raise Exception(f"Failed to search Google Drive: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((HttpError, Exception))
    )
    async def get_document(self, doc_id: str) -> DocumentContent:
        """Get document content from Google Drive"""
        logger.info(f"Fetching Google Drive document: {doc_id}")
        
        try:
            service = await self._get_service()
            
            if not service and self.use_production_api:
                logger.error("Google Drive service not available")
                raise Exception("Google Drive service not available")
            
            if service:
                # Production API call
                loop = asyncio.get_event_loop()
                
                # Get file metadata
                def _get_metadata():
                    return service.files().get(
                        fileId=doc_id,
                        fields="id,name,description,webViewLink,modifiedTime,owners,mimeType,size"
                    ).execute()
                
                metadata = await loop.run_in_executor(None, _get_metadata)
                
                # Get file content based on MIME type
                content = ""
                mime_type = metadata.get('mimeType', '')
                
                if mime_type in self.SUPPORTED_MIME_TYPES:
                    export_mime_type = self.SUPPORTED_MIME_TYPES[mime_type]
                    
                    def _get_content():
                        if mime_type.startswith('application/vnd.google-apps'):
                            # Export Google Workspace documents
                            return service.files().export(
                                fileId=doc_id,
                                mimeType=export_mime_type
                            ).execute()
                        else:
                            # Get binary files
                            return service.files().get_media(fileId=doc_id).execute()
                    
                    try:
                        content_bytes = await loop.run_in_executor(None, _get_content)
                        if isinstance(content_bytes, bytes):
                            content = content_bytes.decode('utf-8', errors='ignore')
                        else:
                            content = str(content_bytes)
                    except Exception as e:
                        logger.warning(f"Could not extract content from document {doc_id}: {e}")
                        content = f"Content not available for {mime_type} files"
                else:
                    content = f"Unsupported file type: {mime_type}"
                
                # Extract owner information
                owners = metadata.get('owners', [])
                author = owners[0].get('displayName', 'Unknown') if owners else 'Unknown'
                
                return DocumentContent(
                    id=f"gdrive:{metadata['id']}",
                    title=metadata.get('name', 'Untitled'),
                    content=content[:10000],  # Limit content size
                    source=DocumentSource.gdrive,
                    url=metadata.get('webViewLink', ''),
                    last_modified=metadata.get('modifiedTime', datetime.now().isoformat()),
                    author=author
                )
            
            else:
                # Mock response for development
                return await self._get_mock_document_content(doc_id)
                
        except HttpError as e:
            logger.error(f"Google Drive API error fetching document {doc_id}: {e}")
            if e.resp.status == 404:
                raise Exception(f"Document {doc_id} not found")
            elif e.resp.status == 403:
                raise Exception(f"Access denied to document {doc_id}")
            else:
                raise Exception(f"Google Drive API error: {e}")
        except Exception as e:
            logger.error(f"Error fetching Google Drive document {doc_id}: {e}")
            raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((HttpError, Exception))
    )
    async def get_recent_updates(self, days: int) -> List[RecentUpdate]:
        """Get recent updates from Google Drive"""
        logger.info(f"Getting Google Drive updates from the last {days} days")
        
        try:
            service = await self._get_service()
            
            if not service and self.use_production_api:
                logger.error("Google Drive service not available")
                return []
            
            if service:
                # Production API call
                cutoff_date = datetime.now() - timedelta(days=days)
                cutoff_date_str = cutoff_date.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
                
                query = f"modifiedTime >= '{cutoff_date_str}' and trashed=false"
                
                loop = asyncio.get_event_loop()
                
                def _get_updates():
                    return service.files().list(
                        q=query,
                        fields="files(id,name,description,webViewLink,modifiedTime,owners,lastModifyingUser,createdTime)",
                        orderBy="modifiedTime desc",
                        pageSize=50
                    ).execute()
                
                result = await loop.run_in_executor(None, _get_updates)
                files = result.get('files', [])
                
                updates = []
                for file in files:
                    try:
                        # Determine update type
                        created_time = datetime.fromisoformat(file.get('createdTime', '').replace('Z', '+00:00'))
                        modified_time = datetime.fromisoformat(file.get('modifiedTime', '').replace('Z', '+00:00'))
                        
                        update_type = "created" if (modified_time - created_time).total_seconds() < 60 else "modified"
                        
                        # Get modifier information
                        last_modifying_user = file.get('lastModifyingUser', {})
                        author = last_modifying_user.get('displayName', 'Unknown')
                        
                        # Generate snippet
                        snippet = file.get('description', '')
                        if not snippet:
                            action = "Created" if update_type == "created" else "Modified"
                            snippet = f"{action} document: {file.get('name', 'Untitled')}"
                        
                        updates.append(RecentUpdate(
                            id=f"gdrive:{file['id']}",
                            title=file.get('name', 'Untitled'),
                            snippet=snippet[:200] + "..." if len(snippet) > 200 else snippet,
                            url=file.get('webViewLink', ''),
                            source=DocumentSource.gdrive,
                            last_modified=file.get('modifiedTime', datetime.now().isoformat()),
                            author=author,
                            update_type=update_type
                        ))
                    except Exception as e:
                        logger.warning(f"Error processing update: {e}")
                        continue
                
                logger.info(f"Found {len(updates)} recent updates in Google Drive")
                return updates
            
            else:
                # Mock response for development
                return await self._get_mock_recent_updates(days)
                
        except HttpError as e:
            logger.error(f"Google Drive API error getting updates: {e}")
            if e.resp.status == 403:
                raise Exception("Google Drive API quota exceeded or access denied")
            else:
                raise Exception(f"Google Drive API error: {e}")
        except Exception as e:
            logger.error(f"Error getting Google Drive updates: {e}")
            raise Exception(f"Failed to get recent updates from Google Drive: {e}")
    
    # Mock methods for development
    async def _get_mock_search_results(self, query: str, max_results: int) -> List[SearchResult]:
        """Mock search results for development"""
        logger.info(f"Returning mock Google Drive search results for: '{query}'")
        
        mock_results = [
            SearchResult(
                id="gdrive:1BxY2zW3vU4sR5qP6oN7mL8kJ9hG",
                title=f"Project Document - {query}",
                snippet=f"This document contains comprehensive information about {query} including project details, timelines, and deliverables. Last updated with new requirements and scope changes.",
                url="https://docs.google.com/document/d/1BxY2zW3vU4sR5qP6oN7mL8kJ9hG/edit",
                source=DocumentSource.gdrive,
                last_modified=datetime.now().isoformat(),
                author="John Smith",
                access_level="editor"
            ),
            SearchResult(
                id="gdrive:2CyZ3xW4vU5sR6qP7oN8mL9kJ0hG",
                title=f"Meeting Notes - {query} Discussion",
                snippet=f"Detailed notes from the {query} meeting held last week. Includes action items, decisions made, and follow-up tasks assigned to team members.",
                url="https://docs.google.com/document/d/2CyZ3xW4vU5sR6qP7oN8mL9kJ0hG/edit",
                source=DocumentSource.gdrive,
                last_modified=(datetime.now() - timedelta(days=2)).isoformat(),
                author="Sarah Johnson",
                access_level="viewer"
            ),
            SearchResult(
                id="gdrive:3DzA4yX5wV6tS7rQ8pO9nM0lK1iH",
                title=f"{query} Presentation",
                snippet=f"Slide deck for the {query} presentation to stakeholders. Contains charts, graphs, and key metrics showing project progress and outcomes.",
                url="https://docs.google.com/presentation/d/3DzA4yX5wV6tS7rQ8pO9nM0lK1iH/edit",
                source=DocumentSource.gdrive,
                last_modified=(datetime.now() - timedelta(hours=6)).isoformat(),
                author="Mike Chen",
                access_level="editor"
            )
        ]
        
        return mock_results[:max_results]
    
    async def _get_mock_document_content(self, doc_id: str) -> DocumentContent:
        """Mock document content for development"""
        logger.info(f"Returning mock Google Drive document content for: {doc_id}")
        
        return DocumentContent(
            id=f"gdrive:{doc_id}",
            title="Project Proposal Document",
            content="""# Project Proposal: Workplace Search Enhancement

## Executive Summary
This document outlines the comprehensive plan for enhancing our workplace search capabilities by integrating multiple document sources including Google Drive, Notion, Slack, and Confluence.

## Project Objectives
1. Improve document discoverability across platforms
2. Reduce time spent searching for information
3. Enhance team collaboration and knowledge sharing
4. Implement secure, role-based access controls

## Technical Architecture
The solution will implement a Model Context Protocol (MCP) server that provides unified search capabilities across:
- Google Drive documents and files
- Notion pages and databases
- Slack messages and files
- Confluence spaces and pages

## Implementation Timeline
- Phase 1: Core MCP server development (4 weeks)
- Phase 2: Google Drive integration (2 weeks)
- Phase 3: Additional source integrations (6 weeks)
- Phase 4: Testing and deployment (2 weeks)

## Resource Requirements
- 2 Senior developers
- 1 DevOps engineer
- 1 Product manager
- Cloud infrastructure costs: $500/month

## Expected Outcomes
- 60% reduction in document search time
- Improved team productivity
- Better knowledge management
- Enhanced security and compliance""",
            source=DocumentSource.gdrive,
            url=f"https://docs.google.com/document/d/{doc_id}/edit",
            last_modified=datetime.now().isoformat(),
            author="Project Team"
        )
    
    async def _get_mock_recent_updates(self, days: int) -> List[RecentUpdate]:
        """Mock recent updates for development"""
        logger.info(f"Returning mock Google Drive recent updates for last {days} days")
        
        base_time = datetime.now()
        
        mock_updates = [
            RecentUpdate(
                id="gdrive:1BxY2zW3vU4sR5qP6oN7mL8kJ9hG",
                title="Q4 Budget Planning",
                snippet="Updated quarterly budget allocations and revised spending projections based on current market conditions.",
                url="https://docs.google.com/spreadsheets/d/1BxY2zW3vU4sR5qP6oN7mL8kJ9hG/edit",
                source=DocumentSource.gdrive,
                last_modified=(base_time - timedelta(hours=2)).isoformat(),
                author="Finance Team",
                update_type="modified"
            ),
            RecentUpdate(
                id="gdrive:2CyZ3xW4vU5sR6qP7oN8mL9kJ0hG",
                title="Team Performance Review Template",
                snippet="Created new template for annual performance reviews with updated criteria and evaluation metrics.",
                url="https://docs.google.com/document/d/2CyZ3xW4vU5sR6qP7oN8mL9kJ0hG/edit",
                source=DocumentSource.gdrive,
                last_modified=(base_time - timedelta(days=1)).isoformat(),
                author="HR Department",
                update_type="created"
            ),
            RecentUpdate(
                id="gdrive:3DzA4yX5wV6tS7rQ8pO9nM0lK1iH",
                title="Project Timeline Update",
                snippet="Revised project milestones and deliverable dates to accommodate new requirements and resource constraints.",
                url="https://docs.google.com/document/d/3DzA4yX5wV6tS7rQ8pO9nM0lK1iH/edit",
                source=DocumentSource.gdrive,
                last_modified=(base_time - timedelta(days=2, hours=5)).isoformat(),
                author="Project Manager",
                update_type="modified"
            )
        ]
        
        # Filter based on days parameter
        cutoff_date = base_time - timedelta(days=days)
        return [
            update for update in mock_updates 
            if datetime.fromisoformat(update.last_modified.replace('Z', '+00:00')) > cutoff_date
        ]


# OAuth Setup Utility
async def setup_google_drive_oauth():
    """Utility function to set up Google Drive OAuth credentials"""
    print("Setting up Google Drive OAuth...")
    
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    
    if not os.path.exists(credentials_path):
        print(f"""
Google Drive OAuth Setup Required:

1. Go to the Google Cloud Console (https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Drive API
4. Create credentials (OAuth 2.0 Client ID)
5. Download the credentials JSON file
6. Save it as '{credentials_path}'

For detailed instructions, visit:
https://developers.google.com/drive/api/quickstart/python
        """)
        return False
    
    oauth_handler = GoogleDriveOAuthHandler(credentials_path)
    
    try:
        # Start OAuth flow
        flow = Flow.from_client_secrets_file(credentials_path, oauth_handler.scopes)
        flow.redirect_uri = 'http://localhost:8080'
        
        auth_url, _ = flow.authorization_url(prompt='consent')
        
        print(f"""
OAuth Setup:

1. Open this URL in your browser:
{auth_url}

2. Complete the authorization process
3. Copy the authorization code from the redirect URL
4. Paste it here:
        """)
        
        auth_code = input("Authorization code: ").strip()
        
        # Exchange authorization code for credentials
        flow.fetch_token(code=auth_code)
        
        # Save credentials
        with open(oauth_handler.token_path, 'w') as token_file:
            token_file.write(flow.credentials.to_json())
        
        print(f"✅ Google Drive OAuth setup complete! Credentials saved to {oauth_handler.token_path}")
        return True
        
    except Exception as e:
        print(f"❌ OAuth setup failed: {e}")
        return False


if __name__ == "__main__":
    # Run OAuth setup if called directly
    asyncio.run(setup_google_drive_oauth())
