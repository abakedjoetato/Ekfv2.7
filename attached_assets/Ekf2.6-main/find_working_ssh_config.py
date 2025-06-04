"""
Find Working SSH Configuration - Check all database collections for SSH credentials
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def find_working_ssh_config():
    """Find where the working SSH credentials are stored"""
    try:
        # Initialize database connection
        mongo_uri = os.getenv('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db = client.emerald_killfeed
        
        print("Searching all collections for SSH credentials...")
        
        # List all collections
        collections = await db.list_collection_names()
        print(f"Database collections: {collections}")
        
        # Check each collection for documents with SSH credentials
        for collection_name in collections:
            collection = db[collection_name]
            
            # Find documents with ssh_host field
            docs_with_ssh = await collection.find({"ssh_host": {"$exists": True}}).to_list(length=None)
            
            if docs_with_ssh:
                print(f"\n=== Collection: {collection_name} ===")
                for doc in docs_with_ssh:
                    print(f"Document ID: {doc.get('_id')}")
                    print(f"  Guild ID: {doc.get('guild_id')}")
                    print(f"  Server Name: {doc.get('server_name', 'Unknown')}")
                    print(f"  Server ID: {doc.get('server_id')}")
                    print(f"  SSH Host: {doc.get('ssh_host')}")
                    print(f"  SSH Username: {doc.get('ssh_username')}")
                    print(f"  SSH Port: {doc.get('ssh_port')}")
                    print(f"  SSH Password: {'SET' if doc.get('ssh_password') else 'NOT SET'}")
                    print(f"  Log Path: {doc.get('log_path', 'NOT SET')}")
                    print(f"  Killfeed Path: {doc.get('killfeed_path', 'NOT SET')}")
                    print("")
            
            # Also check for nested servers with SSH credentials
            docs_with_nested_ssh = await collection.find({"servers.ssh_host": {"$exists": True}}).to_list(length=None)
            
            if docs_with_nested_ssh:
                print(f"\n=== Collection: {collection_name} (nested servers) ===")
                for doc in docs_with_nested_ssh:
                    print(f"Document ID: {doc.get('_id')}")
                    print(f"  Guild ID: {doc.get('guild_id')}")
                    
                    servers = doc.get('servers', [])
                    for server in servers:
                        if server.get('ssh_host'):
                            print(f"  Server: {server.get('server_name', 'Unknown')}")
                            print(f"    Server ID: {server.get('server_id')}")
                            print(f"    SSH Host: {server.get('ssh_host')}")
                            print(f"    SSH Username: {server.get('ssh_username')}")
                            print(f"    SSH Port: {server.get('ssh_port')}")
                            print(f"    SSH Password: {'SET' if server.get('ssh_password') else 'NOT SET'}")
                            print(f"    Log Path: {server.get('log_path', 'NOT SET')}")
                            print(f"    Killfeed Path: {server.get('killfeed_path', 'NOT SET')}")
                            print("")
        
        print("\nSearching complete.")
        
    except Exception as e:
        print(f"Error finding SSH config: {e}")

if __name__ == "__main__":
    asyncio.run(find_working_ssh_config())