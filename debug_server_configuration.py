"""
Debug Server Configuration - Find why parsers aren't detecting configured servers
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_server_configuration():
    """Debug server configuration detection"""
    
    print("🔍 DEBUGGING SERVER CONFIGURATION DETECTION")
    print("=" * 60)
    
    try:
        # Import bot components
        from main import EmeraldKillfeedBot
        import os
        
        # Create minimal bot instance for database access
        bot = EmeraldKillfeedBot()
        
        # Initialize database connection
        await bot.setup_database()
        
        print("✅ Database connection established")
        
        # Check guild_configs collection
        database = bot.db_manager.get_database()
        guild_configs = database.guild_configs
        
        # Count total documents
        total_docs = await guild_configs.count_documents({})
        print(f"📊 Total guild_configs documents: {total_docs}")
        
        # Count documents with servers field
        docs_with_servers = await guild_configs.count_documents({'servers': {'$exists': True}})
        print(f"📊 Documents with 'servers' field: {docs_with_servers}")
        
        # Count documents with non-empty servers
        docs_with_nonempty_servers = await guild_configs.count_documents({
            'servers': {'$exists': True, '$not': {'$size': 0}}
        })
        print(f"📊 Documents with non-empty servers: {docs_with_nonempty_servers}")
        
        # Sample some documents to see structure
        print("\n📋 SAMPLE DOCUMENTS:")
        cursor = guild_configs.find({}).limit(3)
        async for doc in cursor:
            guild_id = doc.get('guild_id', 'unknown')
            servers = doc.get('servers', [])
            print(f"• Guild {guild_id}: {len(servers)} servers")
            if servers:
                for i, server in enumerate(servers[:2]):  # Show first 2 servers
                    server_name = server.get('server_name', 'unnamed')
                    print(f"  - Server {i+1}: {server_name}")
        
        # Check for documents that match the parser query
        print("\n🔍 PARSER QUERY RESULTS:")
        parser_query = {'servers': {'$exists': True, '$not': {'$size': 0}}}
        parser_docs = await guild_configs.find(parser_query).to_list(length=None)
        
        print(f"📊 Documents matching parser query: {len(parser_docs)}")
        
        if parser_docs:
            print("✅ Found configured servers:")
            for doc in parser_docs:
                guild_id = doc.get('guild_id')
                servers = doc.get('servers', [])
                print(f"• Guild {guild_id}: {len(servers)} servers configured")
                
                for server in servers[:2]:  # Show details of first 2 servers
                    server_name = server.get('server_name', 'unnamed')
                    host = server.get('host', 'no-host')
                    enabled = server.get('enabled', False)
                    print(f"  - {server_name} ({host}) - Enabled: {enabled}")
        else:
            print("❌ No servers found matching parser query")
            
            # Try to find any servers at all
            all_docs = await guild_configs.find({}).to_list(length=None)
            print(f"\n🔍 Analyzing all {len(all_docs)} documents:")
            
            for doc in all_docs:
                guild_id = doc.get('guild_id', 'unknown')
                servers = doc.get('servers')
                
                if servers is None:
                    print(f"• Guild {guild_id}: servers field missing")
                elif isinstance(servers, list):
                    if len(servers) == 0:
                        print(f"• Guild {guild_id}: empty servers array")
                    else:
                        print(f"• Guild {guild_id}: {len(servers)} servers present")
                else:
                    print(f"• Guild {guild_id}: servers field is {type(servers)} (not list)")
        
        # Test the exact method used by the parser
        print("\n🧪 TESTING PARSER METHOD:")
        
        # Simulate the parser's guild config retrieval
        from bot.parsers.scalable_unified_parser import ScalableUnifiedParser
        parser = ScalableUnifiedParser(bot, {})
        
        # Temporarily enable database access for testing
        original_method = parser._get_all_guild_configs
        
        async def test_guild_configs():
            """Test version of guild config retrieval"""
            guild_configs = {}
            
            try:
                database = bot.db_manager.get_database()
                collection = database.guild_configs
                
                # Find all guilds with servers configured
                cursor = collection.find({
                    'servers': {'$exists': True, '$not': {'$size': 0}}
                })
                
                guild_docs = await cursor.to_list(length=None)
                print(f"🔍 Test query found {len(guild_docs)} documents")
                
                for guild_doc in guild_docs:
                    guild_id = guild_doc.get('guild_id')
                    servers = guild_doc.get('servers', [])
                    
                    if guild_id and servers:
                        for server in servers:
                            server['guild_id'] = guild_id
                        guild_configs[guild_id] = servers
                        print(f"✅ Added guild {guild_id} with {len(servers)} servers")
                
            except Exception as e:
                print(f"❌ Test query failed: {e}")
            
            return guild_configs
        
        test_configs = await test_guild_configs()
        print(f"📊 Test method result: {len(test_configs)} guilds with servers")
        
        await bot.close()
        
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_server_configuration())