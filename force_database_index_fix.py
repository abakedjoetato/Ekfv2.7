"""
Force Database Index Fix - Complete reconstruction of player sessions collection
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def force_database_index_fix():
    """Force complete reconstruction of player sessions collection"""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(os.environ['MONGO_URI'])
        db = client.emerald_killfeed
        
        print("=== FORCE DATABASE INDEX FIX ===")
        
        # Drop the entire player_sessions collection to start fresh
        await db.player_sessions.drop()
        print("✅ Dropped entire player_sessions collection")
        
        # Recreate collection with proper index immediately
        await db.create_collection("player_sessions")
        print("✅ Recreated player_sessions collection")
        
        # Create the correct unique index for EOS ID tracking
        await db.player_sessions.create_index([
            ("guild_id", 1),
            ("server_id", 1), 
            ("eos_id", 1)
        ], unique=True, name="guild_server_eos_unique")
        print("✅ Created proper guild_server_eos_unique index")
        
        # Verify indexes
        indexes = await db.player_sessions.list_indexes().to_list(None)
        print(f"📋 Current indexes: {[idx['name'] for idx in indexes]}")
        
        # Verify collection is empty
        count = await db.player_sessions.count_documents({})
        print(f"📊 Player sessions count: {count}")
        
        client.close()
        print("✅ Database index fix completed!")
        
    except Exception as e:
        logger.error(f"Error forcing database fix: {e}")

if __name__ == "__main__":
    asyncio.run(force_database_index_fix())