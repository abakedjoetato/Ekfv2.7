#!/usr/bin/env python3

"""
Test Internal Database Access - Verify /online command using bot's exact connection method
"""

import asyncio
import os
import sys
import motor.motor_asyncio

async def test_internal_database_access():
    """Test database access using bot's internal connection method"""
    print("=== INTERNAL DATABASE ACCESS TEST ===")
    
    try:
        # Initialize exactly like the bot does in main.py
        from bot.models.database import DatabaseManager
        from bot.utils.unified_cache import initialize_cache
        from bot.utils.cache_integration import create_cached_database_manager
        
        # Step 1: Initialize cache system (like bot does)
        await initialize_cache()
        print("✓ Cache system initialized")
        
        # Step 2: Create MongoDB client (like bot does)
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        print("✓ MongoDB client created")
        
        # Step 3: Create base database manager (like bot does)
        base_db_manager = DatabaseManager(mongo_client)
        print("✓ Base database manager created")
        
        # Step 4: Wrap with caching layer (like bot does)
        cached_db_manager = create_cached_database_manager(base_db_manager)
        print("✓ Cached database manager created")
        
        guild_id = 1219706687980568769
        
        # Test with cached connection (bot's actual method)
        print("\n=== TESTING WITH BOT'S CACHED CONNECTION ===")
        
        cached_total = await cached_db_manager.player_sessions.count_documents({
            'guild_id': guild_id
        })
        cached_online = await cached_db_manager.player_sessions.count_documents({
            'guild_id': guild_id,
            'state': 'online'
        })
        cached_emerald = await cached_db_manager.player_sessions.count_documents({
            'guild_id': guild_id,
            'server_name': 'Emerald EU',
            'state': 'online'
        })
        
        print(f"Cached connection results:")
        print(f"  Total sessions: {cached_total}")
        print(f"  Online sessions: {cached_online}")
        print(f"  Emerald EU online: {cached_emerald}")
        
        # Test with direct connection (external method)
        print("\n=== TESTING WITH DIRECT CONNECTION ===")
        
        direct_client = motor.motor_asyncio.AsyncIOMotorClient(os.environ.get('MONGO_URI'))
        direct_db = direct_client.emerald_killfeed
        
        direct_total = await direct_db.player_sessions.count_documents({
            'guild_id': guild_id
        })
        direct_online = await direct_db.player_sessions.count_documents({
            'guild_id': guild_id,
            'state': 'online'
        })
        direct_emerald = await direct_db.player_sessions.count_documents({
            'guild_id': guild_id,
            'server_name': 'Emerald EU',
            'state': 'online'
        })
        
        print(f"Direct connection results:")
        print(f"  Total sessions: {direct_total}")
        print(f"  Online sessions: {direct_online}")
        print(f"  Emerald EU online: {direct_emerald}")
        
        # Test with base database manager (without cache)
        print("\n=== TESTING WITH BASE DATABASE MANAGER ===")
        
        base_total = await base_db_manager.player_sessions.count_documents({
            'guild_id': guild_id
        })
        base_online = await base_db_manager.player_sessions.count_documents({
            'guild_id': guild_id,
            'state': 'online'
        })
        base_emerald = await base_db_manager.player_sessions.count_documents({
            'guild_id': guild_id,
            'server_name': 'Emerald EU',
            'state': 'online'
        })
        
        print(f"Base database manager results:")
        print(f"  Total sessions: {base_total}")
        print(f"  Online sessions: {base_online}")
        print(f"  Emerald EU online: {base_emerald}")
        
        # Analysis
        print(f"\n=== ANALYSIS ===")
        if cached_emerald > 0:
            print(f"✅ SUCCESS: Bot's cached connection shows {cached_emerald} players")
            print("   /online command should work with bot's internal connection")
        else:
            print("❌ ISSUE: Even bot's cached connection shows 0 players")
            
        if direct_emerald != cached_emerald:
            print(f"⚠️  ISOLATION: Cached ({cached_emerald}) vs Direct ({direct_emerald}) connections differ")
        else:
            print("✓ CONSISTENCY: Cached and direct connections match")
            
        if base_emerald == cached_emerald:
            print("✓ CACHE: Cache layer is transparent")
        else:
            print(f"⚠️  CACHE ISSUE: Base ({base_emerald}) vs Cached ({cached_emerald}) differ")
        
        # Clean up
        direct_client.close()
        mongo_client.close()
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_internal_database_access())