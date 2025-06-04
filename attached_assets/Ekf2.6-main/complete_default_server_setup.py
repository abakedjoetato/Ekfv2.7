"""
Complete Default Server Setup - Configure all missing embed types in default server
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def complete_default_server_configuration():
    """Configure all missing embed types in default server"""
    
    try:
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        guild_id = 1219706687980568769
        
        # Get current configuration
        guild_config = await db_manager.get_guild(guild_id)
        server_channels = guild_config.get('server_channels', {}) if guild_config else {}
        
        # Get current default server configuration
        default_config = server_channels.get('default', {})
        
        logger.info("Current default server channels:")
        for channel_type, channel_id in default_config.items():
            if not channel_type.endswith('_enabled') and not channel_type.endswith('_updated'):
                logger.info(f"  {channel_type}: {channel_id}")
        
        # Add missing embed types to default server
        missing_types = []
        if 'missions' not in default_config:
            default_config['missions'] = default_config.get('events', 1361522248451756234)
            missing_types.append('missions')
        
        if 'helicrash' not in default_config:
            default_config['helicrash'] = default_config.get('events', 1361522248451756234)
            missing_types.append('helicrash')
        
        if missing_types:
            # Update server_channels
            server_channels['default'] = default_config
            
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
            
            logger.info(f"Added missing embed types to default server: {missing_types}")
        else:
            logger.info("All embed types already configured in default server")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to complete default server configuration: {e}")
        return False

async def test_complete_channel_routing():
    """Test complete channel routing for all embed types"""
    
    try:
        from bot.utils.channel_router import ChannelRouter
        
        # Mock bot for testing
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
        
        # Test all embed types
        embed_types = ['killfeed', 'events', 'missions', 'helicrash']
        
        logger.info("Testing complete channel routing:")
        
        successful_routes = 0
        
        for embed_type in embed_types:
            channel_id = await router.get_channel_id(guild_id, server_id, embed_type)
            
            if channel_id:
                logger.info(f"✅ {embed_type}: Channel ID {channel_id}")
                successful_routes += 1
            else:
                logger.warning(f"❌ {embed_type}: No channel found")
        
        logger.info(f"Successfully routed {successful_routes}/4 embed types")
        
        return successful_routes == 4
        
    except Exception as e:
        logger.error(f"Channel routing test failed: {e}")
        return False

async def test_parser_system_integration():
    """Test parser system integration with real server data patterns"""
    
    try:
        # Connect to database
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        
        guild_id = 1219706687980568769
        server_id = '7020'
        
        # Get server configuration
        guild_config = await db_manager.get_guild(guild_id)
        servers = guild_config.get('servers', []) if guild_config else []
        
        if not servers:
            logger.error("No server configuration found")
            return False
        
        server_config = servers[0]
        
        logger.info("Parser system configuration:")
        logger.info(f"  Server ID: {server_config.get('server_id')}")
        logger.info(f"  Server Name: {server_config.get('server_name')}")
        logger.info(f"  SFTP Host: {server_config.get('sftp_credentials', {}).get('host')}")
        logger.info(f"  Log Path: {server_config.get('log_path')}")
        logger.info(f"  Killfeed Path: {server_config.get('killfeed_path')}")
        
        # Check parser state
        parser_state = await db_manager.get_parser_state(guild_id, server_id)
        logger.info(f"  Parser State: {parser_state.get('parser_type')} last updated {parser_state.get('last_updated')}")
        
        # Verify channel routing works for all types
        from bot.utils.channel_router import ChannelRouter
        
        class MockBot:
            def __init__(self, db_manager):
                self.db_manager = db_manager
        
        mock_bot = MockBot(db_manager)
        router = ChannelRouter(mock_bot)
        
        embed_types = ['killfeed', 'events', 'missions', 'helicrash']
        channel_routes = {}
        
        for embed_type in embed_types:
            channel_id = await router.get_channel_id(guild_id, server_id, embed_type)
            channel_routes[embed_type] = channel_id
        
        logger.info("Channel routing results:")
        for embed_type, channel_id in channel_routes.items():
            status = "✅" if channel_id else "❌"
            logger.info(f"  {status} {embed_type}: {channel_id}")
        
        # Verify all routes work
        working_routes = sum(1 for channel_id in channel_routes.values() if channel_id)
        
        logger.info(f"Parser system ready: {working_routes}/4 embed types have valid channels")
        
        return working_routes >= 3  # At least 3 types should work
        
    except Exception as e:
        logger.error(f"Parser system integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Complete default server setup and testing"""
    
    logger.info("Completing default server setup for all embed types...")
    
    # Complete default server configuration
    config_complete = await complete_default_server_configuration()
    
    # Test complete channel routing
    routing_test = await test_complete_channel_routing()
    
    # Test parser system integration
    parser_integration = await test_parser_system_integration()
    
    # Summary
    logger.info("=== Setup Results ===")
    logger.info(f"Default Server Configuration: {'COMPLETE' if config_complete else 'FAILED'}")
    logger.info(f"Channel Routing Test: {'PASS' if routing_test else 'FAIL'}")
    logger.info(f"Parser System Integration: {'PASS' if parser_integration else 'FAIL'}")
    
    if all([config_complete, routing_test, parser_integration]):
        logger.info("✅ Default server setup completed successfully")
        logger.info("All embed types will route to appropriate channels via default server fallback")
        logger.info("Parser system is ready to deliver embeds to Discord")
    else:
        logger.error("❌ Some issues remain with default server setup")

if __name__ == "__main__":
    asyncio.run(main())