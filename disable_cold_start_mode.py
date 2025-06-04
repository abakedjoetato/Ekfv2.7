"""
Disable Cold Start Mode - Enable embed delivery for killfeed events
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def disable_cold_start():
    """Disable cold start mode to enable embed delivery"""
    try:
        client = AsyncIOMotorClient(os.environ.get("MONGO_URI"))
        db = client.emerald_killfeed
        
        guild_id = 1219706687980568769
        
        print("Disabling cold start mode...")
        
        # Clear cold start flags
        result = await db.guild_configs.update_one(
            {"guild_id": guild_id},
            {"$unset": {"cold_start": 1}}
        )
        
        print(f"Updated guild config: {result.modified_count} documents")
        
        # Clear parser states cold start flags
        parser_result = await db.parser_states.update_many(
            {"guild_id": guild_id},
            {"$unset": {"cold_start": 1}}
        )
        
        print(f"Updated parser states: {parser_result.modified_count} documents")
        
        # Check current state
        guild_config = await db.guild_configs.find_one({"guild_id": guild_id})
        if guild_config:
            cold_start = guild_config.get("cold_start", False)
            print(f"Guild cold start status: {cold_start}")
        
        # Check parser states
        parser_states = await db.parser_states.find({"guild_id": guild_id}).to_list(length=None)
        for state in parser_states:
            server_id = state.get("server_id", "unknown")
            cold_start = state.get("cold_start", False)
            print(f"Parser state {server_id} cold start: {cold_start}")
        
        client.close()
        print("✅ Cold start mode disabled - embeds should now be delivered")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(disable_cold_start())