"""
Fix Server Path Configuration - Remove hardcoded log_path to use dynamic pattern
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def fix_server_path():
    """Remove hardcoded log_path from server configuration to use dynamic pattern"""
    try:
        # Connect to MongoDB using the same database name as the bot
        mongo_uri = os.getenv('MONGO_URI')
        if not mongo_uri:
            print("Missing MONGO_URI environment variable")
            return
        
        client = AsyncIOMotorClient(mongo_uri)
        
        # Check both possible database names
        databases_to_check = ['EmeraldDB', 'emerald_killfeed']
        
        for db_name in databases_to_check:
            print(f"\nChecking database: {db_name}")
            db = client[db_name]
            
            # Check guilds collection
            guilds_collection = db.guilds
            guild_doc = await guilds_collection.find_one({'guild_id': 1219706687980568769})
            
            if guild_doc:
                print(f"Found guild configuration in {db_name}")
                servers = guild_doc.get('servers', [])
                
                for i, server in enumerate(servers):
                    print(f"\nServer {i}: {server.get('name', 'Unknown')}")
                    print(f"  Current log_path: {server.get('log_path', 'None')}")
                    
                    if 'log_path' in server:
                        del server['log_path']
                        print(f"  Removed hardcoded log_path")
                    
                    if 'base_path' in server:
                        del server['base_path']
                        print(f"  Removed hardcoded base_path")
                
                # Update the configuration
                result = await guilds_collection.update_one(
                    {'guild_id': 1219706687980568769},
                    {'$set': {'servers': servers}}
                )
                
                if result.modified_count > 0:
                    print(f"\n✅ Updated server configuration in {db_name}")
                else:
                    print(f"\n❌ No changes made in {db_name}")
                
                # Verify the update
                updated_doc = await guilds_collection.find_one({'guild_id': 1219706687980568769})
                if updated_doc:
                    updated_servers = updated_doc.get('servers', [])
                    print(f"\nVerified configuration:")
                    for server in updated_servers:
                        print(f"  Server: {server.get('name')}")
                        print(f"  Host: {server.get('host')}:{server.get('port')}")
                        print(f"  Log path: {'Dynamic pattern' if not server.get('log_path') else server.get('log_path')}")
                        print(f"  Server ID: {server.get('server_id')}")
                
                break
            
            # Check guild_configs collection
            guild_configs_collection = db.guild_configs
            guild_config_doc = await guild_configs_collection.find_one({'guild_id': 1219706687980568769})
            
            if guild_config_doc:
                print(f"Found guild_configs in {db_name}")
                servers = guild_config_doc.get('servers', [])
                
                for i, server in enumerate(servers):
                    print(f"\nServer {i}: {server.get('server_name', 'Unknown')}")
                    print(f"  Current log_path: {server.get('log_path', 'None')}")
                    
                    if 'log_path' in server:
                        del server['log_path']
                        print(f"  Removed hardcoded log_path")
                    
                    if 'base_path' in server:
                        del server['base_path']
                        print(f"  Removed hardcoded base_path")
                
                # Update the configuration
                result = await guild_configs_collection.update_one(
                    {'guild_id': 1219706687980568769},
                    {'$set': {'servers': servers}}
                )
                
                if result.modified_count > 0:
                    print(f"\n✅ Updated guild_configs in {db_name}")
                else:
                    print(f"\n❌ No changes made in guild_configs in {db_name}")
                
                break
        
        client.close()
        
    except Exception as e:
        print(f"Failed to fix server configuration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(fix_server_path())