"""
Check Server SSH Credentials - Examine what SSH credentials are stored in database
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient

async def check_server_ssh_credentials():
    """Check the SSH credentials stored in database for servers"""
    try:
        # Initialize database connection
        mongo_uri = os.getenv('MONGO_URI')
        client = AsyncIOMotorClient(mongo_uri)
        db = client.emerald_killfeed
        servers_collection = db.servers
        
        print("Checking server configurations and SSH credentials...")
        
        # Get all servers
        servers = await servers_collection.find({}).to_list(length=None)
        print(f"Found {len(servers)} servers in database")
        
        for server in servers:
            print(f"\nServer: {server.get('server_name', 'Unknown')}")
            print(f"  Guild ID: {server.get('guild_id')}")
            print(f"  Server ID: {server.get('server_id')}")
            print(f"  SSH Host: {server.get('ssh_host', 'NOT SET')}")
            print(f"  SSH Username: {server.get('ssh_username', 'NOT SET')}")
            print(f"  SSH Port: {server.get('ssh_port', 'NOT SET')}")
            print(f"  SSH Password: {'SET' if server.get('ssh_password') else 'NOT SET'}")
            print(f"  Log Path: {server.get('log_path', 'NOT SET')}")
            
        # Check if any servers have missing SSH credentials
        servers_missing_ssh = []
        for server in servers:
            if not all([
                server.get('ssh_host'),
                server.get('ssh_username'), 
                server.get('ssh_password')
            ]):
                servers_missing_ssh.append(server.get('server_name', 'Unknown'))
        
        if servers_missing_ssh:
            print(f"\n⚠️  Servers missing SSH credentials: {', '.join(servers_missing_ssh)}")
        else:
            print("\n✅ All servers have SSH credentials configured")
            
    except Exception as e:
        print(f"Error checking server SSH credentials: {e}")

if __name__ == "__main__":
    asyncio.run(check_server_ssh_credentials())