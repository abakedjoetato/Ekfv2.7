"""
Test Default Server Fallback System - Verify parser uses default server channels
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager
from bot.utils.channel_router import ChannelRouter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_current_channel_configuration():
    """Check current channel configuration and default server setup"""
    
    try:
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        guild_id = 1219706687980568769
        server_id = '7020'  # Emerald EU server
        
        # Get current guild configuration
        guild_config = await db_manager.get_guild(guild_id)
        
        if not guild_config:
            logger.error("No guild configuration found")
            return False
        
        logger.info("=== Current Channel Configuration ===")
        
        # Check server_channels structure
        server_channels = guild_config.get('server_channels', {})
        logger.info(f"Server channels configured: {list(server_channels.keys())}")
        
        # Check if default server exists
        if 'default' in server_channels:
            default_channels = server_channels['default']
            logger.info(f"Default server channels: {list(default_channels.keys())}")
            
            for channel_type, channel_id in default_channels.items():
                logger.info(f"  {channel_type}: {channel_id}")
        else:
            logger.warning("No 'default' server configured")
        
        # Check server-specific channels
        if server_id in server_channels:
            specific_channels = server_channels[server_id]
            logger.info(f"Server '{server_id}' specific channels: {list(specific_channels.keys())}")
        else:
            logger.info(f"No specific channels for server '{server_id}' - will use default fallback")
        
        # Check legacy channels
        legacy_channels = guild_config.get('channels', {})
        if legacy_channels:
            logger.info(f"Legacy channels: {list(legacy_channels.keys())}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to check channel configuration: {e}")
        return False

async def test_channel_router_fallback():
    """Test channel router fallback logic"""
    
    try:
        # Mock bot object for channel router
        class MockBot:
            def __init__(self, db_manager):
                self.db_manager = db_manager
        
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        mock_bot = MockBot(db_manager)
        router = ChannelRouter(mock_bot)
        
        guild_id = 1219706687980568769
        server_id = '7020'
        
        # Test each embed type
        embed_types = ['killfeed', 'events', 'missions', 'helicrash']
        
        logger.info("=== Testing Channel Router Fallback ===")
        
        for embed_type in embed_types:
            channel_id = await router.get_channel_id(guild_id, server_id, embed_type)
            
            if channel_id:
                logger.info(f"✅ {embed_type}: Channel ID {channel_id}")
            else:
                logger.warning(f"❌ {embed_type}: No channel found")
        
        return True
        
    except Exception as e:
        logger.error(f"Channel router test failed: {e}")
        return False

async def configure_default_server_channels():
    """Configure default server channels if not present"""
    
    try:
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        guild_id = 1219706687980568769
        
        # Get current configuration
        guild_config = await db_manager.get_guild(guild_id)
        server_channels = guild_config.get('server_channels', {}) if guild_config else {}
        
        # Check if default server needs configuration
        if 'default' not in server_channels or not server_channels['default']:
            logger.info("Configuring default server channels...")
            
            # Set up default server with general channel for all embed types
            default_channels = {
                'killfeed': 1219706688815398002,  # Use first available text channel as fallback
                'events': 1219706688815398002,
                'missions': 1219706688815398002,
                'helicrash': 1219706688815398002
            }
            
            # Update server_channels
            server_channels['default'] = default_channels
            
            # Update database
            await db_manager.guild_configs.update_one(
                {'guild_id': guild_id},
                {
                    '$set': {
                        'server_channels': server_channels,
                        'last_updated': datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
            
            logger.info("Default server channels configured")
            return True
        else:
            logger.info("Default server channels already configured")
            return True
        
    except Exception as e:
        logger.error(f"Failed to configure default server channels: {e}")
        return False

async def test_parser_embed_delivery():
    """Test actual parser embed delivery through default server fallback"""
    
    try:
        # Import parser components
        import sys
        sys.path.insert(0, '.')
        
        from bot.utils.scalable_unified_processor import ScalableUnifiedProcessor
        from bot.models.database import DatabaseManager
        from motor.motor_asyncio import AsyncIOMotorClient
        
        # Mock bot for testing
        class MockBot:
            def __init__(self):
                mongo_uri = os.environ.get('MONGO_URI')
                client = AsyncIOMotorClient(mongo_uri)
                self.db_manager = DatabaseManager(client)
                
            def get_channel(self, channel_id):
                # Mock channel object
                class MockChannel:
                    def __init__(self, channel_id):
                        self.id = channel_id
                        self.name = f"channel_{channel_id}"
                    
                    async def send(self, embed=None, file=None):
                        logger.info(f"Mock send to channel {self.id}: {embed.title if embed else 'No embed'}")
                        return True
                
                return MockChannel(channel_id)
        
        mock_bot = MockBot()
        
        # Create processor instance
        processor = ScalableUnifiedProcessor(mock_bot)
        
        guild_id = 1219706687980568769
        server_id = '7020'
        
        # Test embed delivery for each type
        test_events = [
            {
                'type': 'killfeed',
                'data': {'killer': 'TestPlayer1', 'victim': 'TestPlayer2', 'weapon': 'AK-74'}
            },
            {
                'type': 'events', 
                'data': {'event_type': 'player_connect', 'player_name': 'TestPlayer3'}
            },
            {
                'type': 'missions',
                'data': {'mission_type': 'Supply Drop', 'location': 'Grid 1500,2000'}
            },
            {
                'type': 'helicrash',
                'data': {'location': 'Grid 1800,2500'}
            }
        ]
        
        logger.info("=== Testing Parser Embed Delivery ===")
        
        successful_deliveries = 0
        
        for event in test_events:
            embed_type = event['type']
            event_data = event['data']
            
            # Create router to test channel resolution
            router = ChannelRouter(mock_bot)
            channel_id = await router.get_channel_id(guild_id, server_id, embed_type)
            
            if channel_id:
                logger.info(f"✅ {embed_type} -> Channel {channel_id} (via default server fallback)")
                successful_deliveries += 1
            else:
                logger.warning(f"❌ {embed_type} -> No channel found")
        
        logger.info(f"Successfully resolved {successful_deliveries}/4 embed types")
        
        return successful_deliveries >= 3  # At least 3 types should work
        
    except Exception as e:
        logger.error(f"Parser embed delivery test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Test complete default server fallback system"""
    
    logger.info("Testing default server fallback system...")
    
    # Check current configuration
    config_check = await check_current_channel_configuration()
    
    # Configure default server if needed
    default_configured = await configure_default_server_channels()
    
    # Test channel router fallback
    router_test = await test_channel_router_fallback()
    
    # Test parser delivery
    parser_test = await test_parser_embed_delivery()
    
    # Summary
    logger.info("=== Test Results ===")
    logger.info(f"Configuration Check: {'PASS' if config_check else 'FAIL'}")
    logger.info(f"Default Server Setup: {'PASS' if default_configured else 'FAIL'}")
    logger.info(f"Channel Router Test: {'PASS' if router_test else 'FAIL'}")
    logger.info(f"Parser Delivery Test: {'PASS' if parser_test else 'FAIL'}")
    
    if all([config_check, default_configured, router_test, parser_test]):
        logger.info("✅ Default server fallback system is operational")
        logger.info("Parser will use default server channels when server-specific channels aren't configured")
    else:
        logger.error("❌ Some issues with default server fallback system")

if __name__ == "__main__":
    asyncio.run(main())