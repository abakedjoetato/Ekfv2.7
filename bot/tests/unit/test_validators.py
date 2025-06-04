"""
Unit Tests for Core Components
"""

import pytest
from bot.utils.input_validator import InputValidator

class TestInputValidator:
    """Test input validation"""
    
    def test_validate_guild_id(self):
        """Test guild ID validation"""
        assert InputValidator.validate_guild_id(12345) == 12345
        assert InputValidator.validate_guild_id("12345") == 12345
        assert InputValidator.validate_guild_id("invalid") is None
        
    def test_validate_player_name(self):
        """Test player name validation"""
        assert InputValidator.validate_player_name("TestPlayer") == "TestPlayer"
        assert InputValidator.validate_player_name("Player With Spaces") == "Player With Spaces"
        assert InputValidator.validate_player_name("A") is None  # Too short
