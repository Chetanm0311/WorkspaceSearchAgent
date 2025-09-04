import asyncio
from app.auth.descope_auth import DescopeAuthenticator
from app.adapters.google_drive_adapter import  GoogleDriveOAuthHandler
import os
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
load_dotenv()
async def main():
    descope_auth = DescopeAuthenticator()
    result = await descope_auth.authenticate_user("chetanmm0311@gmail.com","h8s8D;soC4H61Zpgvyrd")
    data = await descope_auth.verify_token(result['token'])
    print(data)


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
        flow.redirect_uri = 'http://localhost:8000'
        
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
    asyncio.run(setup_google_drive_oauth())
