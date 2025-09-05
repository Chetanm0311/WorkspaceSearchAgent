# AI-Powered Workplace Search - WorkplaceSearchAgent MCP Server[Hackathon: https://www.hackerearth.com/challenges/hackathon/mcp-hackathon]

## Project Description
A comprehensive **Model Context Protocol (MCP) server** that enables AI agents to search, retrieve, and summarize content from workplace tools including Google Drive, Notion, Slack, and Confluence. This remote MCP server allows Claude Desktop to seamlessly interact with your workplace documents through secure, authenticated connections while maintaining proper user permissions and access scopes.

## Team Information
**Team Name:** Team Lewok

**Team Members:**
- Chetan Mali
- Abhijeet Rajput

## Hackathon Theme
**Theme 2: Secure Agent-API Interface Layer**

This project addresses the critical challenge of creating a reliable, secure interface layer for autonomous agents to interact with real-world APIs. As agents transition from research to production environments, they require robust identity, scoping, and trust frameworks to operate autonomously at scale. Our MCP server serves as a foundational building block in this new software architecture, enabling agents to safely invoke tools and automate operations with integrated Descope authentication and Cequence MCP proxy security.

# YouTube Link
https://youtu.be/SqHEs32dtBQ?si=rBs-IuEbRcR0giB8

## What We Built

### Core Features
- **🔍 Universal Workplace Search**: Unified search across Google Drive, Notion, Slack, and Confluence
- **📄 Document Content Retrieval**: Read full content of specific documents with proper formatting
- **🤖 AI-Powered Summarization**: Extract key points and generate summaries from retrieved documents
- **🔐 Secure Authentication**: User-specific access control using Descope authentication framework
- **🛡️ Proxy Security**: All agent interactions secured through Cequence MCP proxy
- **⏰ Recent Updates Tracking**: Pull and display recently modified documents across platforms
- **🎯 Smart Query Processing**: Natural language understanding for complex search requests

### Available Tools for Claude Desktop

#### 1. Search Google Drive
- **Functionality**: Natural language search across all Google Drive documents
- **Usage**: "Search my Google Drive for quarterly reports" or "Find documents about project timeline"
- **Returns**: Structured results with document metadata, summaries, and direct links

#### 2. Get Document Content
- **Functionality**: Retrieve full content of specific documents by ID
- **Usage**: "Read the content of document ID 1BxY2zW3vU4sR5qP6oN7mL8kJ9hG"
- **Returns**: Complete document content with formatting and metadata

#### 3. Recent Updates Monitor
- **Functionality**: Display recently modified or created documents
- **Usage**: "Show me documents updated in the last 7 days"
- **Returns**: Chronological list of recent changes across connected platforms

#### 4. Document Summarization
- **Functionality**: Generate intelligent summaries of workplace documents
- **Usage**: "Summarize the Q4 budget document" or "Give me key points from the project proposal"
- **Returns**: Structured summaries with key insights and action items

### Architecture Components
1. **MCP Server Core**: Implements Model Context Protocol for seamless agent communication
2. **Authentication Layer**: Descope integration for secure, token-based user authentication
3. **Multi-Platform Adapters**: Individual adapters for Google Drive, Notion, Slack, and Confluence
4. **Security Proxy**: Cequence MCP proxy ensuring secure agent interactions
5. **Mock Development Services**: Full mock implementations for testing and development

## How to Run

### Prerequisites
- Python 3.8+
- Active internet connection for remote server access
- Google Drive account with API access
- Descope authentication credentials
- Claude Desktop application

### Quick Setup (2 minutes)

#### Step 1: Start the MCP Server
```bash
# Start the server on port 8000
python start_server.py
```
Server will be accessible at `http://localhost:8000`

#### Step 2: Configure Claude Desktop

**Option A: Automatic Configuration (Recommended)**
```bash
# Run the MCP client configuration
python claude_mcp_client.py
```

**Option B: Manual Configuration**
1. Locate Claude Desktop config file:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/claude/claude_desktop_config.json`

2. Add MCP server configuration:
```json
{
  "mcpServers": {
    "workplace-search-mcp": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8000/mcp"
      }
    }
  }
}
```

3. Restart Claude Desktop

#### Step 3: Google Drive OAuth Setup
```bash
# Run OAuth setup utility
python test.py
# Follow the interactive setup instructions
```

#### Step 4: Test the Connection
1. Open Claude Desktop
2. Start a new conversation
3. Ask: "Search my Google Drive for project documents"
4. Claude should now access your workplace tools!

### Development Setup
```bash
# Clone and install dependencies
git clone <repository-url>
cd WorkSpaceAgent_New
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and credentials

