#!/usr/bin/env python3
"""
List Actual Killfeed Files - See what's really in the deathlogs directories
"""

import asyncio
import logging
import os
import asyncssh

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def list_killfeed_files():
    """List all files in killfeed directories"""
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
        
        # Check the main deathlogs directory
        deathlogs_path = './79.127.236.1_44424/actual1/deathlogs/'
        
        logger.info(f"Listing contents of: {deathlogs_path}")
        
        try:
            # List subdirectories
            entries = await sftp.listdir(deathlogs_path)
            logger.info(f"Subdirectories found: {entries}")
            
            for entry in entries:
                subdir_path = f"{deathlogs_path}{entry}/"
                logger.info(f"\nChecking subdirectory: {entry}")
                
                try:
                    # Check if it's a directory
                    stat_info = await sftp.stat(subdir_path)
                    if stat_info.permissions and (stat_info.permissions & 0o040000):
                        # List files in this subdirectory
                        files = await sftp.listdir(subdir_path)
                        logger.info(f"  Files in {entry}: {files}")
                        
                        # Check CSV files specifically
                        csv_files = [f for f in files if f.endswith('.csv')]
                        if csv_files:
                            logger.info(f"  CSV files: {csv_files}")
                            
                            # Check the newest CSV file
                            newest_csv = max(csv_files) if csv_files else None
                            if newest_csv:
                                csv_file_path = f"{subdir_path}{newest_csv}"
                                try:
                                    csv_stat = await sftp.stat(csv_file_path)
                                    logger.info(f"  Newest CSV: {newest_csv} (size: {csv_stat.size} bytes)")
                                    
                                    if csv_stat.size > 0:
                                        # Read first few lines
                                        async with sftp.open(csv_file_path, 'r') as file:
                                            content = await file.read(500)  # Read first 500 chars
                                            lines = content.split('\n')[:3]  # First 3 lines
                                            logger.info(f"  First lines: {lines}")
                                    else:
                                        logger.info(f"  File is empty")
                                        
                                except Exception as e:
                                    logger.warning(f"  Could not read {newest_csv}: {e}")
                        else:
                            logger.info(f"  No CSV files found in {entry}")
                    else:
                        logger.info(f"  {entry} is not a directory")
                        
                except Exception as e:
                    logger.warning(f"Could not access {entry}: {e}")
                    
        except Exception as e:
            logger.error(f"Could not list deathlogs directory: {e}")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(list_killfeed_files())