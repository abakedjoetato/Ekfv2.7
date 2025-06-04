"""
Check MongoDB Structure - Direct database inspection
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def check_mongodb_structure():
    """Check MongoDB database structure"""
    
    print("Checking MongoDB database structure...")
    
    try:
        # Get MongoDB connection string
        mongo_uri = os.environ.get('MONGO_URI')
        if not mongo_uri:
            print("ERROR: MONGO_URI environment variable not found")
            return
        
        # Connect to MongoDB
        client = AsyncIOMotorClient(mongo_uri)
        database = client.emerald_killfeed
        
        # List all collections
        collections = await database.list_collection_names()
        print(f"Collections found: {collections}")
        
        # Check guild_configs collection specifically
        if 'guild_configs' in collections:
            guild_configs = database.guild_configs
            
            # Count documents
            total_docs = await guild_configs.count_documents({})
            print(f"Total guild_configs documents: {total_docs}")
            
            # Check for servers field
            docs_with_servers = await guild_configs.count_documents({'servers': {'$exists': True}})
            print(f"Documents with servers field: {docs_with_servers}")
            
            # Check for non-empty servers
            docs_with_nonempty_servers = await guild_configs.count_documents({
                'servers': {'$exists': True, '$not': {'$size': 0}}
            })
            print(f"Documents with non-empty servers: {docs_with_nonempty_servers}")
            
            # Sample documents
            print("\nSample documents:")
            cursor = guild_configs.find({}).limit(3)
            count = 0
            async for doc in cursor:
                count += 1
                guild_id = doc.get('guild_id', 'unknown')
                servers = doc.get('servers', [])
                print(f"Guild {guild_id}: {len(servers)} servers")
                
                # Show server details if any
                for i, server in enumerate(servers[:2]):
                    server_name = server.get('server_name', 'unnamed')
                    host = server.get('host', 'no-host')
                    enabled = server.get('enabled', False)
                    print(f"  Server {i+1}: {server_name} ({host}) - Enabled: {enabled}")
            
            if count == 0:
                print("No documents found in guild_configs")
        else:
            print("guild_configs collection not found")
        
        # Check if we need to create sample configuration
        if total_docs == 0:
            print("\nDatabase appears empty. Need to configure servers.")
            print("This explains why parsers find 0 configured servers.")
            
            # Show what a proper configuration would look like
            print("\nExample server configuration needed:")
            example_config = {
                'guild_id': 1219706687980568769,  # Emerald Servers guild
                'servers': [
                    {
                        'server_name': 'Example Server',
                        'host': 'server.example.com',
                        'port': 22,
                        'username': 'username',
                        'password': 'password',
                        'enabled': True,
                        'killfeed_path': '/path/to/killfeed',
                        'log_path': '/path/to/logs'
                    }
                ]
            }
            print(f"Configuration structure: {example_config}")
        
        await client.close()
        
    except Exception as e:
        print(f"Failed to check MongoDB: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_mongodb_structure())