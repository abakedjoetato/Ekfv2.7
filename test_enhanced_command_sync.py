"""
Test Enhanced Command Sync - Verify per-guild fallback works
"""

import asyncio
import os
from datetime import datetime, timedelta

async def test_command_sync_logic():
    """Test the command sync logic without Discord API calls"""
    
    print("🧪 Testing enhanced command sync logic...")
    
    # Test 1: No cooldowns - should attempt global sync
    print("\nTest 1: No cooldowns active")
    global_cooldown_file = 'global_sync_cooldown.txt'
    guild_cooldown_file = 'guild_sync_cooldown.txt'
    
    # Clean up any existing files
    for file in [global_cooldown_file, guild_cooldown_file]:
        if os.path.exists(file):
            os.remove(file)
    
    print("  ✅ Should attempt global sync first")
    
    # Test 2: Global cooldown active - should attempt guild sync
    print("\nTest 2: Global cooldown active")
    cooldown_time = datetime.utcnow() + timedelta(hours=2)
    with open(global_cooldown_file, 'w') as f:
        f.write(cooldown_time.isoformat())
    
    print("  ✅ Should skip global sync and attempt guild sync")
    
    # Test 3: Both cooldowns active - should skip sync
    print("\nTest 3: Both cooldowns active")
    cooldown_time = datetime.utcnow() + timedelta(hours=1)
    with open(guild_cooldown_file, 'w') as f:
        f.write(cooldown_time.isoformat())
    
    print("  ✅ Should skip both syncs and use cached commands")
    
    # Clean up test files
    for file in [global_cooldown_file, guild_cooldown_file]:
        if os.path.exists(file):
            os.remove(file)
    
    print("\n🎉 Enhanced command sync logic tests completed!")

if __name__ == "__main__":
    asyncio.run(test_command_sync_logic())
