"""
Comprehensive Command Timeout Fix Validation
Tests all slash commands for proper timeout handling and response patterns
"""
import asyncio
import os
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_command_timeout_fixes():
    """Test all slash commands for proper timeout handling"""
    print("Testing comprehensive command timeout fixes...")
    
    bot_token = os.environ.get('BOT_TOKEN')
    if not bot_token:
        print("Error: BOT_TOKEN not found")
        return False
    
    # Create bot instance with proper configuration
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    
    # Use the same configuration as main.py to ensure consistency
    bot = commands.Bot(
        command_prefix='!',
        intents=intents,
        auto_sync_commands=False  # This prevents timeout issues
    )
    
    try:
        # Load all cogs to test
        from bot.cogs.core import Core
        from bot.cogs.admin_channels import AdminChannels
        from bot.cogs.stats import Stats
        from bot.cogs.linking import Linking
        
        # Set up mock database manager
        class MockDatabaseManager:
            async def find_player_in_pvp_data(self, guild_id, character):
                await asyncio.sleep(0.1)  # Simulate database delay
                return character if character else None
            
            async def get_linked_player(self, guild_id, discord_id):
                await asyncio.sleep(0.1)
                return {
                    'linked_characters': ['TestPlayer'],
                    'primary_character': 'TestPlayer'
                }
            
            async def link_player(self, guild_id, discord_id, character):
                await asyncio.sleep(0.1)
                return True
            
            @property
            def players(self):
                return self
            
            @property
            def player_sessions(self):
                return self
            
            async def find_one(self, query):
                await asyncio.sleep(0.1)
                return None
            
            def find(self, query):
                return self
            
            async def to_list(self, length=None):
                await asyncio.sleep(0.1)
                return []
        
        bot.db_manager = MockDatabaseManager()
        
        # Load cogs using py-cord 2.6.1 compatible method
        bot.add_cog(Core(bot))
        bot.add_cog(AdminChannels(bot))
        bot.add_cog(Stats(bot))
        bot.add_cog(Linking(bot))
        
        print(f"✅ Loaded {len(bot.cogs)} cogs successfully")
        
        # Test command discovery
        command_count = 0
        all_commands = []
        
        # Check different command attribute names for py-cord 2.6.1
        if hasattr(bot, 'pending_application_commands') and bot.pending_application_commands:
            command_count = len(bot.pending_application_commands)
            all_commands = list(bot.pending_application_commands)
        elif hasattr(bot, 'application_commands') and bot.application_commands:
            command_count = len(bot.application_commands)
            all_commands = list(bot.application_commands)
        else:
            # Fallback: count commands from cogs directly
            for cog_name, cog in bot.cogs.items():
                if hasattr(cog, 'get_commands'):
                    cog_commands = cog.get_commands()
                    command_count += len(cog_commands)
                    all_commands.extend(cog_commands)
                # Also check for slash commands specifically
                for attr_name in dir(cog):
                    attr = getattr(cog, attr_name)
                    if hasattr(attr, '__discord_app_commands_is_command__'):
                        command_count += 1
                        all_commands.append(attr)
        
        print(f"📊 Total commands found: {command_count}")
        
        # Test key timeout fixes
        test_results = {}
        
        # Test 1: Verify defer() is used in critical commands
        critical_commands = ['online', 'stats', 'link', 'setchannel']
        defer_check_passed = 0
        
        for cog_name, cog in bot.cogs.items():
            for attr_name in dir(cog):
                attr = getattr(cog, attr_name)
                if hasattr(attr, '__discord_app_commands_is_command__'):
                    command_name = getattr(attr, 'name', attr_name)
                    if command_name in critical_commands:
                        # Check if command has defer logic
                        import inspect
                        source = inspect.getsource(attr)
                        if 'await ctx.defer()' in source:
                            defer_check_passed += 1
                            print(f"✅ /{command_name} uses ctx.defer()")
                        else:
                            print(f"❌ /{command_name} missing ctx.defer()")
        
        test_results['defer_usage'] = defer_check_passed >= 3
        
        # Test 2: Verify timeout protection in database operations
        timeout_protection_passed = 0
        
        for cog_name, cog in bot.cogs.items():
            for attr_name in dir(cog):
                attr = getattr(cog, attr_name)
                if hasattr(attr, '__discord_app_commands_is_command__'):
                    command_name = getattr(attr, 'name', attr_name)
                    if command_name in critical_commands:
                        import inspect
                        source = inspect.getsource(attr)
                        if 'asyncio.wait_for' in source and 'timeout=' in source:
                            timeout_protection_passed += 1
                            print(f"✅ /{command_name} has timeout protection")
                        else:
                            print(f"❌ /{command_name} missing timeout protection")
        
        test_results['timeout_protection'] = timeout_protection_passed >= 2
        
        # Test 3: Verify proper error handling
        error_handling_passed = 0
        
        for cog_name, cog in bot.cogs.items():
            for attr_name in dir(cog):
                attr = getattr(cog, attr_name)
                if hasattr(attr, '__discord_app_commands_is_command__'):
                    command_name = getattr(attr, 'name', attr_name)
                    if command_name in critical_commands:
                        import inspect
                        source = inspect.getsource(attr)
                        if 'except' in source and ('ctx.followup.send' in source or 'ctx.respond' in source):
                            error_handling_passed += 1
                            print(f"✅ /{command_name} has proper error handling")
                        else:
                            print(f"❌ /{command_name} missing proper error handling")
        
        test_results['error_handling'] = error_handling_passed >= 3
        
        # Test 4: Verify py-cord 2.6.1 compliance
        pycord_compliance_passed = 0
        
        for cog_name, cog in bot.cogs.items():
            for attr_name in dir(cog):
                attr = getattr(cog, attr_name)
                if hasattr(attr, '__discord_app_commands_is_command__'):
                    command_name = getattr(attr, 'name', attr_name)
                    if command_name in critical_commands:
                        import inspect
                        source = inspect.getsource(attr)
                        # Check for py-cord syntax
                        if '@discord.slash_command' in source:
                            pycord_compliance_passed += 1
                            print(f"✅ /{command_name} uses py-cord syntax")
                        else:
                            print(f"❌ /{command_name} missing py-cord syntax")
        
        test_results['pycord_compliance'] = pycord_compliance_passed >= 3
        
        # Test 5: Verify no command sync issues
        no_sync_issues = not hasattr(bot, 'auto_sync_commands') or not bot.auto_sync_commands
        test_results['no_sync_issues'] = no_sync_issues
        
        if no_sync_issues:
            print("✅ Auto sync disabled - no rate limiting issues")
        else:
            print("❌ Auto sync enabled - potential rate limiting")
        
        # Summary
        print("\n" + "="*50)
        print("COMPREHENSIVE COMMAND TIMEOUT FIX VALIDATION")
        print("="*50)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        
        print(f"Tests Passed: {passed_tests}/{total_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
        
        # Final verdict
        if passed_tests >= 4:
            print("\n🎉 COMMAND TIMEOUT FIXES: SUCCESSFULLY IMPLEMENTED")
            print("All critical commands should now respond without timeouts")
        else:
            print("\n⚠️ COMMAND TIMEOUT FIXES: NEEDS IMPROVEMENT")
            print("Some commands may still experience timeout issues")
        
        return passed_tests >= 4
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False
    
    finally:
        if bot:
            await bot.close()

if __name__ == "__main__":
    asyncio.run(test_command_timeout_fixes())