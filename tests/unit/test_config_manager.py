"""
Unit tests for configuration manager functionality.
"""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.core.config_manager import (
    ConfigurationManager,
    Environment,
    ValidationResult,
    config_manager
)
from src.core.config import Settings


class TestConfigurationManager:
    """Test configuration manager functionality."""
    
    def test_initialization(self, test_settings):
        """Test configuration manager initialization."""
        manager = ConfigurationManager(test_settings)
        
        assert manager.settings == test_settings
        assert manager.environment == Environment.DEVELOPMENT
        assert manager.config_dir.exists()
    
    def test_validate_configuration_success(self, test_settings):
        """Test successful configuration validation."""
        manager = ConfigurationManager(test_settings)
        result = manager.validate_configuration()
        
        assert isinstance(result, ValidationResult)
        # Test environment should pass basic validation
        assert len(result.errors) == 0
    
    def test_validate_production_config_errors(self):
        """Test production configuration validation with errors."""
        # Create settings that should fail production validation
        prod_settings = Settings(
            SECRET_KEY="short",  # Too short
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://user:los_password@localhost:5432/db",  # Default password
            REDIS_URL="redis://localhost:6379/0",
            QDRANT_URL="http://localhost:6333",
            GEMINI_API_KEY="test-api-key",
            OLLAMA_URL="http://localhost:11434",
            force_https=False,  # Should be True in production
            cors_origins=["*"],  # Wildcard not allowed
            allowed_hosts=["*"]  # Wildcard risky
        )
        
        manager = ConfigurationManager(prod_settings)
        result = manager.validate_configuration()
        
        # Should have multiple errors
        assert len(result.errors) > 0
        assert not result.is_valid
        
        # Check for specific errors
        error_messages = ' '.join(result.errors)
        assert "Secret key must be at least 32 characters" in error_messages
        assert "HTTPS must be enforced" in error_messages
        assert "Default database password" in error_messages
        assert "Wildcard CORS origins not allowed" in error_messages
    
    def test_create_environment_config(self, test_settings):
        """Test environment-specific configuration creation."""
        manager = ConfigurationManager(test_settings)
        
        # Test development config
        dev_config = manager.create_environment_config(Environment.DEVELOPMENT)
        assert dev_config["environment"] == "development"
        assert dev_config["debug"] is True
        assert dev_config["force_https"] is False
        assert "http://localhost" in str(dev_config["cors_origins"])
        
        # Test production config
        prod_config = manager.create_environment_config(Environment.PRODUCTION)
        assert prod_config["environment"] == "production"
        assert prod_config["debug"] is False
        assert prod_config["force_https"] is True
        assert prod_config["log_level"] == "WARNING"
        
        # Test staging config
        staging_config = manager.create_environment_config(Environment.STAGING)
        assert staging_config["environment"] == "staging"
        assert staging_config["force_https"] is True
        assert staging_config["log_level"] == "INFO"
    
    def test_save_and_load_environment_config(self, test_settings, temp_directory):
        """Test saving and loading environment configuration."""
        # Override config directory for test
        test_settings.config_dir = str(temp_directory)
        manager = ConfigurationManager(test_settings)
        
        # Create and save config
        config = manager.create_environment_config(Environment.DEVELOPMENT)
        manager.save_environment_config(Environment.DEVELOPMENT, config)
        
        # Verify file was created
        config_file = temp_directory / "development.yaml"
        assert config_file.exists()
        
        # Load config and verify
        loaded_config = manager.load_environment_config(Environment.DEVELOPMENT)
        assert loaded_config is not None
        assert loaded_config["environment"] == "development"
        assert loaded_config["debug"] is True
    
    def test_load_nonexistent_config(self, test_settings):
        """Test loading non-existent configuration file."""
        manager = ConfigurationManager(test_settings)
        result = manager.load_environment_config(Environment.PRODUCTION)
        
        # Should return None for non-existent file
        assert result is None
    
    def test_generate_deployment_checklist(self, test_settings):
        """Test deployment checklist generation."""
        manager = ConfigurationManager(test_settings)
        
        # Test development checklist
        dev_checklist = manager.generate_deployment_checklist()
        assert isinstance(dev_checklist, list)
        assert len(dev_checklist) > 0
        assert any("development" in item for item in dev_checklist)
        
        # Test production checklist
        test_settings.environment = "production"
        manager = ConfigurationManager(test_settings)
        prod_checklist = manager.generate_deployment_checklist()
        assert len(prod_checklist) > len(dev_checklist)  # Production has more items
        assert any("SSL certificates" in item for item in prod_checklist)
        assert any("SECRET_KEY" in item for item in prod_checklist)
    
    def test_export_config_summary(self, test_settings):
        """Test configuration summary export."""
        manager = ConfigurationManager(test_settings)
        summary = manager.export_config_summary()
        
        # Check structure
        assert "environment" in summary
        assert "validation" in summary
        assert "configuration" in summary
        assert "deployment_checklist" in summary
        
        # Check validation section
        validation = summary["validation"]
        assert "is_valid" in validation
        assert "error_count" in validation
        assert "warning_count" in validation
        assert "errors" in validation
        assert "warnings" in validation
        assert "recommendations" in validation
        
        # Check configuration section
        config = summary["configuration"]
        assert "app_name" in config
        assert "version" in config
        assert "database_pool_size" in config
        assert "api_rate_limits" in config
        assert "processing" in config
        assert "security" in config
    
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_required_vars_validation(self, test_settings):
        """Test validation with missing required environment variables."""
        manager = ConfigurationManager(test_settings)
        result = manager.validate_configuration()
        
        # Should have errors for missing environment variables
        assert len(result.errors) > 0
        error_messages = ' '.join(result.errors)
        assert "Missing required environment variables" in error_messages
    
    def test_chunk_size_validation(self, test_settings):
        """Test chunk size validation warnings."""
        # Test very small chunk size
        test_settings.chunk_size = 50
        manager = ConfigurationManager(test_settings)
        result = manager.validate_configuration()
        
        warning_messages = ' '.join(result.warnings)
        assert "Very small chunk size" in warning_messages
        
        # Test very large chunk size
        test_settings.chunk_size = 3000
        manager = ConfigurationManager(test_settings)
        result = manager.validate_configuration()
        
        warning_messages = ' '.join(result.warnings)
        assert "Large chunk size" in warning_messages
    
    def test_overlap_size_validation(self, test_settings):
        """Test overlap size validation."""
        # Test overlap size >= chunk size
        test_settings.chunk_size = 100
        test_settings.overlap_size = 100
        manager = ConfigurationManager(test_settings)
        result = manager.validate_configuration()
        
        assert len(result.errors) > 0
        error_messages = ' '.join(result.errors)
        assert "Overlap size must be smaller than chunk size" in error_messages
    
    def test_url_format_validation(self, test_settings):
        """Test service URL format validation."""
        # Test invalid URL formats
        test_settings.redis_url = "invalid-url"
        test_settings.qdrant_url = "not-a-url"
        test_settings.ollama_url = "also-invalid"
        
        manager = ConfigurationManager(test_settings)
        result = manager.validate_configuration()
        
        # Should have URL format errors
        assert len(result.errors) > 0
        error_messages = ' '.join(result.errors)
        assert "URL format appears invalid" in error_messages
    
    def test_langfuse_validation(self, test_settings):
        """Test Langfuse configuration validation."""
        # Test incomplete Langfuse config
        test_settings.langfuse_public_key = "test-public-key"
        test_settings.langfuse_secret_key = None
        
        manager = ConfigurationManager(test_settings)
        result = manager.validate_configuration()
        
        warning_messages = ' '.join(result.warnings)
        assert "Langfuse public key provided but secret key missing" in warning_messages


class TestGlobalConfigManager:
    """Test global configuration manager instance."""
    
    def test_global_instance(self):
        """Test that global config manager instance exists."""
        assert config_manager is not None
        assert isinstance(config_manager, ConfigurationManager)
    
    def test_global_instance_environment(self):
        """Test global instance environment detection."""
        # Should detect environment from current settings
        assert isinstance(config_manager.environment, Environment)
        assert config_manager.settings is not None
