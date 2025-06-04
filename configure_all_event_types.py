"""
Configure All Event Types - Add airdrop and trader to Events channel routing
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorClient
from bot.models.database import DatabaseManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def configure_all_event_types():
    """Configure airdrop and trader events to route to Events channel"""
    
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
        events_channel = default_config.get('events', 1361522248451756234)
        
        logger.info("Configuring all event types to route to Events channel...")
        logger.info(f"Events channel ID: {events_channel}")
        
        # Add all event types that should go to Events channel
        event_types = ['missions', 'helicrash', 'airdrop', 'trader']
        added_types = []
        
        for event_type in event_types:
            if event_type not in default_config:
                default_config[event_type] = events_channel
                added_types.append(event_type)
            else:
                # Update existing to ensure they point to Events channel
                if default_config[event_type] != events_channel:
                    default_config[event_type] = events_channel
                    added_types.append(f"{event_type} (updated)")
        
        if added_types:
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
            
            logger.info(f"Configured event types: {added_types}")
        
        # Verify final configuration
        logger.info("Final default server channel configuration:")
        for channel_type, channel_id in default_config.items():
            if not channel_type.endswith('_enabled') and not channel_type.endswith('_updated'):
                logger.info(f"  {channel_type}: {channel_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to configure all event types: {e}")
        return False

async def test_complete_routing():
    """Test routing for all event types"""
    
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
        all_types = ['killfeed', 'events', 'missions', 'helicrash', 'airdrop', 'trader']
        
        logger.info("Testing complete event type routing:")
        
        routing_results = {}
        
        for event_type in all_types:
            channel_id = await router.get_channel_id(guild_id, server_id, event_type)
            routing_results[event_type] = channel_id
            
            if channel_id:
                logger.info(f"✅ {event_type}: Channel ID {channel_id}")
            else:
                logger.warning(f"❌ {event_type}: No channel found")
        
        # Verify channel assignments
        killfeed_channel = routing_results.get('killfeed')
        events_channel = routing_results.get('events')
        
        logger.info("\nChannel assignment verification:")
        logger.info(f"Killfeed channel: {killfeed_channel}")
        logger.info(f"Events channel: {events_channel}")
        
        # Check that missions, helicrash, airdrop, trader all go to Events channel
        events_types = ['missions', 'helicrash', 'airdrop', 'trader']
        correct_routing = True
        
        for event_type in events_types:
            channel_id = routing_results.get(event_type)
            if channel_id == events_channel:
                logger.info(f"✅ {event_type} correctly routes to Events channel")
            else:
                logger.error(f"❌ {event_type} routes to {channel_id}, expected {events_channel}")
                correct_routing = False
        
        logger.info(f"\nRouting verification: {'PASS' if correct_routing else 'FAIL'}")
        
        return correct_routing and len([r for r in routing_results.values() if r]) >= 5
        
    except Exception as e:
        logger.error(f"Complete routing test failed: {e}")
        return False

async def main():
    """Configure and test all event type routing"""
    
    logger.info("Configuring all event types for proper channel routing...")
    
    # Configure all event types
    config_success = await configure_all_event_types()
    
    # Test complete routing
    routing_success = await test_complete_routing()
    
    # Summary
    logger.info("=== Configuration Results ===")
    logger.info(f"Event Type Configuration: {'SUCCESS' if config_success else 'FAILED'}")
    logger.info(f"Routing Verification: {'SUCCESS' if routing_success else 'FAILED'}")
    
    if config_success and routing_success:
        logger.info("✅ All event types configured correctly")
        logger.info("Channel routing:")
        logger.info("  killfeed → Killfeed channel")
        logger.info("  events, missions, helicrash, airdrop, trader → Events channel")
        logger.info("Parser system ready to deliver all embed types to appropriate channels")
    else:
        logger.error("❌ Configuration issues detected")

if __name__ == "__main__":
    asyncio.run(main())