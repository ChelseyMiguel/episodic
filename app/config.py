from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://episodic:episodic_password@localhost:5432/episodic_db"
    SECRET_KEY: str = "change-this-to-a-long-random-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    # Override via ALLOWED_ORIGINS env var on Railway for production
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "https://episodic-magazine.github.io",
    ]
    ENVIRONMENT: str = "development"

    # File uploads
    STORAGE_BACKEND: str = "local"          # "local" or "s3"
    UPLOAD_DIR: str = "uploads"             # local disk path (relative or absolute)
    MAX_FILE_SIZE_MB: int = 20              # applies to all uploads

    # S3 / Cloudflare R2 (only needed when STORAGE_BACKEND=s3)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = "us-east-1"

    # Email (SendGrid)
    # Leave SENDGRID_API_KEY empty in development — emails will log to console instead.
    SENDGRID_API_KEY: str = ""
    EMAIL_FROM: str = "episodicmagazine@gmail.com"
    EMAIL_FROM_NAME: str = "Episodic Magazine"
    # Used to build links inside emails (confirmation URLs, unsubscribe links, etc.)
    APP_BASE_URL: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
