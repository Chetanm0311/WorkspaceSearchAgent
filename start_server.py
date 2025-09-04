#!/usr/bin/env python3
"""
Start the Workplace Search MCP HTTP Server
"""

import os
import sys
import argparse
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.utils.logger import logger


def setup_environment():
    """Setup environment variables"""
    # Load .env file if it exists
    env_file = Path(".env")
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
    
    # Set default values
    os.environ.setdefault("GOOGLE_DRIVE_PRODUCTION", "true")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("PORT", "8000")
    os.environ.setdefault("HOST", "0.0.0.0")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Workplace Search MCP HTTP Server")
    parser.add_argument("--host", default=os.getenv("HOST", "0.0.0.0"), help="Host to bind to")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()
    
    setup_environment()
    
    logger.info("Starting Workplace Search MCP HTTP Server...")
    logger.info(f"Server will be accessible at http://{args.host}:{args.port}")
    logger.info("Available endpoints:")
    logger.info("  - GET  /health - Health check")
    logger.info("  - GET  /mcp/info - MCP server information")
    logger.info("  - POST /mcp/tools - List available tools")
    logger.info("  - POST /mcp/call-tool - Call MCP tools")
    logger.info("  - POST /auth/login - User authentication")
    logger.info("  - POST /search - Search documents")
    logger.info("  - POST /document - Get document content")
    
    import uvicorn
    from app.remote_mcp_server import app
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )


if __name__ == "__main__":
    main()
