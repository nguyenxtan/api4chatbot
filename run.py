"""
Main entry point for running the API server.
"""
import uvicorn
from src.utils.logger import setup_logging


if __name__ == "__main__":
    # Setup logging
    setup_logging(log_dir="logs", log_level="INFO")

    # Run server
    uvicorn.run(
        "src.api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Set to False in production
        log_level="info",
    )
