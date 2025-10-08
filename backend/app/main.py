from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
