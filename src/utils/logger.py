"""
Logging configuration.
"""
import sys
from pathlib import Path
from loguru import logger


def setup_logging(log_dir: str = "logs", log_level: str = "INFO"):
    """
    Configure logging for the application.

    Args:
        log_dir: Directory to store log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    # Create logs directory
    Path(log_dir).mkdir(exist_ok=True)

    # Remove default handler
    logger.remove()

    # Console handler (colorized)
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )

    # File handler for general logs
    logger.add(
        f"{log_dir}/app.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
    )

    # File handler for errors only
    logger.add(
        f"{log_dir}/errors.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="10 MB",
        retention="90 days",
        compression="zip",
    )

    logger.info("Logging configured successfully")
