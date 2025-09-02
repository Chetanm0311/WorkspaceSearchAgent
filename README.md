# WorkplaceSearchAgent MCP Server - User Guide

This comprehensive guide will walk you through setting up and running the WorkplaceSearchAgent MCP (Model Context Protocol) server, which enables AI agents to search and retrieve content from workplace tools like Google Drive, Notion, Slack, and Confluence.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Google Drive Setup](#google-drive-setup)
- [Other Service Setup](#other-service-setup)
- [Running the Server](#running-the-server)
- [Testing the Setup](#testing-the-setup)
- [API Usage](#api-usage)
- [MCP Client Integration](#mcp-client-integration)
- [Docker Deployment](#docker-deployment)
- [Troubleshooting](#troubleshooting)

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.9 or higher** - Check with `python --version`
- **Git** - For cloning the repository
- **Administrator privileges** - For installing dependencies
- **Access to workplace services** you want to integrate:
  - Google Drive account
  - Notion workspace (optional)
  - Slack workspace (optional) 
  - Confluence instance (optional)

## Installation

### 1. Clone the Repository

```powershell
git clone https://github.com/Chetanm0311/WorkspaceSearchAgent.git -o WorkSpaceAgent
cd WorkSpaceAgent
```

### 2. Create Virtual Environment

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Verify activation (you should see (venv) in your prompt)
```

### 3. Install Dependencies

```powershell
# Install Python packages
pip install -r requirements.txt

# Verify installation
pip list
```

## Configuration

### 1. Environment Setup

Copy the example environment file and configure it:

```powershell
copy .env.example .env
```

Edit `.env` file with your preferred text editor and configure the following sections:

#### Basic Server Configuration
```env
PORT=8000
ENVIRONMENT=development
LOG_LEVEL=INFO
```

#### Authentication (Optional)
```env
# Set to true if you want to enable Descope authentication
AUTH_ENABLED=false
DESCOPE_BASE_URL=https://api.descope.com
DESCOPE_PROJECT_ID=your_descope_project_id_here
DESCOPE_API_KEY=your_descope_api_key_here
```

#### Security (Optional)
```env
# Set to true if you want to enable Cequence MCP proxy
CEQUENCE_ENABLED=false
CEQUENCE_API_KEY=your_cequence_api_key_here
```

#### Cache Settings
```env
CACHE_ENABLED=true
SEARCH_CACHE_TTL=300
DOCUMENT_CACHE_TTL=600
UPDATES_CACHE_TTL=300
```

## Google Drive Setup

Google Drive is the primary integration and requires OAuth 2.0 setup.

### 1. Google Cloud Console Setup

1. **Go to [Google Cloud Console](https://console.cloud.google.com/)**

2. **Create or Select Project**
   - Create a new project or select an existing one
   - Note the project ID for later use

3. **Enable Google Drive API**
   - Navigate to **APIs & Services > Library**
   - Search for "Google Drive API"
   - Click **Enable**

4. **Create OAuth 2.0 Credentials**
   - Go to **APIs & Services > Credentials**
   - Click **Create Credentials > OAuth 2.0 Client ID**
   - If prompted, configure the OAuth consent screen:
     - Choose **External** user type (for testing)
     - Fill in required fields:
       - App name: "WorkplaceSearchAgent"
       - User support email: Your email
       - Developer contact information: Your email
     - Add your email to test users
     - Save and continue through all steps
   - Back to Create Credentials:
     - Select **Desktop Application** as the application type
     - Name it "WorkplaceSearchAgent Client"
     - Click **Create**

5. **Download Credentials**
   - Download the JSON credentials file
   - **Important**: Save it as `credentials.json` in your project root directory (`c:\WorkSpaceAgent\credentials.json`)

### 2. Update Google Drive Configuration

In your `.env` file, update the Google Drive section:

```env
# Enable production Google Drive API
GOOGLE_DRIVE_PRODUCTION=true
GOOGLE_CREDENTIALS_PATH=credentials.json
GOOGLE_TOKEN_PATH=token.json
```

### 3. OAuth Authorization

Run the Google Drive OAuth setup script:

```powershell
# Ensure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Run OAuth setup
python setup_google_oauth.py
```

This script will:
1. Check for your credentials file
2. Open a browser window for Google authorization
3. Guide you through the OAuth flow
4. Save authentication tokens to `token.json`

**Important OAuth Redirect URI Fix:**
If you encounter redirect URI issues, update your Google Cloud Console:
1. Go to **APIs & Services > Credentials**
2. Edit your OAuth 2.0 Client ID
3. In **Authorized redirect URIs**, add:
   - `http://localhost:8080`
   - `http://localhost`

## Other Service Setup

### Notion Integration (Optional)

1. **Create Notion Integration**
   - Go to [Notion Developers](https://developers.notion.com/)
   - Create new integration
   - Copy the API key

2. **Update .env**
   ```env
   NOTION_API_KEY=your_notion_api_key_here
   ```

### Slack Integration (Optional)

1. **Create Slack App**
   - Go to [Slack API](https://api.slack.com/apps)
   - Create new app
   - Get Bot User OAuth Token

2. **Update .env**
   ```env
   SLACK_API_TOKEN=xoxb-your-slack-bot-token
   ```

### Confluence Integration (Optional)

1. **Get API Token**
   - Go to Atlassian Account Settings
   - Create API token

2. **Update .env**
   ```env
   CONFLUENCE_USERNAME=your_confluence_username
   CONFLUENCE_API_TOKEN=your_confluence_api_token
   ```

## Running the Server

You have several options to start the server:

### Option 1: Using PowerShell Script (Recommended)

```powershell
.\start_server.ps1
```

### Option 2: Using Batch File

```cmd
start_server.bat
```

### Option 3: Manual Start

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start server
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info
```

### Option 4: Development Mode (Auto-reload)

```powershell
# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Start with auto-reload for development
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### Option 5: Using VS Code Task

If you're using VS Code, you can use the pre-configured task:
- Press `Ctrl+Shift+P`
- Type "Tasks: Run Task"
- Select "Start Python MCP Server (Dev Mode)"

The server will start and you should see output like:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
```

## Testing the Setup

### 1. Test Google Drive Integration

```powershell
# Run comprehensive Google Drive test
python test_google_drive_final.py
```

This will test:
- OAuth authentication
- File search functionality
- Document content retrieval
- Recent updates tracking

### 2. Test API Endpoints

Open your browser and navigate to:

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### 3. Test Search Functionality

```powershell
# Quick search test
python quick_search_test.py
```

## API Usage

### REST API Endpoints

The server provides REST API endpoints that can be used directly:

#### 1. Search Documents
```http
POST http://localhost:8000/search
Content-Type: application/json

{
    "query": "project documentation",
    "sources": ["gdrive", "notion"],
    "max_results": 10
}
```

#### 2. Summarize Content
```http
POST http://localhost:8000/summarize
Content-Type: application/json

{
    "document_ids": ["document_id_1", "document_id_2"],
    "max_length": 500
}
```

#### 3. Get Recent Updates
```http
POST http://localhost:8000/updates
Content-Type: application/json

{
    "sources": ["gdrive"],
    "days": 7,
    "max_results": 10
}
```

### Example Response Format

```json
{
    "results": [
        {
            "id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms",
            "title": "Project Documentation",
            "content": "This document contains...",
            "source": "gdrive",
            "url": "https://docs.google.com/document/d/...",
            "last_modified": "2025-09-01T10:30:00Z",
            "author": "user@example.com",
            "file_type": "application/vnd.google-apps.document"
        }
    ]
}
```

## MCP Client Integration

### Using as MCP Server

The server can also run as an MCP stdio server:

```powershell
# Run as MCP stdio server
python mcp_server.py
```

### MCP Functions Available

1. **search_documents**
   - Search across multiple knowledge sources
   - Parameters: query, sources, max_results, auth_token

2. **summarize_content**
   - Summarize retrieved documents
   - Parameters: document_ids, max_length, auth_token

3. **get_recent_updates**
   - Get recent changes and updates
   - Parameters: sources, days, max_results, auth_token

### Integration with LLM Clients

Configure your LLM client (like Claude Desktop) to use this MCP server by adding to your client configuration:

```json
{
  "mcpServers": {
    "workplace-search": {
      "command": "python",
      "args": ["c:/WorkSpaceAgent/mcp_server.py"],
      "cwd": "c:/WorkSpaceAgent"
    }
  }
}
```

## Docker Deployment

### Build and Run with Docker

```powershell
# Build Docker image
docker build -t workplace-search-agent .

# Run container
docker run -p 8000:8000 \
  -v ${PWD}/credentials.json:/app/credentials.json \
  -v ${PWD}/token.json:/app/token.json \
  -v ${PWD}/.env:/app/.env \
  workplace-search-agent
```

### Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'
services:
  workplace-search:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./credentials.json:/app/credentials.json:ro
      - ./token.json:/app/token.json
      - ./.env:/app/.env:ro
    environment:
      - ENVIRONMENT=production
    restart: unless-stopped
```

Run with:
```powershell
docker-compose up -d
```

## Troubleshooting

### Common Issues and Solutions

#### 1. OAuth Redirect URI Mismatch

**Error**: `redirect_uri_mismatch`

**Solution**: 
- Update Google Cloud Console OAuth credentials
- Add `http://localhost:8080` to authorized redirect URIs
- Ensure `credentials.json` matches console settings

#### 2. Missing Credentials File

**Error**: `credentials.json not found`

**Solution**:
- Download credentials from Google Cloud Console
- Save as `credentials.json` in project root
- Verify file path in `.env` file

#### 3. Permission Denied Errors

**Error**: `Permission denied` or `Access token expired`

**Solution**:
- Delete `token.json` file
- Run `python setup_google_oauth.py` again
- Complete OAuth flow in browser

#### 4. Module Import Errors

**Error**: `ModuleNotFoundError`

**Solution**:
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`
- Check Python path configuration

#### 5. Port Already in Use

**Error**: `Address already in use`

**Solution**:
- Change port in `.env` file: `PORT=8001`
- Or stop existing service on port 8000
- Use `netstat -ano | findstr :8000` to find process

#### 6. Google API Quota Exceeded

**Error**: `Quota exceeded`

**Solution**:
- Check Google Cloud Console quota limits
- Implement rate limiting in your application
- Consider upgrading to paid tier if needed

### Logs and Debugging

#### Enable Debug Logging

Update `.env`:
```env
LOG_LEVEL=DEBUG
```

#### Check Log Files

The application creates several log files:
- `combined.log` - All log messages
- `error.log` - Error messages only

#### Verbose Google Drive Testing

```powershell
# Run with detailed logging
python test_google_drive_final.py
```

### Getting Help

1. **Check Documentation**: Review this guide and `README.md`
2. **Review Logs**: Check `combined.log` and `error.log` files
3. **Test Components**: Use individual test scripts to isolate issues
4. **Verify Configuration**: Double-check `.env` and credentials files
5. **Update Dependencies**: Ensure all packages are up to date

## Security Considerations

### Production Deployment

1. **Enable Authentication**:
   ```env
   AUTH_ENABLED=true
   ```

2. **Use HTTPS**: Deploy behind reverse proxy with SSL
3. **Secure Credentials**: Use environment variables or secure vaults
4. **Network Security**: Restrict access to trusted networks
5. **Regular Updates**: Keep dependencies updated

### API Keys and Tokens

- Never commit `.env`, `credentials.json`, or `token.json` to version control
- Use separate credentials for development and production
- Rotate API keys regularly
- Monitor API usage and set up alerts

## Performance Optimization

### Caching

The server includes built-in caching:
- Search results cached for 5 minutes
- Document content cached for 10 minutes
- Updates cached for 5 minutes

Adjust cache settings in `.env`:
```env
SEARCH_CACHE_TTL=300
DOCUMENT_CACHE_TTL=600
UPDATES_CACHE_TTL=300
```

### Resource Limits

For production deployment, consider:
- Setting appropriate worker processes
- Configuring memory limits
- Implementing rate limiting
- Monitoring performance metrics

---

This completes the comprehensive user guide for setting up and running the WorkplaceSearchAgent MCP server. Follow the steps in order, and refer to the troubleshooting section if you encounter any issues.
