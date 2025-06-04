#!/usr/bin/env python3
"""
Explore Server Structure - Find where killfeed files are actually located
"""

import asyncio
import logging
import os
import asyncssh

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def explore_server_structure():
    """Explore the actual server directory structure"""
    try:
        conn = await asyncssh.connect(
            '79.127.236.1',
            port=8822,
            username='baked',
            password=os.getenv('SSH_PASSWORD'),
            known_hosts=None,
            kex_algs=['diffie-hellman-group14-sha1', 'diffie-hellman-group1-sha1']
        )
        
        sftp = await conn.start_sftp_client()
        
        # Start from root and explore
        logger.info("Exploring server root directory...")
        
        try:
            root_entries = await sftp.listdir('.')
            logger.info(f"Root directory contents: {root_entries}")
            
            # Look for server directories that match the pattern
            server_dirs = [entry for entry in root_entries if '79.127.236.1' in entry or 'server' in entry.lower()]
            logger.info(f"Potential server directories: {server_dirs}")
            
            for server_dir in server_dirs:
                logger.info(f"\nExploring {server_dir}:")
                try:
                    server_contents = await sftp.listdir(f'./{server_dir}')
                    logger.info(f"  Contents: {server_contents}")
                    
                    # Look for actual1 or similar directories
                    for item in server_contents:
                        if 'actual' in item.lower() or 'deadside' in item.lower():
                            actual_path = f'./{server_dir}/{item}'
                            logger.info(f"  Checking {actual_path}:")
                            try:
                                actual_contents = await sftp.listdir(actual_path)
                                logger.info(f"    Contents: {actual_contents}")
                                
                                # Look for deathlogs or similar
                                for subitem in actual_contents:
                                    if 'death' in subitem.lower() or 'kill' in subitem.lower() or 'log' in subitem.lower():
                                        death_path = f'{actual_path}/{subitem}'
                                        logger.info(f"    Found potential killfeed dir: {death_path}")
                                        try:
                                            death_contents = await sftp.listdir(death_path)
                                            logger.info(f"      Contents: {death_contents}")
                                            
                                            # Check for world directories and CSV files
                                            for death_item in death_contents:
                                                death_item_path = f'{death_path}/{death_item}'
                                                try:
                                                    stat_info = await sftp.stat(death_item_path)
                                                    if stat_info.permissions and (stat_info.permissions & 0o040000):
                                                        # It's a directory
                                                        world_contents = await sftp.listdir(death_item_path)
                                                        csv_files = [f for f in world_contents if f.endswith('.csv')]
                                                        if csv_files:
                                                            logger.info(f"        {death_item}/ has CSV files: {csv_files}")
                                                except:
                                                    pass
                                                    
                                        except Exception as e:
                                            logger.warning(f"      Could not access {death_path}: {e}")
                                            
                            except Exception as e:
                                logger.warning(f"    Could not access {actual_path}: {e}")
                                
                except Exception as e:
                    logger.warning(f"  Could not access {server_dir}: {e}")
            
            # Also check if there are any CSV files in the root or common directories
            logger.info("\nSearching for CSV files in common locations...")
            common_paths = [
                './logs',
                './Logs', 
                './deadside',
                './Deadside',
                './server',
                './Server'
            ]
            
            for path in common_paths:
                try:
                    contents = await sftp.listdir(path)
                    csv_files = [f for f in contents if f.endswith('.csv')]
                    if csv_files:
                        logger.info(f"Found CSV files in {path}: {csv_files}")
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Could not explore root directory: {e}")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(explore_server_structure())