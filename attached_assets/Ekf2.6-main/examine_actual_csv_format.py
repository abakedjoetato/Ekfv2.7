#!/usr/bin/env python3

"""
Examine Actual CSV Format
Direct examination of the CSV file format to understand why parsing is failing
"""

import asyncio
import logging
import os
import asyncssh

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def examine_csv_format():
    """Examine the actual CSV format to fix parsing"""
    try:
        logger.info("=== Examining Actual CSV Format ===")
        
        # Connect to the server directly
        conn = await asyncssh.connect(
            '79.127.236.1', 
            port=8822,
            username='baked',
            password=os.environ.get('SSH_PASSWORD'),
            known_hosts=None
        )
        
        sftp = await conn.start_sftp_client()
        
        # Get the latest CSV file
        csv_path = "./79.127.236.1_7020/actual1/deathlogs/world_0/2025.06.03-00.00.00.csv"
        
        logger.info(f"Reading CSV file: {csv_path}")
        
        try:
            async with sftp.open(csv_path, 'r') as file:
                content = await file.read()
                lines = content.splitlines()
                
                logger.info(f"Total lines in CSV: {len(lines)}")
                
                # Examine first few lines
                for i, line in enumerate(lines[:10]):
                    if line.strip():
                        parts = line.split(',')
                        logger.info(f"Line {i+1} ({len(parts)} columns): {line}")
                        
                        # Show column breakdown
                        for j, part in enumerate(parts):
                            logger.info(f"  Column {j}: '{part.strip()}'")
                        
                        if i >= 2:  # Show first 3 actual data lines
                            break
                
                # Check if it's semicolon-delimited instead
                logger.info("\n=== Checking semicolon delimiter ===")
                for i, line in enumerate(lines[:3]):
                    if line.strip():
                        parts = line.split(';')
                        if len(parts) > 1:
                            logger.info(f"Line {i+1} with semicolons ({len(parts)} columns): {line}")
                            for j, part in enumerate(parts):
                                logger.info(f"  Column {j}: '{part.strip()}'")
                
        except Exception as e:
            logger.error(f"Failed to read CSV file: {e}")
        
        await conn.close()
        
    except Exception as e:
        logger.error(f"Examination failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(examine_csv_format())