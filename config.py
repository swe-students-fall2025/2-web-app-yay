import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB: str = os.getenv("MONGO_DB", "todoapp")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev")
    PORT: int = int(os.getenv("PORT", "5000"))
    DEBUG: bool = os.getenv("FLASK_ENV") == "development"


settings = Settings()
