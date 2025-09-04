#!/usr/bin/env python3
"""
Google Drive MCP Server Entry Point

This script can run the server in different modes:
- MCP mode: stdio-based MCP server for Claude Desktop
- HTTP mode: FastAPI server for web deployment
"""

import sys
import os
import asyncio
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


def run_remote_mcp_server():
    """Run the remote MCP server"""
    logger.info("Starting Enhanced Remote Google Drive MCP Server...")
    
    import uvicorn
    from app.remote_mcp_server import app
    
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Google Drive MCP Server")
    parser.add_argument(
        "--setup-oauth",
        action="store_true",
        help="Setup Google Drive OAuth credentials"
    )
    
    args = parser.parse_args()
    
    # Setup environment
    setup_environment()
    
    if args.setup_oauth:
        # Run OAuth setup
        from app.adapters.google_drive_adapter import setup_google_drive_oauth
        asyncio.run(setup_google_drive_oauth())
        return
    run_remote_mcp_server()


if __name__ == "__main__":
    main()
