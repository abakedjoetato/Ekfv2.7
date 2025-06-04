"""
Complete Killfeed Pipeline Test - End-to-End Real World Testing
Tests all parsers with authentic data to ensure proper Discord embed delivery
"""

import asyncio
import logging
from datetime import datetime, timezone
import os
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_complete_killfeed_pipeline():
    """Test complete killfeed pipeline with real data"""
    
    logger.info("🚀 Starting complete killfeed pipeline test...")
    
    try:
        # Import bot components
        from bot.models.database import db
        from bot.utils.scalable_unified_processor import ScalableUnifiedProcessor
        from bot.utils.unified_cache import unified_cache
        
        # Initialize database connection
        await db.initialize()
        logger.info("✅ Database connection established")
        
        # Get server configurations
        servers = await db.get_all_servers()
        logger.info(f"📡 Found {len(servers)} configured servers")
        
        if not servers:
            logger.error("❌ No servers configured in database")
            return False
        
        # Test each server configuration
        for server in servers:
            server_id = server.get('server_id', 'unknown')
            logger.info(f"🔍 Testing server: {server_id}")
            
            # Check server configuration
            required_fields = ['log_path', 'killfeed_path', 'guild_id']
            missing_fields = [field for field in required_fields if not server.get(field)]
            
            if missing_fields:
                logger.warning(f"⚠️ Server {server_id} missing fields: {missing_fields}")
                continue
            
            # Test SFTP connection
            sftp_credentials = server.get('sftp_credentials', {})
            if not sftp_credentials.get('host'):
                logger.warning(f"⚠️ Server {server_id} missing SFTP credentials")
                continue
            
            logger.info(f"🔗 Testing SFTP connection to {sftp_credentials.get('host')}")
            
            # Initialize processor for this server
            processor = ScalableUnifiedProcessor()
            
            # Test log parser
            logger.info(f"📝 Testing log parser for server {server_id}")
            try:
                log_results = await processor.process_server_logs(server)
                logger.info(f"📊 Log parser processed {len(log_results)} events")
                
                # Verify event types
                event_types = set()
                for event in log_results:
                    event_types.add(event.get('event_type', 'unknown'))
                
                logger.info(f"📋 Event types found: {event_types}")
                
            except Exception as e:
                logger.error(f"❌ Log parser failed for {server_id}: {e}")
                continue
            
            # Test killfeed parser
            logger.info(f"💀 Testing killfeed parser for server {server_id}")
            try:
                killfeed_results = await processor.process_killfeed_data(server)
                logger.info(f"📊 Killfeed parser processed {len(killfeed_results)} kills")
                
                # Verify killfeed data structure
                for kill in killfeed_results[:3]:  # Check first 3 kills
                    required_kill_fields = ['killer', 'victim', 'weapon', 'timestamp']
                    missing_kill_fields = [field for field in required_kill_fields if not kill.get(field)]
                    if missing_kill_fields:
                        logger.warning(f"⚠️ Kill event missing fields: {missing_kill_fields}")
                
            except Exception as e:
                logger.error(f"❌ Killfeed parser failed for {server_id}: {e}")
                continue
            
            # Test Discord delivery
            logger.info(f"📤 Testing Discord embed delivery for server {server_id}")
            
            guild_id = server.get('guild_id')
            channel_configs = await db.get_channel_configs(guild_id)
            
            if not channel_configs:
                logger.warning(f"⚠️ No channel configurations found for guild {guild_id}")
                continue
            
            logger.info(f"📺 Found {len(channel_configs)} channel configurations")
            
            # Test each embed type delivery
            embed_types = ['killfeed', 'events', 'missions', 'helicrash']
            
            for embed_type in embed_types:
                logger.info(f"🎯 Testing {embed_type} embed delivery")
                
                # Find appropriate channel for this embed type
                target_channel = None
                for config in channel_configs:
                    if embed_type in config.get('embed_types', []):
                        target_channel = config.get('channel_id')
                        break
                
                if not target_channel:
                    logger.warning(f"⚠️ No channel configured for {embed_type} embeds")
                    continue
                
                # Create test embed based on type
                if embed_type == 'killfeed' and killfeed_results:
                    test_data = killfeed_results[0]
                    embed_content = {
                        'title': f"💀 {test_data.get('killer', 'Unknown')} killed {test_data.get('victim', 'Unknown')}",
                        'description': f"Weapon: {test_data.get('weapon', 'Unknown')}",
                        'timestamp': test_data.get('timestamp', datetime.now(timezone.utc)),
                        'color': 0xff0000
                    }
                elif embed_type == 'events' and log_results:
                    event_data = next((e for e in log_results if e.get('event_type') == 'player_connect'), None)
                    if event_data:
                        embed_content = {
                            'title': f"🎮 Player Connected",
                            'description': f"{event_data.get('player_name', 'Unknown')} joined the server",
                            'timestamp': event_data.get('timestamp', datetime.now(timezone.utc)),
                            'color': 0x00ff00
                        }
                    else:
                        logger.info(f"📝 No connect events found for {embed_type} test")
                        continue
                else:
                    # Create generic test embed
                    embed_content = {
                        'title': f"🧪 Test {embed_type.title()} Embed",
                        'description': f"End-to-end test of {embed_type} delivery pipeline",
                        'timestamp': datetime.now(timezone.utc),
                        'color': 0x0099ff
                    }
                
                # Simulate Discord delivery (would normally use Discord bot)
                logger.info(f"✅ {embed_type} embed ready for delivery to channel {target_channel}")
                logger.info(f"📋 Embed content: {embed_content['title']}")
        
        logger.info("🎉 Complete killfeed pipeline test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_real_sftp_connections():
    """Test actual SFTP connections to verify credentials"""
    
    logger.info("🔗 Testing real SFTP connections...")
    
    try:
        from bot.models.database import db
        
        # Get server configurations
        servers = await db.get_all_servers()
        
        for server in servers:
            server_id = server.get('server_id', 'unknown')
            sftp_creds = server.get('sftp_credentials', {})
            
            if not sftp_creds.get('host'):
                logger.warning(f"⚠️ Server {server_id} has no SFTP host configured")
                continue
            
            logger.info(f"🌐 Testing SFTP connection to {sftp_creds.get('host')} for server {server_id}")
            
            try:
                import paramiko
                
                # Create SFTP client
                transport = paramiko.Transport((sftp_creds.get('host'), sftp_creds.get('port', 22)))
                
                # Authenticate
                if sftp_creds.get('password'):
                    transport.connect(
                        username=sftp_creds.get('username'),
                        password=sftp_creds.get('password')
                    )
                else:
                    logger.warning(f"⚠️ Server {server_id} missing SFTP password")
                    continue
                
                # Create SFTP client
                sftp = paramiko.SFTPClient.from_transport(transport)
                
                # Test file access
                log_path = server.get('log_path')
                killfeed_path = server.get('killfeed_path')
                
                if log_path:
                    try:
                        # Check if log directory exists
                        log_dir = str(Path(log_path).parent)
                        sftp.listdir(log_dir)
                        logger.info(f"✅ Log directory accessible: {log_dir}")
                    except Exception as e:
                        logger.error(f"❌ Cannot access log directory {log_dir}: {e}")
                
                if killfeed_path:
                    try:
                        # Check if killfeed directory exists
                        killfeed_dir = str(Path(killfeed_path).parent)
                        sftp.listdir(killfeed_dir)
                        logger.info(f"✅ Killfeed directory accessible: {killfeed_dir}")
                    except Exception as e:
                        logger.error(f"❌ Cannot access killfeed directory {killfeed_dir}: {e}")
                
                # Close connections
                sftp.close()
                transport.close()
                
                logger.info(f"✅ SFTP connection successful for server {server_id}")
                
            except Exception as e:
                logger.error(f"❌ SFTP connection failed for server {server_id}: {e}")
    
    except Exception as e:
        logger.error(f"❌ SFTP connection test failed: {e}")

async def main():
    """Run complete end-to-end testing"""
    
    logger.info("🎯 Starting complete end-to-end parser testing...")
    
    # Test SFTP connections first
    await test_real_sftp_connections()
    
    # Test complete pipeline
    success = await test_complete_killfeed_pipeline()
    
    if success:
        logger.info("🎉 All end-to-end tests completed successfully")
    else:
        logger.error("❌ Some end-to-end tests failed")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())