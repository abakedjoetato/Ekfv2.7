#!/usr/bin/env python3

"""
Test Killfeed Bot Instance Passing
Direct test to identify where bot instance is lost during killfeed processing
"""

import asyncio
import logging
import os
import discord
from discord.ext import commands
from motor.motor_asyncio import AsyncIOMotorClient
from bot.utils.simple_killfeed_processor import MultiServerSimpleKillfeedProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockBot:
    """Mock bot with essential killfeed functionality"""
    def __init__(self):
        self.db_manager = None
        self.mongo_client = None
        
    async def setup_database(self):
        """Setup database connection"""
        self.mongo_client = AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        
        # Create db_manager-like interface
        class DBManager:
            def __init__(self, client):
                self.guild_configs = client.emerald_killfeed.guild_configs
                
            async def get_guild(self, guild_id):
                return await self.guild_configs.find_one({"guild_id": guild_id})
                
            async def get_guild_servers(self, guild_id):
                guild_config = await self.get_guild(guild_id)
                if not guild_config:
                    return []
                return guild_config.get('servers', [])
        
        self.db_manager = DBManager(self.mongo_client)
        
    def get_channel(self, channel_id):
        """Mock channel retrieval"""
        logger.info(f"Mock bot retrieving channel {channel_id}")
        return MockChannel(channel_id)

class MockChannel:
    """Mock Discord channel"""
    def __init__(self, channel_id):
        self.id = channel_id
        
    async def send(self, content=None, embed=None, file=None):
        """Mock sending message"""
        if embed:
            logger.info(f"✅ MOCK DELIVERY: Killfeed event sent to channel {self.id}")
            logger.info(f"   Title: {embed.title}")
            logger.info(f"   Description: {embed.description}")
        return MockMessage()

class MockMessage:
    """Mock Discord message"""
    def __init__(self):
        self.id = 12345

async def test_bot_instance_passing():
    """Test bot instance passing through killfeed processing chain"""
    try:
        logger.info("=== Testing Bot Instance Passing in Killfeed Processing ===")
        
        # Create mock bot
        bot = MockBot()
        await bot.setup_database()
        
        guild_id = 1219706687980568769
        
        # Get servers for guild
        servers = await bot.db_manager.get_guild_servers(guild_id)
        logger.info(f"Found {len(servers)} servers for guild {guild_id}")
        
        if not servers:
            logger.error("No servers configured for testing")
            return
            
        # Test bot instance availability at each step
        logger.info(f"Bot instance before processor creation: {bot is not None}")
        
        # Create processor
        processor = MultiServerSimpleKillfeedProcessor(guild_id, bot)
        logger.info(f"Bot instance in processor: {processor.bot is not None}")
        
        # Test single server processing
        test_server = servers[0]
        logger.info(f"Testing with server: {test_server.get('name', 'Unknown')}")
        
        # Create single server processor
        from bot.utils.simple_killfeed_processor import SimpleKillfeedProcessor
        single_processor = SimpleKillfeedProcessor(guild_id, test_server, bot)
        logger.info(f"Bot instance in single processor: {single_processor.bot is not None}")
        
        # Test direct delivery method
        logger.info("Testing direct delivery method...")
        
        # Create a test event
        from bot.utils.simple_killfeed_processor import KillfeedEvent
        from datetime import datetime
        
        test_event = KillfeedEvent(
            timestamp=datetime.now(),
            killer="TestKiller",
            victim="TestVictim", 
            weapon="TestWeapon",
            distance=100,
            killer_platform="PC",
            victim_platform="PC",
            raw_line="test;line;format",
            line_number=1,
            filename="test.csv"
        )
        
        # Test delivery directly
        await single_processor._deliver_killfeed_events([test_event])
        
        logger.info("=== Bot Instance Test Complete ===")
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_bot_instance_passing())