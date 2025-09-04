import logging
import sys
from loguru import logger
from typing import Dict, Any
import os


class InterceptHandler(logging.Handler):
    """Intercept standard logging messages toward loguru"""
    
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(level: str = "INFO", log_file: str = None):
    """Setup logging configuration"""
    
    # Remove default handler
    logger.remove()
    
    # Add console handler
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # Add file handler if specified
    if log_file:
        logger.add(
            log_file,
            level=level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="1 week",
            compression="zip"
        )
    
    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Set levels for external libraries
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO) 
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)


# Initialize logging
log_level = os.getenv("LOG_LEVEL", "INFO")
log_file = os.getenv("LOG_FILE")
setup_logging(log_level, log_file)

# Export logger instance
__all__ = ["logger"]
