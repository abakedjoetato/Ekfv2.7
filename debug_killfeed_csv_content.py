"""
Debug Killfeed CSV Content - Check what's actually in the CSV file
"""

import asyncio
import logging
from bot.utils.connection_pool import connection_manager
from bot.models.database import DatabaseManager
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_csv_content():
    """Check the actual content of the killfeed CSV file"""
    try:
        # Initialize database connection
        mongo_client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
        db_manager = DatabaseManager(mongo_client)
        
        # Get guild configuration
        guild_id = 1219706687980568769
        guild_config = await db_manager.get_guild(guild_id)
        
        if not guild_config or not guild_config.get('servers'):
            logger.error("No guild configuration found")
            return
        
        server_config = guild_config['servers'][0]
        server_name = server_config.get('name', 'Unknown')
        
        logger.info(f"Checking killfeed CSV for server: {server_name}")
        
        # Start connection manager
        await connection_manager.start()
        
        # Get connection using bot's method
        async with connection_manager.get_connection(guild_id, server_config) as conn:
            if not conn:
                logger.error("Failed to get SSH connection")
                return
            
            sftp = await conn.start_sftp_client()
            
            # Check the CSV file path
            host = server_config.get('host', 'unknown')
            server_id = server_config.get('server_id', server_config.get('_id', 'unknown'))
            killfeed_path = f"./{host}_{server_id}/actual1/deathlogs/"
            
            logger.info(f"Killfeed path: {killfeed_path}")
            
            # List directories under deathlogs
            try:
                entries = await sftp.listdir(killfeed_path)
                logger.info(f"Directories under deathlogs: {entries}")
                
                # Check world_0 directory (where file was found)
                world_0_path = f"{killfeed_path}world_0/"
                csv_files = await sftp.listdir(world_0_path)
                logger.info(f"CSV files in world_0: {csv_files}")
                
                # Check the specific file that was found
                target_file = "2025.06.03-00.00.00.csv"
                if target_file in csv_files:
                    file_path = f"{world_0_path}{target_file}"
                    
                    # Get file info
                    stat_info = await sftp.stat(file_path)
                    logger.info(f"File size: {stat_info.size} bytes")
                    
                    # Read file content
                    async with sftp.open(file_path, 'rb') as file:
                        content = await file.read()
                        
                    if not content:
                        logger.warning("CSV file is empty!")
                        return
                    
                    # Decode and analyze content
                    text_content = content.decode('utf-8', errors='ignore')
                    lines = text_content.splitlines()
                    
                    logger.info(f"Total lines in CSV: {len(lines)}")
                    logger.info(f"File content length: {len(text_content)} characters")
                    
                    # Show first 10 lines
                    logger.info("First 10 lines of CSV:")
                    for i, line in enumerate(lines[:10]):
                        if line.strip():
                            logger.info(f"Line {i+1}: {line}")
                    
                    # Check line format
                    if lines:
                        sample_line = lines[0] if lines[0].strip() else (lines[1] if len(lines) > 1 else "")
                        if sample_line:
                            parts = sample_line.split(';')
                            logger.info(f"Sample line has {len(parts)} columns (semicolon-delimited)")
                            logger.info(f"Columns: {parts}")
                    
                    # Check parser state
                    from bot.utils.shared_parser_state import get_shared_state_manager, initialize_shared_state_manager
                    initialize_shared_state_manager(db_manager)
                    state_manager = get_shared_state_manager()
                    
                    current_state = await state_manager.get_parser_state(guild_id, server_name)
                    if current_state:
                        logger.info(f"Current parser state:")
                        logger.info(f"  Last file: {current_state.last_file}")
                        logger.info(f"  Last line: {current_state.last_line}")
                        logger.info(f"  Last byte position: {current_state.last_byte_position}")
                        logger.info(f"  Updated by: {current_state.updated_by_parser}")
                    else:
                        logger.info("No parser state found - first run")
                
                else:
                    logger.warning(f"Target file {target_file} not found in world_0 directory")
                    
            except Exception as e:
                logger.error(f"Error listing directories: {e}")
        
        await connection_manager.stop()
        await mongo_client.close()
        
    except Exception as e:
        logger.error(f"Debug failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(check_csv_content())