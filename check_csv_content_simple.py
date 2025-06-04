#!/usr/bin/env python3
"""
Simple CSV Content Check - Direct examination of the killfeed CSV file
"""

import asyncio
import logging
import os
import asyncssh

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_csv_content():
    """Check actual CSV content"""
    try:
        # Connect directly using SSH credentials
        conn = await asyncssh.connect(
            '79.127.236.1',
            port=8822,
            username='baked',
            password=os.getenv('SSH_PASSWORD'),
            known_hosts=None,
            kex_algs=['diffie-hellman-group14-sha1', 'diffie-hellman-group1-sha1']
        )
        
        sftp = await conn.start_sftp_client()
        
        # Path to CSV file that was found by parser
        csv_path = './79.127.236.1_44424/actual1/deathlogs/world_0/2025.06.03-00.00.00.csv'
        
        logger.info(f"Checking CSV file: {csv_path}")
        
        try:
            # Get file stats
            stat_info = await sftp.stat(csv_path)
            file_size = stat_info.size
            logger.info(f"File size: {file_size} bytes")
            
            if file_size == 0:
                logger.warning("CSV file is completely empty!")
                return
            
            # Read file content
            async with sftp.open(csv_path, 'r') as file:
                content = await file.read()
                
            if not content or not content.strip():
                logger.warning("CSV file contains no content or only whitespace!")
                return
            
            lines = content.strip().split('\n')
            logger.info(f"Total lines in CSV: {len(lines)}")
            
            # Show first few lines
            logger.info("First 5 lines of CSV:")
            for i, line in enumerate(lines[:5]):
                logger.info(f"Line {i+1}: '{line}'")
            
            # Check format
            if lines:
                sample_line = lines[0]
                parts = sample_line.split(';')
                logger.info(f"Line format: {len(parts)} columns (semicolon-separated)")
                logger.info(f"Columns: {parts}")
                
                # Check if it matches expected killfeed format
                if len(parts) >= 9:
                    logger.info("✅ Format looks correct (9+ columns)")
                else:
                    logger.warning(f"❌ Format issue: only {len(parts)} columns, need 9+")
            
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_csv_content())