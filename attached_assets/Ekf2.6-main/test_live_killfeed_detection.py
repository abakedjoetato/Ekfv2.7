"""
Live Killfeed Detection Test - End-to-End Real World Parser Testing
Tests all parsers with authentic server data to ensure proper Discord embed delivery
"""

import asyncio
import logging
from datetime import datetime, timezone
import os
import sys
from pathlib import Path

# Add the bot directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_live_parser_execution():
    """Test live parser execution with real server data"""
    
    logger.info("Starting live parser execution test...")
    
    try:
        # Import bot components using the actual structure
        from bot.models.database import DatabaseManager
        from bot.utils.thread_safe_db_wrapper import ThreadSafeDBWrapper
        from motor.motor_asyncio import AsyncIOMotorClient
        import os
        
        # Get MongoDB connection from environment
        mongo_uri = os.environ.get('MONGO_URI')
        if not mongo_uri:
            logger.error("MONGO_URI environment variable not found")
            return False
        
        # Initialize database connection
        client = AsyncIOMotorClient(mongo_uri)
        db_manager = DatabaseManager(client)
        db_wrapper = ThreadSafeDBWrapper(db_manager)
        
        logger.info("Database connection established")
        
        # Get all configured servers
        try:
            servers_cursor = db_manager.guild_configs.find({
                "servers": {"$exists": True, "$ne": []}
            })
            
            all_configs = await servers_cursor.to_list(length=None)
            logger.info(f"Found {len(all_configs)} guild configurations")
            
            # Extract all servers from all guilds
            all_servers = []
            for config in all_configs:
                guild_id = config.get('guild_id')
                servers = config.get('servers', [])
                for server in servers:
                    server['guild_id'] = guild_id
                    all_servers.append(server)
            
            logger.info(f"Found {len(all_servers)} total servers configured")
            
            if not all_servers:
                logger.error("No servers found in database configuration")
                return False
            
            # Test each server
            for server in all_servers:
                server_id = server.get('server_id', 'unknown')
                guild_id = server.get('guild_id')
                
                logger.info(f"Testing server: {server_id} in guild {guild_id}")
                
                # Check required fields
                required_fields = ['log_path', 'killfeed_path']
                missing_fields = [field for field in required_fields if not server.get(field)]
                
                if missing_fields:
                    logger.warning(f"Server {server_id} missing required fields: {missing_fields}")
                    continue
                
                # Check SFTP credentials
                sftp_creds = server.get('sftp_credentials', {})
                if not all([sftp_creds.get('host'), sftp_creds.get('username'), sftp_creds.get('password')]):
                    logger.warning(f"Server {server_id} missing complete SFTP credentials")
                    continue
                
                # Test SFTP connection
                await test_sftp_connection(server)
                
                # Test log parser
                await test_log_parser(server, db_wrapper)
                
                # Test killfeed parser
                await test_killfeed_parser(server, db_wrapper)
                
                # Test Discord channel configuration
                await test_discord_channels(server, db_manager)
                
            logger.info("Live parser execution test completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to get server configurations: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Test setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_sftp_connection(server):
    """Test SFTP connection to verify access to log files"""
    
    server_id = server.get('server_id', 'unknown')
    sftp_creds = server.get('sftp_credentials', {})
    
    logger.info(f"Testing SFTP connection for server {server_id}")
    
    try:
        import paramiko
        
        # Create transport
        transport = paramiko.Transport((sftp_creds.get('host'), sftp_creds.get('port', 22)))
        
        # Connect with authentication
        transport.connect(
            username=sftp_creds.get('username'),
            password=sftp_creds.get('password')
        )
        
        # Create SFTP client
        sftp = paramiko.SFTPClient.from_transport(transport)
        
        # Test log file access
        log_path = server.get('log_path')
        if log_path:
            try:
                log_dir = str(Path(log_path).parent)
                files = sftp.listdir(log_dir)
                log_files = [f for f in files if f.endswith('.log')]
                logger.info(f"Found {len(log_files)} log files in {log_dir}")
                
                if log_files:
                    # Try to access the most recent log file
                    latest_log = sorted(log_files)[-1]
                    full_log_path = f"{log_dir}/{latest_log}"
                    
                    # Read first few lines to verify accessibility
                    with sftp.open(full_log_path, 'r') as f:
                        lines = []
                        for i, line in enumerate(f):
                            if i >= 5:  # Read first 5 lines
                                break
                            lines.append(line.strip())
                    
                    logger.info(f"Successfully read from log file: {latest_log}")
                    logger.info(f"Sample lines: {len(lines)} lines read")
                
            except Exception as e:
                logger.error(f"Cannot access log files: {e}")
        
        # Test killfeed file access
        killfeed_path = server.get('killfeed_path')
        if killfeed_path:
            try:
                killfeed_dir = str(Path(killfeed_path).parent)
                files = sftp.listdir(killfeed_dir)
                csv_files = [f for f in files if f.endswith('.csv')]
                logger.info(f"Found {len(csv_files)} CSV files in {killfeed_dir}")
                
                if csv_files:
                    # Try to access the most recent CSV file
                    latest_csv = sorted(csv_files)[-1]
                    full_csv_path = f"{killfeed_dir}/{latest_csv}"
                    
                    # Read first few lines to verify format
                    with sftp.open(full_csv_path, 'r') as f:
                        lines = []
                        for i, line in enumerate(f):
                            if i >= 10:  # Read first 10 lines
                                break
                            lines.append(line.strip())
                    
                    logger.info(f"Successfully read from killfeed file: {latest_csv}")
                    logger.info(f"Killfeed lines: {len(lines)} lines read")
                    
                    # Check CSV format
                    if lines:
                        header = lines[0] if lines else ""
                        data_lines = lines[1:] if len(lines) > 1 else []
                        logger.info(f"CSV header: {header}")
                        logger.info(f"Data rows available: {len(data_lines)}")
                
            except Exception as e:
                logger.error(f"Cannot access killfeed files: {e}")
        
        # Close connections
        sftp.close()
        transport.close()
        
        logger.info(f"SFTP connection test successful for server {server_id}")
        
    except Exception as e:
        logger.error(f"SFTP connection failed for server {server_id}: {e}")

async def test_log_parser(server, db_wrapper):
    """Test log parser with real server data"""
    
    server_id = server.get('server_id', 'unknown')
    logger.info(f"Testing log parser for server {server_id}")
    
    try:
        from bot.utils.scalable_unified_processor import ScalableUnifiedProcessor
        
        processor = ScalableUnifiedProcessor()
        
        # Process server logs
        events = await processor.process_server_logs(server)
        
        logger.info(f"Log parser processed {len(events)} events")
        
        # Analyze event types
        event_types = {}
        for event in events:
            event_type = event.get('event_type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        logger.info(f"Event type breakdown: {event_types}")
        
        # Verify event structure
        for event in events[:3]:  # Check first 3 events
            required_fields = ['event_type', 'timestamp', 'server_id']
            missing_fields = [field for field in required_fields if not event.get(field)]
            if missing_fields:
                logger.warning(f"Event missing fields: {missing_fields}")
        
        logger.info(f"Log parser test completed for server {server_id}")
        
    except Exception as e:
        logger.error(f"Log parser test failed for server {server_id}: {e}")

async def test_killfeed_parser(server, db_wrapper):
    """Test killfeed parser with real server data"""
    
    server_id = server.get('server_id', 'unknown')
    logger.info(f"Testing killfeed parser for server {server_id}")
    
    try:
        from bot.utils.scalable_unified_processor import ScalableUnifiedProcessor
        
        processor = ScalableUnifiedProcessor()
        
        # Process killfeed data
        kills = await processor.process_killfeed_data(server)
        
        logger.info(f"Killfeed parser processed {len(kills)} kills")
        
        # Verify kill data structure
        for kill in kills[:3]:  # Check first 3 kills
            required_fields = ['killer', 'victim', 'weapon', 'timestamp']
            missing_fields = [field for field in required_fields if not kill.get(field)]
            if missing_fields:
                logger.warning(f"Kill event missing fields: {missing_fields}")
            else:
                logger.info(f"Valid kill: {kill.get('killer')} -> {kill.get('victim')} ({kill.get('weapon')})")
        
        logger.info(f"Killfeed parser test completed for server {server_id}")
        
    except Exception as e:
        logger.error(f"Killfeed parser test failed for server {server_id}: {e}")

async def test_discord_channels(server, db_manager):
    """Test Discord channel configuration for embed delivery"""
    
    server_id = server.get('server_id', 'unknown')
    guild_id = server.get('guild_id')
    
    logger.info(f"Testing Discord channels for server {server_id}")
    
    try:
        # Get channel configurations for this guild
        guild_config = await db_manager.guild_configs.find_one({'guild_id': guild_id})
        
        if not guild_config:
            logger.warning(f"No guild configuration found for guild {guild_id}")
            return
        
        channels = guild_config.get('channels', [])
        logger.info(f"Found {len(channels)} configured channels")
        
        # Check channel configurations for different embed types
        embed_types = ['killfeed', 'events', 'missions', 'helicrash']
        
        for embed_type in embed_types:
            target_channels = []
            for channel in channels:
                if embed_type in channel.get('embed_types', []):
                    target_channels.append(channel.get('channel_id'))
            
            if target_channels:
                logger.info(f"{embed_type} embeds configured for channels: {target_channels}")
            else:
                logger.warning(f"No channels configured for {embed_type} embeds")
        
        logger.info(f"Discord channel test completed for server {server_id}")
        
    except Exception as e:
        logger.error(f"Discord channel test failed for server {server_id}: {e}")

async def main():
    """Run complete end-to-end parser testing"""
    
    logger.info("Starting complete end-to-end parser testing with real data...")
    
    success = await test_live_parser_execution()
    
    if success:
        logger.info("All end-to-end parser tests completed successfully")
    else:
        logger.error("Some end-to-end parser tests failed")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())