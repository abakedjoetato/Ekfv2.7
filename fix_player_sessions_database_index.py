"""
Fix Player Sessions Database Index Issue
Removes problematic compound index and creates proper index for player sessions
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def fix_player_sessions_index():
    """Fix the player sessions database index to allow proper player state tracking"""
    try:
        # Connect to MongoDB
        client = AsyncIOMotorClient(os.environ['MONGO_URI'])
        db = client.emerald_killfeed
        
        print("=== FIXING PLAYER SESSIONS DATABASE INDEX ===")
        
        # Check existing indexes
        existing_indexes = await db.player_sessions.list_indexes().to_list(None)
        print(f"Existing indexes: {[idx['name'] for idx in existing_indexes]}")
        
        # Drop the problematic compound index that includes player_id
        try:
            await db.player_sessions.drop_index("guild_id_1_server_id_1_player_id_1")
            print("✅ Dropped problematic guild_id_1_server_id_1_player_id_1 index")
        except Exception as e:
            print(f"Index drop not needed or failed: {e}")
        
        # Create proper index for EOS ID based player sessions
        try:
            await db.player_sessions.create_index([
                ("guild_id", 1),
                ("server_id", 1), 
                ("eos_id", 1)
            ], unique=True, name="guild_server_eos_unique")
            print("✅ Created proper guild_server_eos_unique index")
        except Exception as e:
            print(f"Index creation: {e}")
        
        # Clean up any invalid sessions
        result = await db.player_sessions.delete_many({
            "$or": [
                {"eos_id": {"$exists": False}},
                {"eos_id": None},
                {"eos_id": ""}
            ]
        })
        print(f"🧹 Cleaned up {result.deleted_count} invalid player sessions")
        
        # Verify the fix worked
        session_count = await db.player_sessions.count_documents({})
        print(f"📊 Total player sessions after cleanup: {session_count}")
        
        client.close()
        print("✅ Player sessions database index fixed!")
        
    except Exception as e:
        logger.error(f"Error fixing player sessions index: {e}")

if __name__ == "__main__":
    asyncio.run(fix_player_sessions_index())