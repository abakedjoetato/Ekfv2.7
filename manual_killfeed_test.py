#!/usr/bin/env python3
"""
Manual Killfeed Test - Test killfeed discovery and processing
"""

import asyncio
import logging
import motor.motor_asyncio
import os
from bot.utils.connection_pool import GlobalConnectionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_killfeed_discovery():
    """Test killfeed file discovery on the server"""
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
        
        # Create connection manager
        connection_manager = GlobalConnectionManager()
        
        # Calculate dynamic killfeed path
        host = server.get('host', 'unknown')
        server_id = server.get('_id', 'unknown')
        killfeed_path = f'./{host}_{server_id}/actual1/deathlogs/'
        
        logger.info(f"Testing killfeed discovery for {server.get('name')}")
        logger.info(f"Dynamic killfeed path: {killfeed_path}")
        
        # Connect and list files
        async with connection_manager.get_connection(1219706687980568769, server) as conn:
            if not conn:
                logger.error("Failed to establish connection")
                return
            
            sftp = await conn.start_sftp_client()
            
            try:
                # Try to list the killfeed directory
                files = await sftp.listdir(killfeed_path)
                csv_files = [f for f in files if f.endswith('.csv')]
                
                logger.info(f"Found {len(files)} total files in {killfeed_path}")
                logger.info(f"Found {len(csv_files)} CSV files: {csv_files}")
                
                if csv_files:
                    # Get the newest CSV file
                    newest_file = sorted(csv_files)[-1]
                    logger.info(f"Newest CSV file: {newest_file}")
                    
                    # Try to read a few lines from the file
                    file_path = f"{killfeed_path.rstrip('/')}/{newest_file}"
                    async with sftp.open(file_path, 'rb') as file:
                        content = await file.read(1024)  # Read first 1KB
                        lines = content.decode('utf-8', errors='ignore').splitlines()
                        logger.info(f"First few lines of {newest_file}:")
                        for i, line in enumerate(lines[:5]):
                            logger.info(f"  Line {i+1}: {line}")
                else:
                    logger.warning("No CSV files found - killfeeds may not be enabled on server")
                    
            except Exception as e:
                logger.error(f"Could not access killfeed directory {killfeed_path}: {e}")
                
                # Try alternate paths
                alternate_paths = [
                    f'./{host}_{server_id}/actual1/',
                    f'./{host}_{server_id}/',
                    './deathlogs/',
                    '/home/deadside/killfeed/'
                ]
                
                for alt_path in alternate_paths:
                    try:
                        files = await sftp.listdir(alt_path)
                        logger.info(f"Found files in alternate path {alt_path}: {files}")
                        break
                    except:
                        continue
        
        await connection_manager.cleanup()
        client.close()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_killfeed_discovery())