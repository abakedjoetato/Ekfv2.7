#!/usr/bin/env python3
"""
Test script to verify mission embed delivery after fixing timestamp parameter issue
"""
import asyncio
import sys
import os
sys.path.append('.')

from bot.utils.embed_factory import EmbedFactory
from motor.motor_asyncio import AsyncIOMotorClient

async def test_mission_embed():
    """Test mission embed creation with correct signature"""
    try:
        # Test the fixed EmbedFactory method
        embed = EmbedFactory.create_mission_embed(
            title="🎯 Mission Ready",
            description="**Testing Mission** is now available for deployment",
            mission_id="GA_Test_Mission",
            level=3,
            state='READY',
            respawn_time=None
        )
        
        print(f"✅ Mission embed created successfully: {embed.title}")
        print(f"✅ Mission embed description: {embed.description}")
        
        # Reset parser state to reprocess failed mission events
        client = AsyncIOMotorClient(os.environ['MONGO_URI'])
        db = client.get_database('EmeraldDB')
        
        # Find current parser state
        current_state = await db.parser_states.find_one({
            'guild_id': 1219706687980568769, 
            'server_name': 'Emerald EU'
        })
        
        if current_state:
            print(f"Current parser position: {current_state.get('position', 'unknown')}")
            print(f"Current parser line: {current_state.get('line_number', 'unknown')}")
            
            # Reset to reprocess the mission events that failed
            await db.parser_states.update_one(
                {'guild_id': 1219706687980568769, 'server_name': 'Emerald EU'},
                {'$set': {'position': 83345, 'line_number': 819}}
            )
            print("✅ Parser state reset to reprocess failed mission events")
        
        client.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mission_embed())