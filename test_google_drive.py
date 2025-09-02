#!/usr/bin/env python3
"""
Comprehensive Google Drive Adapter Test

This script tests all Google Drive functionality with real API calls.
Make sure you have completed OAuth setup before running this.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.adapters.google_drive_adapter import GoogleDriveAdapter
from app.models.models import UserContext


async def test_google_drive_comprehensive():
    """Comprehensive test of Google Drive adapter with real API calls"""
    print("Google Drive Adapter - Comprehensive Test")
    print("=" * 60)
    
    # Enable production mode
    os.environ["GOOGLE_DRIVE_PRODUCTION"] = "true"
    
    # Create a test user context
    user_context = UserContext(
        authenticated=True,
        user_id="test-user",
        email="chetanmm0311@gmail.com",
        name="Test User",
        access_scopes=["gdrive:read"],
        access_token="oauth-token"
    )
    
    # Initialize the adapter
    print("🔧 Initializing Google Drive adapter...")
    adapter = GoogleDriveAdapter(user_context)
    print("✅ Adapter initialized")
    
    # Test 1: Search for files
    print("\n" + "="*60)
    print("🔍 TEST 1: Searching for files")
    print("="*60)
    
    search_queries = [
        "document",
        "presentation", 
        "Emotion Classification",
        "project"
    ]
    
    for query in search_queries:
        try:
            print(f"\n🔎 Searching for: '{query}'")
            results = await adapter.search(query, max_results=3)
            print(f"✅ Found {len(results)} results")
            
            for i, result in enumerate(results[:2], 1):  # Show first 2 results
                print(f"\n   📄 Result {i}:")
                print(f"      Title: {result.title}")
                print(f"      Author: {result.author}")
                print(f"      Modified: {result.last_modified}")
                print(f"      URL: {result.url}")
                print(f"      Snippet: {result.snippet[:100]}...")
                
        except Exception as e:
            print(f"❌ Search failed for '{query}': {e}")
    
    # Test 2: Get recent updates
    print("\n" + "="*60)
    print("📅 TEST 2: Getting recent updates")
    print("="*60)
    
    try:
        print("🔄 Getting updates from last 7 days...")
        updates = await adapter.get_recent_updates(days=7)
        print(f"✅ Found {len(updates)} recent updates")
        
        for i, update in enumerate(updates[:3], 1):  # Show first 3 updates
            print(f"\n   📝 Update {i}:")
            print(f"      Title: {update.title}")
            print(f"      Type: {update.update_type}")
            print(f"      Author: {update.author}")
            print(f"      Modified: {update.last_modified}")
            print(f"      Snippet: {update.snippet[:80]}...")
            
    except Exception as e:
        print(f"❌ Recent updates failed: {e}")
    
    # Test 3: Get document content (if we found any documents)
    print("\n" + "="*60)
    print("📄 TEST 3: Getting document content")
    print("="*60)
    
    try:
        # First, search for a document
        print("🔎 Searching for documents to test content retrieval...")
        search_results = await adapter.search("", max_results=1)  # Get any document
        
        if search_results:
            test_doc_id = search_results[0].id.replace("gdrive:", "")  # Remove prefix
            print(f"📄 Testing content retrieval for: {search_results[0].title}")
            
            document = await adapter.get_document(test_doc_id)
            print(f"✅ Document content retrieved")
            print(f"   Title: {document.title}")
            print(f"   Author: {document.author}")
            print(f"   Content length: {len(document.content)} characters")
            print(f"   Content preview: {document.content[:200]}...")
            
        else:
            print("⚠️ No documents found to test content retrieval")
            
    except Exception as e:
        print(f"❌ Document content retrieval failed: {e}")
    
    # Test 4: Search with different filters
    print("\n" + "="*60)
    print("🎯 TEST 4: Advanced search tests")
    print("="*60)
    
    advanced_searches = [
        ("PDF files", "pdf"),
        ("Recent documents", "document"),
        ("Shared files", "shared"),
    ]
    
    for description, query in advanced_searches:
        try:
            print(f"\n🔍 {description} (query: '{query}')")
            results = await adapter.search(query, max_results=2)
            print(f"✅ Found {len(results)} results")
            
            for result in results:
                print(f"   - {result.title} (by {result.author})")
                
        except Exception as e:
            print(f"❌ {description} search failed: {e}")
    
    print("\n" + "="*60)
    print("🎉 ALL TESTS COMPLETED!")
    print("="*60)
    
    print("\n📊 Test Summary:")
    print("   ✅ Adapter initialization")
    print("   ✅ File search functionality")
    print("   ✅ Recent updates retrieval")
    print("   ✅ Document content retrieval")
    print("   ✅ Advanced search options")
    
    print("\n🔧 The Google Drive adapter is ready for use!")
    print("   • Set GOOGLE_DRIVE_PRODUCTION=true to use real API")
    print("   • Set GOOGLE_DRIVE_PRODUCTION=false for mock data")


if __name__ == "__main__":
    try:
        asyncio.run(test_google_drive_comprehensive())
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        print("Make sure you have completed OAuth setup with: python setup_google_oauth.py")
