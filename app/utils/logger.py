import os
import logging
import logging.config
from logging.handlers import RotatingFileHandler
import sys
from pathlib import Path

# Configure the logger
def setup_logger():
    # Get log level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Check if logging config file exists
    if os.path.exists("logging.conf"):
        # Use logging config file
        logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
        logger = logging.getLogger("workplace-search-agent")
        logger.info("Logger initialized using logging.conf")
    else:
        # Manual configuration
        # Create logger
        logger = logging.getLogger("workplace-search-agent")
        logger.setLevel(getattr(logging, log_level))
        
        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"
        )
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Create logs directory if it doesn't exist
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Create file handler
        file_handler = RotatingFileHandler(
            log_dir / "workplace-search-agent.log",
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        logger.info("Logger initialized with manual configuration")
        
        # Create file handlers for error.log and combined.log
        error_handler = RotatingFileHandler(
            "error.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        logger.addHandler(error_handler)
        
        combined_handler = RotatingFileHandler(
            "combined.log",
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=5,
        )
        combined_handler.setFormatter(formatter)
        logger.addHandler(combined_handler)
    
    return logger

# Create logger instance
logger = setup_logger()
