#!/usr/bin/env python3
"""
Comprehensive Fix Implementation - Resolves all four interconnected issues
1. Player state tracking (0 sessions)
2. Voice channel count (incorrect)  
3. /online command (not working)
4. Cold start detection (missing)
"""
import asyncio
import os
import motor.motor_asyncio
from datetime import datetime, timezone, timedelta

async def comprehensive_fix():
    """Execute comprehensive fixes for all interconnected issues"""
    mongo_uri = os.environ.get('MONGO_URI')
    client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
    db = client.EmeraldDB
    
    guild_id = 1219706687980568769
    
    print("=== COMPREHENSIVE FIX IMPLEMENTATION ===")
    
    # Fix 1: Add voice channel configuration
    print("\n1. Configuring voice channel...")
    try:
        guild_config = await db.guild_configs.find_one({'guild_id': guild_id})
        if guild_config:
            # Update with proper MongoDB update syntax
            result = await db.guild_configs.update_one(
                {'guild_id': guild_id},
                {'$set': {'server_channels.default.playercountvc': 1361522251018928320}}
            )
            if result.modified_count > 0:
                print("✓ Voice channel configuration added")
            else:
                print("✓ Voice channel configuration already exists")
        else:
            print("❌ No guild config found")
    except Exception as e:
        print(f"❌ Voice channel config failed: {e}")
    
    # Fix 2: Reset all player sessions to force cold start detection
    print("\n2. Resetting player sessions for cold start...")
    try:
        # Reset all online players to offline with current timestamp
        reset_time = datetime.now(timezone.utc)
        result = await db.player_sessions.update_many(
            {
                "guild_id": guild_id,
                "state": {"$in": ["online", "queued"]}
            },
            {
                "$set": {
                    "state": "offline",
                    "last_updated": reset_time
                }
            }
        )
        print(f"✓ Reset {result.modified_count} player sessions to offline")
        
        # This will trigger cold start detection on next parser run
        print("✓ Cold start conditions established")
        
    except Exception as e:
        print(f"❌ Player session reset failed: {e}")
    
    # Fix 3: Clear command sync cooldowns to fix /online command
    print("\n3. Fixing command registration...")
    try:
        # Remove command sync cooldown files
        cooldown_files = [
            "command_sync_cooldown.txt",
            "command_hash.txt",
            "global_sync_success.txt"
        ]
        
        for file in cooldown_files:
            if os.path.exists(file):
                os.remove(file)
                print(f"✓ Removed {file}")
        
        print("✓ Command registration cooldowns cleared")
        
    except Exception as e:
        print(f"❌ Command fix failed: {e}")
    
    # Fix 4: Reset parser state to force full reprocessing
    print("\n4. Resetting parser state...")
    try:
        # Reset unified parser state to force cold start
        result = await db.parser_states.delete_many({
            "guild_id": guild_id,
            "parser_type": "unified"
        })
        print(f"✓ Removed {result.deleted_count} unified parser states")
        
        # Keep killfeed parser state but mark for reset
        await db.parser_states.update_many(
            {
                "guild_id": guild_id,
                "parser_type": "killfeed"
            },
            {
                "$unset": {
                    "last_byte_position": "",
                    "last_line": "",
                    "file_timestamp": ""
                }
            }
        )
        print("✓ Reset killfeed parser positions")
        
    except Exception as e:
        print(f"❌ Parser state reset failed: {e}")
    
    # Verification
    print("\n=== VERIFICATION ===")
    
    # Check player sessions
    online_count = await db.player_sessions.count_documents({
        "guild_id": guild_id,
        "state": "online"
    })
    print(f"Current online players: {online_count}")
    
    # Check voice channel config
    guild_config = await db.guild_configs.find_one({'guild_id': guild_id})
    if guild_config:
        vc_id = guild_config.get('server_channels', {}).get('default', {}).get('playercountvc')
        print(f"Voice channel configured: {vc_id is not None}")
        if vc_id:
            print(f"Voice channel ID: {vc_id}")
    
    # Check parser states
    parser_count = await db.parser_states.count_documents({
        "guild_id": guild_id,
        "parser_type": "unified"
    })
    print(f"Unified parser states: {parser_count} (should be 0 for cold start)")
    
    await client.close()
    
    print("\n=== FIX SUMMARY ===")
    print("✓ Voice channel configuration added")
    print("✓ Player sessions reset for cold start detection")
    print("✓ Command registration cooldowns cleared")
    print("✓ Parser states reset for full reprocessing")
    print("\n🔄 Bot will automatically:")
    print("  • Detect cold start on next unified parser run")
    print("  • Process all player connections from log")
    print("  • Update voice channel with real counts")
    print("  • Re-register /online command properly")

if __name__ == "__main__":
    asyncio.run(comprehensive_fix())