# Run tests
python -m pytest tests/
```

## Tech Stack

### Required Technologies (Core)
- **Python 3.8+**: Primary development language
- **Model Context Protocol (MCP)**: Standard for agent-tool communication
- **Descope**: Authentication and identity management platform
- **Cequence**: MCP security proxy for agent interactions

### Workplace API Integrations
- **Google Drive API**: Document search, retrieval, and metadata access
- **Notion API**: Workspace content and database access
- **Slack API**: Message search and channel content retrieval
- **Confluence API**: Knowledge base and wiki integration

### Development Libraries
- **asyncio**: Asynchronous programming for concurrent operations
- **dotenv**: Secure environment variable management
- **google-auth-oauthlib**: OAuth2 authentication flow implementation
- **googleapiclient**: Official Google API client library
- **httpx**: Modern HTTP client for API communications
- **pydantic**: Data validation and settings management

### Security and Authentication Stack
- **OAuth 2.0**: Industry-standard authorization framework
- **JWT Tokens**: Secure session and identity management
- **Scoped Permissions**: Granular, user-specific access control
- **HTTPS/TLS**: Encrypted data transmission
- **Proxy Layer**: Cequence MCP security proxy for agent protection

## Project Structure
```
WorkSpaceAgent_New/
├── app/
│   ├── auth/
│   │   └── descope_auth.py          # Descope authentication handler
|   |   |── cequence_gateway.py      # Cequence Gateway Handler
|   |   ├── security.py              # Security Layer
│   ├── adapters/
│   │   ├── google_drive_adapter.py  # Google Drive integration
│   └── utils/
|       ├── logger.py                # Logger
├── start_server.py                 # Server startup script
├── claude_mcp_client.py           # Claude Desktop configuration
├── test.py                        # OAuth setup and testing
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment template
└── USER_GUIDE.md                 # End-user documentation
```

## Usage Examples

### Basic Workplace Search
```
User: "Search my Google Drive for budget documents"

Claude: I'll search your Google Drive for budget documents.

Found 3 documents:

1. **Q4 Budget Planning**
   Author: Finance Team
   Last Modified: 2025-09-01T14:30:00Z
   Summary: Updated quarterly budget allocations for Q4...
   Document ID: 1BxY2zW3vU4sR5qP6oN7mL8kJ9hG
```

### Smart Content Analysis
```
User: "Find all documents related to the marketing campaign and summarize key points"

Claude: Found 5 marketing campaign documents. Here are the key insights:

**Campaign Strategy Overview:**
- Target audience: 25-45 professionals
- Budget allocation: $50K digital, $30K traditional
- Timeline: Q4 2025 launch

**Action Items:**
- Creative assets due Sept 15
- Media buy confirmation needed
- Analytics dashboard setup required
```

## Privacy & Security

### Data Access Model
- **Read-only permissions**: Server can only read existing files, no modification capabilities
- **Scope-limited access**: Only accesses files user has explicit permission to view
- **No persistent storage**: Document content is not cached or stored on server
- **Audit trail**: All access logged for security compliance

### Authentication Security
- **OAuth 2.0 standard**: Industry-standard authorization without credential sharing
- **Token-based access**: Secure, time-limited access tokens
- **User consent**: Explicit user authorization for each connected service
- **Revocable permissions**: Users can revoke access at any time

### Data Transmission
- **HTTPS encryption**: All communications use TLS encryption
- **No data logging**: File content not permanently logged or stored
- **Minimal data transfer**: Only requested content and metadata transmitted
- **Secure proxy**: Cequence MCP proxy adds additional security layer

## Innovation Highlights

This project represents a significant advancement in secure agent-API interaction patterns:

1. **First-class MCP Implementation**: Native Model Context Protocol support for seamless agent integration
2. **Multi-platform Abstraction**: Unified interface across diverse workplace tools
3. **Security-first Design**: Built-in authentication, authorization, and audit capabilities
4. **Production-ready Architecture**: Scalable, maintainable codebase with comprehensive testing
5. **Developer Experience**: Simple setup, clear documentation, and robust error handling

## Future Roadmap

- **Additional Platform Support**: Teams, Asana, Jira integration
- **Advanced AI Features**: Semantic search, content recommendations
- **Enterprise Features**: SSO integration, advanced audit logging
- **Performance Optimization**: Caching, batch operations, real-time updates
- **Mobile Support**: Mobile app integration and responsive design

---

*This project demonstrates how AI agents can securely and efficiently access workplace knowledge, providing a robust foundation for the next generation of autonomous workplace assistance while maintaining the highest standards of security and user
