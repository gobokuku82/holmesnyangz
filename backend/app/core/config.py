import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "HolmesNyangz"
    SECRET_KEY: str = os.getenv("SECRET_KEY","")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    ALLOWED_HOSTS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    MONGODB_URL :str = os.getenv("MONGODB_URL", "")
    real_estate_data_path: str = "frontend/public/data/real_estate_with_coordinates_kakao.csv"
    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields from .env file

settings = Settings()