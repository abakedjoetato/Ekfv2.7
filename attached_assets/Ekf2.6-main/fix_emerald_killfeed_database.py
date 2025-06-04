"""
Fix Emerald Killfeed Database - Remove hardcoded log_path from the correct database
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_emerald_killfeed_db():
    """Remove hardcoded log_path from emerald_killfeed database"""
    try:
        # Connect to the correct database that the parser uses
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            print("Missing MONGO_URI environment variable")
            return
        
        client = AsyncIOMotorClient(mongo_uri)
        database = client.emerald_killfeed  # This is what the parser uses
        collection = database.guild_configs
        
        # Find the guild configuration
        guild_doc = await collection.find_one({'guild_id': 1219706687980568769})
        
        if guild_doc:
            print("Found guild configuration in emerald_killfeed database")
            servers = guild_doc.get('servers', [])
            
            updated = False
            for i, server in enumerate(servers):
                print(f"\nServer {i}: {server.get('server_name', 'Unknown')}")
                print(f"  Current log_path: {server.get('log_path', 'None')}")
                print(f"  Enabled: {server.get('enabled', False)}")
                
                if 'log_path' in server:
                    del server['log_path']
                    print(f"  Removed hardcoded log_path")
                    updated = True
                
                if 'base_path' in server:
                    del server['base_path']
                    print(f"  Removed hardcoded base_path")
                    updated = True
            
            if updated:
                # Update the document
                result = await collection.update_one(
                    {'guild_id': 1219706687980568769},
                    {'$set': {'servers': servers}}
                )
                
                if result.modified_count > 0:
                    print("\n✅ Successfully updated emerald_killfeed database")
                    
                    # Verify the update
                    updated_doc = await collection.find_one({'guild_id': 1219706687980568769})
                    if updated_doc:
                        updated_servers = updated_doc.get('servers', [])
                        print("\nVerified configuration:")
                        for server in updated_servers:
                            print(f"  Server: {server.get('server_name')}")
                            print(f"  Host: {server.get('host')}:{server.get('port')}")
                            print(f"  Log path: {'Dynamic pattern' if not server.get('log_path') else server.get('log_path')}")
                            print(f"  Server ID: {server.get('server_id')}")
                            print(f"  Enabled: {server.get('enabled')}")
                else:
                    print("\n❌ Failed to update database")
            else:
                print("\n✅ No hardcoded paths found - configuration is already correct")
        else:
            print("No guild configuration found in emerald_killfeed database")
        
        client.close()
        
    except Exception as e:
        print(f"Failed to fix emerald_killfeed database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_emerald_killfeed_db())