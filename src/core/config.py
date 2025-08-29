from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List
import os
import secrets
from pathlib import Path


class Settings(BaseSettings):
    """Application settings and configuration with security hardening."""
    
    # Application
    app_name: str = "LOs Generation Pipeline"
    version: str = "1.0.0"
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    secret_key: str = Field(..., env="SECRET_KEY")
    
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    redis_url: str = Field(..., env="REDIS_URL")
    redis_max_connections: int = Field(default=10, env="REDIS_MAX_CONNECTIONS")
    
    # Qdrant
    qdrant_url: str = Field(..., env="QDRANT_URL")
    qdrant_collection_name: str = Field(default="los_chunks", env="QDRANT_COLLECTION_NAME")
    vector_dimension: int = Field(default=1024, env="VECTOR_DIMENSION")
    
    # LLM APIs
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    ollama_url: str = Field(..., env="OLLAMA_URL")
    
    # Langfuse
    langfuse_public_key: Optional[str] = Field(None, env="LANGFUSE_PUBLIC_KEY")
    langfuse_secret_key: Optional[str] = Field(None, env="LANGFUSE_SECRET_KEY")
    langfuse_host: str = Field(default="https://cloud.langfuse.com", env="LANGFUSE_HOST")
    
    # Rate Limiting & Security
    default_rate_limit: int = Field(default=100, env="DEFAULT_RATE_LIMIT")
    rate_limit_period: int = Field(default=3600, env="RATE_LIMIT_PERIOD")
    api_rate_limit_per_minute: int = Field(default=60, env="API_RATE_LIMIT_PER_MINUTE")
    api_rate_limit_per_hour: int = Field(default=1000, env="API_RATE_LIMIT_PER_HOUR")
    api_key_expiry_days: int = Field(default=365, env="API_KEY_EXPIRY_DAYS")
    
    # Production Security
    force_https: bool = Field(default=False, env="FORCE_HTTPS")
    ssl_cert_path: Optional[str] = Field(None, env="SSL_CERT_PATH")
    ssl_key_path: Optional[str] = Field(None, env="SSL_KEY_PATH")
    allowed_hosts: List[str] = Field(default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS")
    cors_origins: List[str] = Field(default=["http://localhost:3000"], env="CORS_ORIGINS")
    
    # Processing
    max_concurrent_jobs: int = Field(default=5, env="MAX_CONCURRENT_JOBS")
    chunk_size: int = Field(default=1000, env="CHUNK_SIZE")
    overlap_size: int = Field(default=200, env="OVERLAP_SIZE")
    max_retrieval_chunks: int = Field(default=20, env="MAX_RETRIEVAL_CHUNKS")
    top_k_retrieval: int = Field(default=10, env="TOP_K_RETRIEVAL")
    
    # Model Configuration (Fixed according to approved config)
    default_embedding_model: str = Field(default="bge-m3", env="DEFAULT_EMBEDDING_MODEL")
    english_embedding_model: str = Field(default="qwen/qwen3-embedding-8b", env="ENGLISH_EMBEDDING_MODEL")
    thai_reranker_model: str = Field(default="bge-reranker-v2-m3", env="THAI_RERANKER_MODEL")
    english_reranker_model: str = Field(default="qwen/qwen3-reranker-8b", env="ENGLISH_RERANKER_MODEL")
    
    # File Paths
    config_dir: str = Field(default="configs", env="CONFIG_DIR")
    input_data_dir: str = Field(default="input_data", env="INPUT_DATA_DIR")
    output_data_dir: str = Field(default="output_data", env="OUTPUT_DATA_DIR")
    logs_dir: str = Field(default="logs", env="LOGS_DIR")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")
    
    @validator('secret_key')
    def validate_secret_key(cls, v, values):
        """Validate secret key security requirements."""
        if values.get('environment') == 'production':
            if len(v) < 32:
                raise ValueError("Secret key must be at least 32 characters in production")
            if v == "your-secret-key-here-change-this-in-production":
                raise ValueError("Must change default secret key in production")
        return v
    
    @validator('gemini_api_key')
    def validate_gemini_api_key(cls, v):
        """Validate Gemini API key format."""
        if v == "your-gemini-api-key-here":
            raise ValueError("Must provide valid Gemini API key")
        if len(v) < 20:  # Basic length check
            raise ValueError("Gemini API key appears to be invalid")
        return v
    
    @validator('database_url')
    def validate_database_url(cls, v, values):
        """Validate database URL security."""
        if values.get('environment') == 'production':
            if 'localhost' in v or '127.0.0.1' in v:
                raise ValueError("Production database should not use localhost")
            if 'password' in v and 'los_password' in v:
                raise ValueError("Must change default database password in production")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment.lower() == "development"
    
    def generate_secure_secret_key(self) -> str:
        """Generate a secure secret key for production use."""
        return secrets.token_urlsafe(32)
    
    def ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        directories = [
            self.config_dir,
            self.input_data_dir,
            self.output_data_dir,
            self.logs_dir
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get application settings."""
    return settings


def get_security_headers() -> dict:
    """Get security headers for production deployment."""
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY", 
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }