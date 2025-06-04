"""
Test Live Command Execution - Verify actual command functionality
Direct testing of command execution to validate fallback mechanisms
"""

import asyncio
import logging
import os
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

async def test_live_command_execution():
    """Test live command execution to verify fallback works"""
    try:
        bot_token = os.environ.get("BOT_TOKEN")
        
        if not bot_token:
            logger.error("BOT_TOKEN not found")
            return False
            
        # Create test bot instance
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        
        bot = commands.Bot(
            command_prefix="!",
            intents=intents,
            help_command=None
        )
        
        # Track command sync attempts
        sync_attempted = False
        sync_successful = False
        rate_limited = False
        
        @bot.event
        async def on_ready():
            nonlocal sync_attempted, sync_successful, rate_limited
            
            logger.info(f"Test bot ready: {bot.user}")
            
            try:
                # Check if we can access application commands
                logger.info("Testing command tree access...")
                
                if hasattr(bot, 'tree'):
                    logger.info("✅ Command tree accessible")
                    
                    # Try to get existing commands
                    try:
                        existing_commands = await bot.tree.fetch_commands()
                        logger.info(f"Found {len(existing_commands)} existing commands")
                        
                        for cmd in existing_commands[:5]:  # Show first 5
                            logger.info(f"  - {cmd.name}: {cmd.description}")
                            
                    except discord.HTTPException as e:
                        if e.status == 429:
                            logger.warning("Rate limited when fetching commands")
                            rate_limited = True
                        else:
                            logger.error(f"HTTP error fetching commands: {e}")
                    
                    # Try minimal sync test
                    try:
                        logger.info("Testing minimal sync operation...")
                        sync_attempted = True
                        
                        # Use very short timeout
                        sync_task = asyncio.create_task(bot.tree.sync())
                        synced = await asyncio.wait_for(sync_task, timeout=5.0)
                        
                        logger.info(f"✅ Sync successful: {len(synced)} commands")
                        sync_successful = True
                        
                    except asyncio.TimeoutError:
                        logger.warning("Sync timed out (rate limited)")
                        rate_limited = True
                        sync_task.cancel()
                        
                    except discord.HTTPException as e:
                        if e.status == 429:
                            logger.warning("Sync rate limited")
                            rate_limited = True
                        else:
                            logger.error(f"Sync HTTP error: {e}")
                    
                else:
                    logger.error("❌ Command tree not accessible")
                
            except Exception as e:
                logger.error(f"Test failed: {e}")
            
            finally:
                # Report results
                logger.info("=== COMMAND SYNC TEST RESULTS ===")
                logger.info(f"Sync attempted: {sync_attempted}")
                logger.info(f"Sync successful: {sync_successful}")
                logger.info(f"Rate limited: {rate_limited}")
                
                if rate_limited and not sync_successful:
                    logger.info("✅ Rate limiting confirmed - fallback should activate")
                elif sync_successful:
                    logger.info("✅ Sync working - no fallback needed")
                else:
                    logger.warning("⚠️ Unclear state - further investigation needed")
                
                await bot.close()
        
        # Start test bot with timeout
        try:
            await asyncio.wait_for(bot.start(bot_token), timeout=30.0)
        except asyncio.TimeoutError:
            logger.info("Test completed (timeout reached)")
        
        return rate_limited and not sync_successful
        
    except Exception as e:
        logger.error(f"Live command test failed: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = asyncio.run(test_live_command_execution())
    print(f"Rate limited without successful sync: {result}")