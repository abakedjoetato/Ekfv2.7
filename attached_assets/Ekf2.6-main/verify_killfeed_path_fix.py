#!/usr/bin/env python3
"""
Verify Killfeed Path Fix
Test the corrected path structure: ./{host}_{server_id}/actual1/deathlogs/ with subdirectory searching
"""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock
from bot.utils.simple_killfeed_processor import SimpleKillfeedProcessor

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockSFTPAttrs:
    def __init__(self, is_dir=False):
        self.permissions = 0o040755 if is_dir else 0o100644

class MockSFTP:
    def __init__(self):
        # Simulate directory structure: deathlogs/world_0/ contains CSV files
        self.file_structure = {
            './79.127.236.1_24242/actual1/deathlogs/': ['world_0', 'world_1', 'some_file.txt'],
            './79.127.236.1_24242/actual1/deathlogs/world_0/': [
                'DeathLogs_2025-06-03_20-30-00.csv',
                'DeathLogs_2025-06-03_21-45-00.csv',
                'DeathLogs_2025-06-03_22-15-00.csv'
            ],
            './79.127.236.1_24242/actual1/deathlogs/world_1/': [
                'DeathLogs_2025-06-03_19-30-00.csv'
            ]
        }
    
    async def listdir(self, path):
        """Mock listdir that returns predefined file structure"""
        logger.info(f"Mock SFTP listdir: {path}")
        return self.file_structure.get(path, [])
    
    async def stat(self, path):
        """Mock stat that identifies directories vs files"""
        # Determine if path is directory based on structure
        is_dir = False
        if path.endswith('world_0') or path.endswith('world_1'):
            is_dir = True
        elif path in self.file_structure:
            is_dir = True
        
        logger.info(f"Mock SFTP stat: {path} -> {'directory' if is_dir else 'file'}")
        return MockSFTPAttrs(is_dir=is_dir)

class MockConnection:
    def __init__(self):
        self.sftp = MockSFTP()
    
    async def start_sftp_client(self):
        return self.sftp

class MockConnectionManager:
    def get_connection(self, guild_id, server_config):
        return self
    
    async def __aenter__(self):
        return MockConnection()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

async def verify_killfeed_path_fix():
    """Verify the corrected killfeed path with subdirectory searching"""
    
    logger.info("=== Verifying Killfeed Path Fix ===")
    
    # Test server config
    server_config = {
        'host': '79.127.236.1',
        'server_id': '24242',
        'name': 'Emerald EU',
        'port': 8822,
        'username': 'baked',
        'auth_method': 'modern_secure'
    }
    
    guild_id = 1219706687980568769
    
    try:
        # Create processor
        processor = SimpleKillfeedProcessor(guild_id, server_config)
        
        # Mock the connection manager
        import bot.utils.simple_killfeed_processor
        original_connection_manager = bot.utils.simple_killfeed_processor.connection_manager
        bot.utils.simple_killfeed_processor.connection_manager = MockConnectionManager()
        
        logger.info(f"✅ Killfeed path: {processor._get_killfeed_path()}")
        
        # Test CSV file discovery with subdirectory searching
        logger.info("Testing subdirectory CSV discovery...")
        newest_file = await processor._discover_newest_csv_file()
        
        if newest_file:
            logger.info(f"✅ Found newest killfeed file: {newest_file}")
            if processor._current_subdir:
                logger.info(f"✅ Found in subdirectory: {processor._current_subdir}")
                logger.info(f"✅ Full path would be: {processor._get_killfeed_path()}{processor._current_subdir}/{newest_file}")
            else:
                logger.info("✅ Found in root deathlogs directory")
                logger.info(f"✅ Full path would be: {processor._get_killfeed_path()}{newest_file}")
        else:
            logger.error("❌ No killfeed files found")
            return False
        
        # Verify the path structure is correct
        expected_path = "./79.127.236.1_24242/actual1/deathlogs/"
        actual_path = processor._get_killfeed_path()
        
        if actual_path == expected_path:
            logger.info(f"✅ Path structure correct: {actual_path}")
        else:
            logger.error(f"❌ Path structure incorrect. Expected: {expected_path}, Got: {actual_path}")
            return False
        
        # Verify subdirectory detection
        if processor._current_subdir in ['world_0', 'world_1']:
            logger.info(f"✅ Subdirectory detection working: {processor._current_subdir}")
        else:
            logger.error(f"❌ Subdirectory detection failed: {processor._current_subdir}")
            return False
        
        # Verify newest file selection
        if newest_file == 'DeathLogs_2025-06-03_22-15-00.csv':
            logger.info("✅ Newest file selection working correctly")
        else:
            logger.error(f"❌ Newest file selection incorrect: {newest_file}")
            return False
        
        # Restore original connection manager
        bot.utils.simple_killfeed_processor.connection_manager = original_connection_manager
        
        logger.info("✅ Killfeed path fix verification completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(verify_killfeed_path_fix())
    if success:
        print("\n🎉 VERIFICATION PASSED: Killfeed path fix is working correctly")
    else:
        print("\n❌ VERIFICATION FAILED: Killfeed path fix needs attention")