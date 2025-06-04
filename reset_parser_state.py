#!/usr/bin/env python3
"""Reset parser state to reprocess mission events"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def reset_parser_state():
    client = AsyncIOMotorClient(os.environ['MONGO_URI'])
    db = client.get_database('EmeraldDB')
    
    # Reset parser state to reprocess the 10 mission events that failed
    result = await db.parser_states.update_one(
        {"guild_id": 1219706687980568769, "server_name": "Emerald EU"},
        {"$set": {"position": 83345, "line_number": 819}}
    )
    
    print(f"Parser state reset: {result.modified_count} document updated")
    client.close()

if __name__ == "__main__":
    asyncio.run(reset_parser_state())