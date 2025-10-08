import logging
import logging.handlers
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.service_agent.foundation.config import Config


# ============ Logging Configuration ============
def setup_logging():
    """Configure structured logging for the application"""

    # Ensure log directory exists
    Config.LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Root logger configuration
    log_format = Config.LOGGING.get("format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    date_format = Config.LOGGING.get("date_format", "%Y-%m-%d %H:%M:%S")
    log_level = Config.LOGGING.get("level", "INFO")

    # Create formatter
    formatter = logging.Formatter(log_format, datefmt=date_format)

    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)

    # File handler (rotating)
    log_file = Config.LOG_DIR / "app.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=100 * 1024 * 1024,  # 100MB
        backupCount=7
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Set specific log levels for modules
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("app.service_agent").setLevel(logging.DEBUG)  # Detailed service_agent logs
    logging.getLogger("app.api").setLevel(logging.INFO)

    logging.info("=" * 80)
    logging.info("Logging configured successfully")
    logging.info(f"Log level: {log_level}")
    logging.info(f"Log file: {log_file}")
    logging.info("=" * 80)


# Setup logging before app initialization
setup_logging()

app = FastAPI(
    title="Chatbot App API",
    description="부동산 AI 챗봇 <도와줘 홈즈냥즈>",
    version="0.0.1"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers
from app.api.chat_api import router as chat_router
from app.api.error_handlers import register_error_handlers

# Include routers
app.include_router(chat_router)

# Register error handlers
register_error_handlers(app)

@app.get("/")
async def root():
    return {"message": "홈즈냥즈 API Server Running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
