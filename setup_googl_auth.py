#!/usr/bin/env python3
"""
Google Drive OAuth Setup Script

This script helps you set up OAuth 2.0 authentication for Google Drive API.
Run this script to authorize the application and generate the required tokens.

Usage:
    python setup_google_oauth.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.adapters.google_drive_adapter import setup_google_drive_oauth


async def main():
    """Main setup function"""
    print("🔧 Google Drive OAuth Setup")
    print("=" * 50)
    
    # Check if credentials file exists
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    
    if not os.path.exists(credentials_path):
        print(f"""Credentials file not found: {credentials_path}

To get started, you need to:

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Create a new project or select existing one
3. Enable Google Drive API:
   - Go to APIs & Services > Library
   - Search for "Google Drive API"
   - Click Enable

4. Create OAuth 2.0 credentials:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client ID"
   - Select "Desktop Application"
   - Download the JSON file
   - Save it as '{credentials_path}' in this directory

5. Run this script again: python setup_google_oauth.py
        """)
        return False
    
    print(f"Found credentials file: {credentials_path}")
    
    # Run OAuth setup
    success = await setup_google_drive_oauth()
    
    if success:
        print(""" Setup Complete!

Your Google Drive integration is now ready. To enable production mode:

1. Update your .env file:
   GOOGLE_DRIVE_PRODUCTION=true

2. Restart your MCP server

The integration will now use real Google Drive API calls.
        """)
    else:
        print("""Setup failed. Please check:

1. Credentials file is valid JSON from Google Cloud Console
2. Google Drive API is enabled in your project
3. You have the correct permissions
4. Your internet connection is working

For help, visit: https://developers.google.com/drive/api/quickstart/python
        """)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
