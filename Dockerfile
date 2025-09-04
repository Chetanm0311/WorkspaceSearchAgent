# Multi-stage build for WorkplaceSearchAgent MCP Server
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_ENV=production
ARG APP_VERSION=1.0.0

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Remove development files in production
RUN if [ "$BUILD_ENV" = "production" ]; then \
    rm -rf tests/ \
    .pytest_cache/ \
    .git/ \
    *.md \
    .env.example; \
    fi

# Production stage
FROM python:3.11-slim as production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HOST=0.0.0.0 \
    PORT=8000 \
    LOG_LEVEL=INFO \
    GOOGLE_DRIVE_PRODUCTION=true

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser \
    && useradd -r -g appuser appuser

# Create app directory and set permissions
WORKDIR /app
RUN chown -R appuser:appuser /app

# Copy from builder stage
COPY --from=builder --chown=appuser:appuser /app /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Switch to non-root user
USER appuser

# Create necessary directories
RUN mkdir -p /app/logs /app/data

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Set entrypoint and command
ENTRYPOINT ["python", "start_server.py"]
CMD ["--host", "0.0.0.0", "--port", "8000"]

# Development stage
FROM production as development

# Switch back to root for development setup
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    vim \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install development Python packages
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    flake8 \
    mypy

# Copy development files back
COPY tests/ /app/tests/
COPY .env.example /app/.env.example
COPY pytest.ini /app/pytest.ini 2>/dev/null || true

# Set development environment variables
ENV LOG_LEVEL=DEBUG \
    GOOGLE_DRIVE_PRODUCTION=false

# Switch back to appuser
USER appuser

# Override command for development
CMD ["--host", "0.0.0.0", "--port", "8000", "--reload"]

# Labels for metadata
LABEL maintainer="WorkplaceSearchAgent Team" \
      version="1.0.0" \
      description="AI-Powered Workplace Search MCP Server" \
      org.opencontainers.image.title="WorkplaceSearchAgent MCP Server" \
      org.opencontainers.image.description="Model Context Protocol server for workplace search across Google Drive, Notion, Slack, and Confluence" \
      org.opencontainers.image.authors="Chetan Mali, Abhijeet Rajput" \
      org.opencontainers.image.source="https://github.com/your-org/workplace-search-agent" \
      org.opencontainers.image.version="1.0.0"
