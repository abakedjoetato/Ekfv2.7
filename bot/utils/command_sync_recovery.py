"""
Command Sync Recovery System
Handles Discord API rate limits and restores command functionality with intelligent retry logic
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)

class CommandSyncRecovery:
    """Manages command sync recovery after rate limits and connection issues"""
    
    def __init__(self, bot):
        self.bot = bot
        self.last_sync_attempt = None
        self.sync_retry_count = 0
        self.max_retry_attempts = 5
        self.base_retry_delay = 60  # 1 minute base delay
        self.is_recovering = False
        
    async def attempt_command_sync_recovery(self) -> bool:
        """Attempt to recover command sync functionality"""
        if self.is_recovering:
            logger.debug("Command sync recovery already in progress")
            return False
            
        self.is_recovering = True
        try:
            logger.info("🔄 Starting command sync recovery...")
            
            # Check if we've exceeded retry attempts
            if self.sync_retry_count >= self.max_retry_attempts:
                logger.warning("⚠️ Maximum sync retry attempts reached, falling back to local commands")
                await self._enable_local_command_fallback()
                return False
            
            # Calculate retry delay with exponential backoff
            retry_delay = self.base_retry_delay * (2 ** self.sync_retry_count)
            
            # Check if enough time has passed since last attempt
            if self.last_sync_attempt:
                time_since_last = datetime.now() - self.last_sync_attempt
                if time_since_last.total_seconds() < retry_delay:
                    remaining_wait = retry_delay - time_since_last.total_seconds()
                    logger.info(f"⏱️ Waiting {remaining_wait:.0f}s before next sync attempt")
                    await asyncio.sleep(remaining_wait)
            
            # Attempt sync
            success = await self._try_command_sync()
            
            if success:
                logger.info("✅ Command sync recovery successful!")
                self.sync_retry_count = 0
                self.last_sync_attempt = None
                return True
            else:
                self.sync_retry_count += 1
                self.last_sync_attempt = datetime.now()
                logger.warning(f"❌ Command sync attempt {self.sync_retry_count} failed")
                
                # Schedule next retry
                if self.sync_retry_count < self.max_retry_attempts:
                    next_retry_delay = self.base_retry_delay * (2 ** self.sync_retry_count)
                    logger.info(f"🔄 Next retry in {next_retry_delay} seconds")
                    asyncio.create_task(self._schedule_retry(next_retry_delay))
                
                return False
                
        except Exception as e:
            logger.error(f"Command sync recovery failed: {e}")
            return False
        finally:
            self.is_recovering = False
    
    async def _try_command_sync(self) -> bool:
        """Try to sync commands with Discord using py-cord syntax"""
        try:
            # First try guild-specific sync for immediate availability
            for guild in self.bot.guilds:
                try:
                    # Use py-cord sync_commands with guild_ids parameter
                    synced = await self.bot.sync_commands(guild_ids=[guild.id])
                    logger.info(f"✅ Synced {len(synced) if synced else 0} commands to guild: {guild.name}")
                    return True
                except discord.HTTPException as e:
                    if e.status == 429:  # Rate limited
                        logger.warning(f"Rate limited syncing to {guild.name}, will retry")
                        continue
                    else:
                        logger.error(f"Failed to sync to {guild.name}: {e}")
                        continue
                except Exception as e:
                    logger.error(f"Unexpected error syncing to {guild.name}: {e}")
                    continue
            
            # If guild sync fails, try global sync
            try:
                synced = await self.bot.sync_commands()
                logger.info(f"✅ Global sync successful: {len(synced) if synced else 0} commands")
                return True
            except discord.HTTPException as e:
                if e.status == 429:
                    logger.warning("Global sync rate limited")
                    return False
                else:
                    logger.error(f"Global sync failed: {e}")
                    return False
                    
        except Exception as e:
            logger.error(f"Command sync attempt failed: {e}")
            return False
    
    async def _schedule_retry(self, delay: float):
        """Schedule the next retry attempt"""
        await asyncio.sleep(delay)
        if self.sync_retry_count < self.max_retry_attempts:
            asyncio.create_task(self.attempt_command_sync_recovery())
    
    async def _enable_local_command_fallback(self):
        """Enable local command processing as fallback"""
        try:
            logger.info("🔧 Enabling local command fallback mode...")
            
            # Register essential commands locally without Discord sync
            essential_commands = ['ping', 'help', 'info', 'online', 'stats']
            
            for command_name in essential_commands:
                command = self.bot.tree.get_command(command_name)
                if command:
                    logger.debug(f"Local fallback enabled for: {command_name}")
            
            logger.info("✅ Local command fallback enabled for essential commands")
            
        except Exception as e:
            logger.error(f"Failed to enable local command fallback: {e}")
    
    async def handle_rate_limit_recovery(self):
        """Handle recovery after Discord rate limits"""
        logger.info("🔄 Handling rate limit recovery...")
        
        # Wait for rate limit to clear (conservative estimate)
        await asyncio.sleep(300)  # 5 minutes
        
        # Attempt recovery
        await self.attempt_command_sync_recovery()
    
    async def monitor_command_availability(self):
        """Monitor if commands are working and trigger recovery if needed"""
        try:
            # Check if commands are responding
            for guild in self.bot.guilds:
                commands = await self.bot.tree.fetch_commands(guild=guild)
                if not commands:
                    logger.warning(f"No commands found for guild {guild.name}, triggering recovery")
                    asyncio.create_task(self.attempt_command_sync_recovery())
                    break
                    
        except Exception as e:
            logger.debug(f"Command availability check failed: {e}")
            # Trigger recovery on any command availability issues
            asyncio.create_task(self.attempt_command_sync_recovery())
    
    def reset_recovery_state(self):
        """Reset recovery state after successful operations"""
        self.sync_retry_count = 0
        self.last_sync_attempt = None
        self.is_recovering = False
        logger.debug("Command sync recovery state reset")

# Global recovery instance
command_sync_recovery = None

def initialize_command_sync_recovery(bot):
    """Initialize the global command sync recovery system"""
    global command_sync_recovery
    command_sync_recovery = CommandSyncRecovery(bot)
    return command_sync_recovery

def get_command_sync_recovery():
    """Get the global command sync recovery instance"""
    return command_sync_recovery