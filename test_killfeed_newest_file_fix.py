"""
Test Killfeed Newest File Discovery Fix
Verify the killfeed parser can properly identify the newest CSV file
"""
import asyncio
import logging
from bot.utils.scalable_killfeed_processor import ScalableKillfeedProcessor
from bot.models.database import DatabaseManager
from bot.utils.connection_pool import GlobalConnectionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_newest_file_discovery():
    """Test the newest file discovery with the current CSV format"""
    try:
        # Initialize database manager
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Initialize connection manager
        connection_manager = GlobalConnectionManager()
        await connection_manager.initialize()
        
        # Get guild and server config
        guild_id = 1219706687980568769
        guild_config = await db_manager.get_guild(guild_id)
        
        if not guild_config:
            logger.error("Guild config not found")
            return
        
        servers = guild_config.get('servers', [])
        if not servers:
            logger.error("No servers found in guild config")
            return
        
        server_config = servers[0]  # Use first server
        server_name = server_config.get('name', 'default')
        
        logger.info(f"Testing newest file discovery for server: {server_name}")
        
        # Initialize killfeed processor
        processor = ScalableKillfeedProcessor(
            guild_id=guild_id,
            server_config=server_config,
            state_manager=None,
            bot=None
        )
        
        # Test newest file discovery
        newest_file = await processor._discover_newest_file()
        
        if newest_file:
            logger.info(f"✅ Successfully discovered newest file: {newest_file}")
            
            # Test timestamp extraction
            timestamp = processor._extract_timestamp_from_filename(newest_file)
            if timestamp:
                logger.info(f"✅ Successfully extracted timestamp: {timestamp}")
            else:
                logger.warning(f"⚠️ Failed to extract timestamp from: {newest_file}")
        else:
            logger.error("❌ Failed to discover newest file")
        
        # Cleanup
        await connection_manager.cleanup()
        await db_manager.close()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_newest_file_discovery())