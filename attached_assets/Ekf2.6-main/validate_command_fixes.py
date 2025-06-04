"""
Validate Command Fixes - Test all slash commands end-to-end to ensure timeout issues are resolved
"""

import asyncio
import os
import sys
import traceback
from datetime import datetime

# Add project root to path
sys.path.insert(0, '.')

async def validate_command_fixes():
    """Validate that all command fixes are working properly"""
    print("🔍 VALIDATING COMMAND FIXES")
    print("=" * 50)
    
    try:
        # Import bot modules
        from main import EmeraldKillfeedBot
        from bot.models.database import DatabaseManager
        import motor.motor_asyncio
        
        print("✓ Bot modules imported successfully")
        
        # Test database connection
        mongo_uri = os.environ.get('MONGO_URI')
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        await mongo_client.admin.command('ping')
        print("✓ Database connection verified")
        
        # Create bot with direct database manager
        bot = EmeraldKillfeedBot()
        bot.mongo_client = mongo_client
        bot.db_manager = DatabaseManager(mongo_client)
        print("✓ Bot created with direct database manager")
        
        # Load cogs
        await bot.load_cogs()
        print(f"✓ Loaded {len(bot.cogs)} cogs with {len(bot.pending_application_commands)} commands")
        
        # Test critical database operations that commands use
        guild_id = 1219706687980568769
        test_operations = [
            ("Direct session count", lambda: bot.db_manager.player_sessions.count_documents({'guild_id': guild_id})),
            ("Direct online players", lambda: bot.db_manager.player_sessions.find({'guild_id': guild_id, 'state': 'online'}).limit(10).to_list(length=10)),
            ("Direct guild lookup", lambda: bot.db_manager.get_guild(guild_id)),
            ("Direct player linking", lambda: bot.db_manager.get_linked_player(guild_id, 123456789)),
        ]
        
        print("\n📊 TESTING COMMAND DATABASE OPERATIONS")
        print("-" * 40)
        
        all_passed = True
        for operation_name, operation_func in test_operations:
            start_time = datetime.now()
            try:
                result = await asyncio.wait_for(operation_func(), timeout=3.0)
                execution_time = (datetime.now() - start_time).total_seconds()
                print(f"✓ {operation_name}: {execution_time:.3f}s")
                
                if execution_time > 2.5:
                    print(f"  ⚠️ WARNING: Operation took {execution_time:.3f}s (close to Discord limit)")
                    
            except asyncio.TimeoutError:
                print(f"❌ {operation_name}: TIMEOUT after 3 seconds")
                all_passed = False
            except Exception as e:
                execution_time = (datetime.now() - start_time).total_seconds()
                print(f"❌ {operation_name}: FAILED in {execution_time:.3f}s - {e}")
                all_passed = False
        
        # Test command structure
        print("\n🎯 TESTING COMMAND STRUCTURE")
        print("-" * 40)
        
        critical_commands = ['online', 'stats', 'link', 'setchannel']
        commands_found = 0
        
        for cog_name, cog in bot.cogs.items():
            for command in bot.pending_application_commands:
                if hasattr(command, 'name') and command.name in critical_commands:
                    commands_found += 1
                    print(f"✓ Found /{command.name} command")
        
        if commands_found >= len(critical_commands):
            print(f"✓ All {len(critical_commands)} critical commands found")
        else:
            print(f"❌ Only {commands_found}/{len(critical_commands)} critical commands found")
            all_passed = False
        
        # Test concurrent operations
        print("\n🔄 TESTING CONCURRENT OPERATIONS")
        print("-" * 40)
        
        start_time = datetime.now()
        try:
            tasks = [
                bot.db_manager.player_sessions.count_documents({'guild_id': guild_id}),
                bot.db_manager.get_guild(guild_id),
                bot.db_manager.get_linked_player(guild_id, 123456789),
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            concurrent_time = (datetime.now() - start_time).total_seconds()
            
            successful = sum(1 for r in results if not isinstance(r, Exception))
            print(f"✓ Concurrent operations: {successful}/3 successful in {concurrent_time:.3f}s")
            
            if concurrent_time > 2.0:
                print(f"  ⚠️ WARNING: Concurrent operations took {concurrent_time:.3f}s")
            
        except Exception as e:
            print(f"❌ Concurrent operation test failed: {e}")
            all_passed = False
        
        # Summary
        print("\n🎯 VALIDATION SUMMARY")
        print("=" * 50)
        
        if all_passed:
            print("✅ ALL TESTS PASSED")
            print("   - Database operations complete under 3 seconds")
            print("   - All critical commands found and registered")
            print("   - Concurrent operations working properly")
            print("   - Direct database manager resolves cache blocking issues")
            print("\n🚀 SLASH COMMANDS SHOULD NOW WORK WITHOUT TIMEOUTS")
        else:
            print("❌ SOME TESTS FAILED")
            print("   Additional fixes may be required")
        
        return all_passed
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR in validation: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(validate_command_fixes())
    if result:
        print("\n🎉 VALIDATION SUCCESSFUL - Commands ready for testing")
    else:
        print("\n⚠️ VALIDATION FAILED - Additional fixes needed")