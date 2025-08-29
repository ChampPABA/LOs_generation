"""
Configuration manager for environment-specific settings and validation.
"""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

from .config import Settings, get_settings

logger = logging.getLogger(__name__)


class Environment(Enum):
    """Supported environment types."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class ValidationResult:
    """Configuration validation result."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    recommendations: List[str]


class ConfigurationManager:
    """Configuration manager with environment-specific handling."""
    
    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.config_dir = Path(self.settings.config_dir)
        self.environment = Environment(self.settings.environment.lower())
        
    def validate_configuration(self) -> ValidationResult:
        """Validate current configuration against environment requirements."""
        errors = []
        warnings = []
        recommendations = []
        
        # Environment-specific validation
        if self.environment == Environment.PRODUCTION:
            prod_validation = self._validate_production_config()
            errors.extend(prod_validation["errors"])
            warnings.extend(prod_validation["warnings"])
            recommendations.extend(prod_validation["recommendations"])
        
        # General validation
        general_validation = self._validate_general_config()
        errors.extend(general_validation["errors"])
        warnings.extend(general_validation["warnings"])
        recommendations.extend(general_validation["recommendations"])
        
        # Service connectivity validation
        connectivity_validation = self._validate_connectivity_config()
        errors.extend(connectivity_validation["errors"])
        warnings.extend(connectivity_validation["warnings"])
        recommendations.extend(connectivity_validation["recommendations"])
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            recommendations=recommendations
        )
    
    def _validate_production_config(self) -> Dict[str, List[str]]:
        """Validate production-specific configuration."""
        errors = []
        warnings = []
        recommendations = []
        
        # Security validation
        if not self.settings.force_https:
            errors.append("HTTPS must be enforced in production (FORCE_HTTPS=true)")
        
        if not self.settings.ssl_cert_path or not self.settings.ssl_key_path:
            errors.append("SSL certificate paths must be configured in production")
        
        # Database security
        if "localhost" in self.settings.database_url or "127.0.0.1" in self.settings.database_url:
            errors.append("Production database should not use localhost")
        
        if "los_password" in self.settings.database_url:
            errors.append("Default database password detected in production")
        
        # Secret key validation
        if len(self.settings.secret_key) < 32:
            errors.append("Secret key must be at least 32 characters in production")
        
        # Rate limiting
        if self.settings.api_rate_limit_per_minute > 200:
            warnings.append("High rate limit may impact performance in production")
        
        # CORS origins
        if "*" in self.settings.cors_origins:
            errors.append("Wildcard CORS origins not allowed in production")
        
        # Allowed hosts
        if "*" in self.settings.allowed_hosts:
            warnings.append("Wildcard allowed hosts may pose security risk")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "recommendations": recommendations
        }
    
    def _validate_general_config(self) -> Dict[str, List[str]]:
        """Validate general configuration."""
        errors = []
        warnings = []
        recommendations = []
        
        # Required environment variables
        required_vars = [
            "DATABASE_URL",
            "REDIS_URL", 
            "QDRANT_URL",
            "GEMINI_API_KEY",
            "OLLAMA_URL",
            "SECRET_KEY"
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            errors.append(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Chunk size validation
        if self.settings.chunk_size < 100:
            warnings.append("Very small chunk size may result in poor context")
        elif self.settings.chunk_size > 2000:
            warnings.append("Large chunk size may exceed model context limits")
        
        # Overlap validation
        if self.settings.overlap_size >= self.settings.chunk_size:
            errors.append("Overlap size must be smaller than chunk size")
        
        # Pool size validation
        if self.settings.database_pool_size < 5:
            warnings.append("Small database pool size may cause connection bottlenecks")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "recommendations": recommendations
        }
    
    def _validate_connectivity_config(self) -> Dict[str, List[str]]:
        """Validate service connectivity configuration."""
        errors = []
        warnings = []
        recommendations = []
        
        # URL format validation
        service_urls = {
            "Database": self.settings.database_url,
            "Redis": self.settings.redis_url,
            "Qdrant": self.settings.qdrant_url,
            "Ollama": self.settings.ollama_url
        }
        
        for service, url in service_urls.items():
            if not url.startswith(("http://", "https://", "postgresql://", "redis://")):
                if service != "Database":
                    errors.append(f"{service} URL format appears invalid: {url}")
        
        # Langfuse optional validation
        if self.settings.langfuse_public_key and not self.settings.langfuse_secret_key:
            warnings.append("Langfuse public key provided but secret key missing")
        
        return {
            "errors": errors,
            "warnings": warnings,
            "recommendations": recommendations
        }
    
    def create_environment_config(self, environment: Environment) -> Dict[str, Any]:
        """Create environment-specific configuration template."""
        base_config = {
            "environment": environment.value,
            "debug": environment in [Environment.DEVELOPMENT, Environment.TESTING],
            "app_name": "LOs Generation Pipeline",
            "version": "1.0.0"
        }
        
        if environment == Environment.PRODUCTION:
            base_config.update({
                "force_https": True,
                "api_rate_limit_per_minute": 60,
                "api_rate_limit_per_hour": 1000,
                "database_pool_size": 20,
                "max_concurrent_jobs": 10,
                "log_level": "WARNING",
                "cors_origins": ["https://yourdomain.com"]
            })
        
        elif environment == Environment.STAGING:
            base_config.update({
                "force_https": True,
                "api_rate_limit_per_minute": 100,
                "api_rate_limit_per_hour": 2000,
                "database_pool_size": 15,
                "max_concurrent_jobs": 8,
                "log_level": "INFO",
                "cors_origins": ["https://staging.yourdomain.com"]
            })
        
        elif environment == Environment.DEVELOPMENT:
            base_config.update({
                "force_https": False,
                "api_rate_limit_per_minute": 200,
                "api_rate_limit_per_hour": 5000,
                "database_pool_size": 10,
                "max_concurrent_jobs": 5,
                "log_level": "DEBUG",
                "cors_origins": ["http://localhost:3000", "http://127.0.0.1:3000"]
            })
        
        elif environment == Environment.TESTING:
            base_config.update({
                "force_https": False,
                "api_rate_limit_per_minute": 500,
                "api_rate_limit_per_hour": 10000,
                "database_pool_size": 5,
                "max_concurrent_jobs": 3,
                "log_level": "ERROR",
                "cors_origins": ["*"]
            })
        
        return base_config
    
    def save_environment_config(self, environment: Environment, config: Dict[str, Any]):
        """Save environment-specific configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = self.config_dir / f"{environment.value}.yaml"
        
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        logger.info(f"Saved {environment.value} configuration to {config_file}")
    
    def load_environment_config(self, environment: Environment) -> Optional[Dict[str, Any]]:
        """Load environment-specific configuration from file."""
        config_file = self.config_dir / f"{environment.value}.yaml"
        
        if not config_file.exists():
            return None
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
    
    def generate_deployment_checklist(self) -> List[str]:
        """Generate deployment checklist based on current environment."""
        checklist = []
        
        if self.environment == Environment.PRODUCTION:
            checklist = [
                "✓ Set ENVIRONMENT=production",
                "✓ Configure production database with strong credentials",
                "✓ Set up SSL certificates (SSL_CERT_PATH, SSL_KEY_PATH)",
                "✓ Generate secure SECRET_KEY (32+ characters)",
                "✓ Set FORCE_HTTPS=true",
                "✓ Configure specific CORS_ORIGINS (no wildcards)",
                "✓ Set appropriate rate limits for production traffic",
                "✓ Configure production Redis instance",
                "✓ Set up production Qdrant instance",
                "✓ Validate Gemini API key and quotas",
                "✓ Configure Ollama models for production",
                "✓ Set LOG_LEVEL to WARNING or ERROR",
                "✓ Set up monitoring and health checks",
                "✓ Configure backup strategies",
                "✓ Set up log aggregation",
                "✓ Review and test circuit breaker configurations"
            ]
        
        elif self.environment == Environment.STAGING:
            checklist = [
                "✓ Set ENVIRONMENT=staging",
                "✓ Configure staging database",
                "✓ Set up SSL for staging domain",
                "✓ Generate staging SECRET_KEY",
                "✓ Configure staging CORS_ORIGINS",
                "✓ Test rate limiting configurations",
                "✓ Verify all external service connections",
                "✓ Run integration tests",
                "✓ Test circuit breaker functionality",
                "✓ Verify monitoring endpoints"
            ]
        
        elif self.environment == Environment.DEVELOPMENT:
            checklist = [
                "✓ Set ENVIRONMENT=development",
                "✓ Configure local database",
                "✓ Set up local Redis instance",
                "✓ Configure local Qdrant instance",
                "✓ Set up Ollama with required models",
                "✓ Configure development API keys",
                "✓ Set DEBUG=true for detailed logging",
                "✓ Test all API endpoints",
                "✓ Verify hot reload functionality"
            ]
        
        return checklist
    
    def export_config_summary(self) -> Dict[str, Any]:
        """Export configuration summary for documentation."""
        validation = self.validate_configuration()
        
        return {
            "environment": self.environment.value,
            "validation": {
                "is_valid": validation.is_valid,
                "error_count": len(validation.errors),
                "warning_count": len(validation.warnings),
                "errors": validation.errors,
                "warnings": validation.warnings,
                "recommendations": validation.recommendations
            },
            "configuration": {
                "app_name": self.settings.app_name,
                "version": self.settings.version,
                "debug": self.settings.debug,
                "database_pool_size": self.settings.database_pool_size,
                "api_rate_limits": {
                    "per_minute": self.settings.api_rate_limit_per_minute,
                    "per_hour": self.settings.api_rate_limit_per_hour
                },
                "processing": {
                    "chunk_size": self.settings.chunk_size,
                    "overlap_size": self.settings.overlap_size,
                    "max_concurrent_jobs": self.settings.max_concurrent_jobs
                },
                "security": {
                    "force_https": self.settings.force_https,
                    "cors_origins_count": len(self.settings.cors_origins),
                    "allowed_hosts_count": len(self.settings.allowed_hosts)
                }
            },
            "deployment_checklist": self.generate_deployment_checklist()
        }


# Global configuration manager instance
config_manager = ConfigurationManager()
