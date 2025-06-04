"""
Comprehensive Command Diagnosis - End-to-End Slash Command Execution Trace
Identifies blocking issues in the command execution chain
"""

import asyncio
import os
import logging
import sys
import traceback
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

async def comprehensive_command_diagnosis():
    """Execute comprehensive end-to-end command diagnosis"""
    print("🔬 COMPREHENSIVE COMMAND DIAGNOSIS")
    print("=" * 60)
    
    try:
        # Import bot modules
        from main import EmeraldKillfeedBot
        from bot.models.database import DatabaseManager
        from bot.utils.unified_cache import initialize_cache
        from bot.utils.cache_integration import create_cached_database_manager
        import motor.motor_asyncio
        
        print("✓ Bot modules imported successfully")
        
        # Test 1: Cache System Diagnosis
        print("\n📊 PHASE 1: CACHE SYSTEM DIAGNOSIS")
        print("-" * 40)
        
        try:
            await initialize_cache()
            print("✓ Cache system initialized")
        except Exception as e:
            print(f"❌ Cache initialization failed: {e}")
            traceback.print_exc()
        
        # Test 2: Database Connection Analysis
        print("\n🗄️ PHASE 2: DATABASE CONNECTION ANALYSIS")
        print("-" * 40)
        
        mongo_uri = os.environ.get('MONGO_URI')
        if not mongo_uri:
            print("❌ MONGO_URI environment variable not found")
            return
        
        # Test direct MongoDB connection
        try:
            mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
            await mongo_client.admin.command('ping')
            print("✓ Direct MongoDB connection successful")
        except Exception as e:
            print(f"❌ Direct MongoDB connection failed: {e}")
            return
        
        # Test base database manager
        try:
            base_db_manager = DatabaseManager(mongo_client)
            print("✓ Base database manager created")
        except Exception as e:
            print(f"❌ Base database manager creation failed: {e}")
            traceback.print_exc()
            return
        
        # Test cached database manager
        try:
            cached_db_manager = create_cached_database_manager(base_db_manager)
            print("✓ Cached database manager created")
        except Exception as e:
            print(f"❌ Cached database manager creation failed: {e}")
            traceback.print_exc()
            return
        
        # Test 3: Database Query Performance Analysis
        print("\n⚡ PHASE 3: DATABASE QUERY PERFORMANCE ANALYSIS")
        print("-" * 40)
        
        guild_id = 1219706687980568769
        
        # Test direct database queries
        start_time = datetime.now()
        try:
            direct_count = await base_db_manager.player_sessions.count_documents({
                'guild_id': guild_id,
                'state': 'online'
            })
            direct_time = (datetime.now() - start_time).total_seconds()
            print(f"✓ Direct query: {direct_count} results in {direct_time:.3f}s")
        except Exception as e:
            print(f"❌ Direct query failed: {e}")
            traceback.print_exc()
        
        # Test cached database queries
        start_time = datetime.now()
        try:
            cached_count = await cached_db_manager.player_sessions.count_documents({
                'guild_id': guild_id,
                'state': 'online'
            })
            cached_time = (datetime.now() - start_time).total_seconds()
            print(f"✓ Cached query: {cached_count} results in {cached_time:.3f}s")
        except Exception as e:
            print(f"❌ Cached query failed: {e}")
            traceback.print_exc()
        
        # Test 4: Command Structure Analysis
        print("\n🎯 PHASE 4: COMMAND STRUCTURE ANALYSIS")
        print("-" * 40)
        
        # Simulate bot creation
        try:
            bot = EmeraldKillfeedBot()
            bot.mongo_client = mongo_client
            bot.db_manager = cached_db_manager
            print("✓ Bot instance created with cached database")
        except Exception as e:
            print(f"❌ Bot instance creation failed: {e}")
            traceback.print_exc()
            return
        
        # Load cogs to analyze command structure
        try:
            await bot.load_cogs()
            print(f"✓ Loaded {len(bot.cogs)} cogs")
        except Exception as e:
            print(f"❌ Cog loading failed: {e}")
            traceback.print_exc()
        
        # Test 5: Command Execution Simulation
        print("\n🚀 PHASE 5: COMMAND EXECUTION SIMULATION")
        print("-" * 40)
        
        # Test database operations that commands use
        operations_to_test = [
            ("get_linked_player", lambda: cached_db_manager.get_linked_player(guild_id, 123456789)),
            ("player_sessions.find", lambda: cached_db_manager.player_sessions.find({'guild_id': guild_id, 'state': 'online'}).limit(10).to_list(length=10)),
            ("get_guild", lambda: cached_db_manager.get_guild(guild_id)),
        ]
        
        for operation_name, operation_func in operations_to_test:
            start_time = datetime.now()
            try:
                result = await asyncio.wait_for(operation_func(), timeout=5.0)
                execution_time = (datetime.now() - start_time).total_seconds()
                print(f"✓ {operation_name}: completed in {execution_time:.3f}s")
            except asyncio.TimeoutError:
                print(f"❌ {operation_name}: TIMEOUT after 5 seconds")
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                print(f"❌ {operation_name}: failed in {execution_time:.3f}s - {e}")
        
        # Test 6: Cache Performance Analysis
        print("\n📈 PHASE 6: CACHE PERFORMANCE ANALYSIS")
        print("-" * 40)
        
        try:
            cache_stats = await cached_db_manager.get_cache_stats()
            print(f"✓ Cache stats: {cache_stats}")
        except Exception as e:
            print(f"❌ Cache stats failed: {e}")
        
        # Test 7: Blocking Operation Detection
        print("\n🚫 PHASE 7: BLOCKING OPERATION DETECTION")
        print("-" * 40)
        
        # Test if cache operations are blocking
        start_time = datetime.now()
        try:
            # Simulate concurrent cache access
            tasks = []
            for i in range(5):
                task = asyncio.create_task(
                    cached_db_manager.player_sessions.count_documents({'guild_id': guild_id})
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            concurrent_time = (datetime.now() - start_time).total_seconds()
            
            successful = sum(1 for r in results if not isinstance(r, Exception))
            print(f"✓ Concurrent operations: {successful}/5 successful in {concurrent_time:.3f}s")
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"  Task {i+1}: Failed - {result}")
                    
        except Exception as e:
            print(f"❌ Concurrent operation test failed: {e}")
        
        print("\n🎯 DIAGNOSIS SUMMARY")
        print("=" * 60)
        
        # Final assessment
        if cached_time > 2.0:
            print("❌ CRITICAL: Cached queries are too slow for Discord's 3s timeout")
            print("   RECOMMENDATION: Bypass cache for slash commands")
        
        if 'TimeoutError' in str(e) if 'e' in locals() else False:
            print("❌ CRITICAL: Database operations are timing out")
            print("   RECOMMENDATION: Implement connection pooling")
        
        print("✅ Diagnosis completed")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR in diagnosis: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(comprehensive_command_diagnosis())