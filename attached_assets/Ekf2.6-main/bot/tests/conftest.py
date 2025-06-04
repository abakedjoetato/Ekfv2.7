"""
Test Configuration
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_bot():
    """Mock bot instance for testing"""
    bot = MagicMock()
    bot.db_manager = AsyncMock()
    bot.premium_manager = AsyncMock()
    bot.cache_manager = AsyncMock()
    return bot

@pytest.fixture
def mock_ctx():
    """Mock Discord context for testing"""
    ctx = AsyncMock()
    ctx.guild_id = 12345
    ctx.respond = AsyncMock()
    ctx.followup.send = AsyncMock()
    return ctx
