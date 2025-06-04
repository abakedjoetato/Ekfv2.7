#!/usr/bin/env python3
"""
Test Killfeed Fix - Manually trigger killfeed parser with recursive CSV discovery
"""

import asyncio
import logging
import motor.motor_asyncio
import os
import sys

# Add the bot directory to Python path
sys.path.insert(0, '/home/runner/workspace')

from bot.utils.connection_pool import GlobalConnectionManager
from bot.utils.shared_parser_state import get_shared_state_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_recursive_csv_discovery():
    """Test the recursive CSV discovery that matches historical parser"""
    try:
        # Connect to database
        client = motor.motor_asyncio.AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        db = client.emerald_killfeed
        
        # Get server configuration
        guild_config = await db.guild_configs.find_one({
            'guild_id': 1219706687980568769
        })
        
        if not guild_config:
            logger.error("No guild configuration found")
            return
        
        servers = guild_config.get('servers', [])
        if not servers:
            logger.error("No servers configured")
            return
        
        server = servers[0]  # Get first server (Emerald EU)
        
        # Create connection manager and state manager
        connection_manager = GlobalConnectionManager()
        state_manager = get_shared_state_manager()
        
        # Calculate dynamic killfeed path
        host = server.get('host', 'unknown')
        server_id = server.get('_id', 'unknown')
        killfeed_path = f'./{host}_{server_id}/actual1/deathlogs/'
        
        logger.info(f"Testing recursive CSV discovery for {server.get('name')}")
        logger.info(f"Dynamic killfeed path: {killfeed_path}")
        
        # Connect and use glob pattern like historical parser
        async with connection_manager.get_connection(1219706687980568769, server) as conn:
            if not conn:
                logger.error("Failed to establish connection")
                return
            
            sftp = await conn.start_sftp_client()
            
            # Use recursive glob pattern (same as historical parser)
            pattern = f"{killfeed_path}**/*.csv"
            logger.info(f"Using glob pattern: {pattern}")
            
            try:
                # Test glob discovery
                paths = await sftp.glob(pattern)
                logger.info(f"Glob discovery: Found {len(paths)} CSV files")
                
                for path in paths:
                    filename = path.split('/')[-1]
                    logger.info(f"Found CSV file: {filename} (full path: {path})")
                    
                    # Get file stats
                    try:
                        stat_result = await sftp.stat(path)
                        size = getattr(stat_result, 'size', 0)
                        logger.info(f"  File size: {size} bytes")
                    except Exception as e:
                        logger.warning(f"  Could not get file stats: {e}")
                
                if paths:
                    logger.info(f"SUCCESS: Recursive discovery found {len(paths)} CSV files")
                    logger.info("The killfeed parser should now be able to find and process these files")
                else:
                    logger.warning("No CSV files found even with recursive discovery")
                    
                    # Check what directories exist
                    try:
                        dirs = await sftp.listdir(killfeed_path)
                        logger.info(f"Directories in {killfeed_path}: {dirs}")
                        
                        for dir_name in dirs:
                            subdir_path = f"{killfeed_path}{dir_name}/"
                            try:
                                subfiles = await sftp.listdir(subdir_path)
                                logger.info(f"Files in {subdir_path}: {subfiles}")
                            except:
                                pass
                    except Exception as e:
                        logger.error(f"Could not list directories: {e}")
                        
            except Exception as e:
                logger.error(f"Glob pattern discovery failed: {e}")
                
                # Test fallback directory listing
                try:
                    all_files = await sftp.listdir(killfeed_path)
                    csv_files = [f for f in all_files if f.endswith('.csv')]
                    logger.info(f"Fallback directory listing: Found {len(csv_files)} CSV files: {csv_files}")
                except Exception as e2:
                    logger.error(f"Fallback directory listing also failed: {e2}")
        
        client.close()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_recursive_csv_discovery())