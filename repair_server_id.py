"""
Repair Server ID - Set the _id field to 7020 for Emerald EU server
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def repair_server_id():
    """Update the Emerald EU server to have _id: 7020"""
    
    try:
        # Connect to MongoDB
        mongo_uri = os.environ.get('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        database = client.emerald_killfeed
        guild_configs = database.guild_configs
        
        # Find the guild document
        guild_doc = await guild_configs.find_one({'guild_id': 1219706687980568769})
        
        if not guild_doc:
            print("❌ Guild document not found")
            return
        
        print("Found guild document")
        servers = guild_doc.get('servers', [])
        print(f"Found {len(servers)} servers")
        
        # Find and update the Emerald EU server
        updated = False
        for i, server in enumerate(servers):
            server_name = server.get('server_name', '')
            if 'Emerald EU' in server_name or 'emerald' in server_name.lower():
                print(f"Found server: {server_name}")
                print(f"Current _id: {server.get('_id', 'NOT SET')}")
                print(f"Current server_id: {server.get('server_id', 'NOT SET')}")
                
                # Update the server with proper _id
                servers[i]['_id'] = "7020"
                servers[i]['server_id'] = "7020"
                updated = True
                print(f"✅ Updated server _id to: 7020")
                break
        
        if not updated:
            print("❌ Emerald EU server not found")
            return
        
        # Update the document in MongoDB
        result = await guild_configs.update_one(
            {'guild_id': 1219706687980568769},
            {'$set': {'servers': servers}}
        )
        
        if result.modified_count > 0:
            print("✅ Database updated successfully")
            
            # Verify the update
            updated_doc = await guild_configs.find_one({'guild_id': 1219706687980568769})
            updated_servers = updated_doc.get('servers', [])
            
            for server in updated_servers:
                if 'Emerald EU' in server.get('server_name', ''):
                    print(f"Verification - _id: {server.get('_id')}")
                    print(f"Verification - server_id: {server.get('server_id')}")
                    break
        else:
            print("❌ Database update failed")
        
        await client.close()
        
    except Exception as e:
        print(f"Error repairing server ID: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(repair_server_id())