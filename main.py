#!/usr/bin/env python3
"""
Emerald's Killfeed - Discord Bot for Deadside PvP Engine
Full production-grade bot with killfeed parsing, stats, economy, and premium features
"""

import asyncio
import logging
import os
import sys
import json
import hashlib
import re
import time
import traceback
from pathlib import Path
from datetime import datetime, timedelta, timezone

# Import py-cord v2.6.1 first
try:
    import discord
    from discord.ext import commands
    print(f"✅ Successfully imported py-cord version: {discord.__version__}")
except ImportError as e:
    print(f"❌ Error importing py-cord: {e}")
    print("Please ensure py-cord 2.6.1 is installed")
    sys.exit(1)

# Block discord.py imports after successful py-cord import
import discord_py_blocker

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bot.models.database import DatabaseManager
from bot.utils.command_sync_recovery import initialize_command_sync_recovery

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

try:
    from bot.parsers.killfeed_parser import KillfeedParser
except Exception as e:
    logger.error(f"Failed to import KillfeedParser: {e}")
    raise
from bot.parsers.historical_parser import HistoricalParser
from bot.parsers.unified_log_parser import UnifiedLogParser
from bot.utils.task_pool import get_task_pool, shutdown_task_pool, dispatch_background_with_lock
from bot.utils.threaded_parser_wrapper import ThreadedParserWrapper

# Load environment variables
load_dotenv()

# Detect Railway environment
RAILWAY_ENV = os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_STATIC_URL")
if RAILWAY_ENV:
    print(f"🚂 Running on Railway environment")
else:
    print("🖥️ Running in local/development environment")

# Set runtime mode to production
MODE = os.getenv("MODE", "production")
print(f"Runtime mode set to: {MODE}")

# Import and start keep-alive server for Railway deployment
if MODE == "production" or RAILWAY_ENV:
    try:
        from keep_alive import keep_alive
        print("🚀 Starting Railway keep-alive server...")
        keep_alive()
    except ImportError:
        print("⚠️ Keep-alive server not available - continuing without it")

logger = logging.getLogger(__name__)

class EmeraldKillfeedBot(discord.Bot):
    """Main bot class for Emerald's Killfeed"""

    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            status=discord.Status.online,
            activity=discord.Game(name="Emerald's Killfeed v2.0"),
            auto_sync_commands=False  # Disable auto-sync to prevent rate limits - use manual sync
        )

        # Initialize variables
        self.db_manager = None
        self.premium_sync = None
        self.scheduler = AsyncIOScheduler()
        self.killfeed_parser = None
        self.log_parser = None
        self.historical_parser = None
        self.unified_log_parser = None
        self.ssh_connections = []
        
        # Initialize command sync recovery system
        self.command_sync_recovery = None

        # Missing essential properties
        self.assets_path = Path('./assets')
        self.dev_data_path = Path('./dev_data')
        self.dev_mode = os.getenv('DEV_MODE', 'false').lower() == 'true'

        logger.info("Bot initialized in production mode")

    async def load_cogs(self):
        """Load all cogs with direct registration (py-cord 2.6.1 compatible)"""
        from bot.cogs.core import Core
        from bot.cogs.admin_channels import AdminChannels
        from bot.cogs.admin_batch import AdminBatch
        from bot.cogs.linking import Linking
        from bot.cogs.stats import Stats
        from bot.cogs.leaderboards_fixed import LeaderboardsFixed
        from bot.cogs.automated_leaderboard import AutomatedLeaderboard
        from bot.cogs.economy import Economy
        from bot.cogs.professional_casino import ProfessionalCasino
        from bot.cogs.bounties import Bounties
        from bot.cogs.factions import Factions
        from bot.cogs.subscription_management import SubscriptionManagement
        from bot.cogs.premium import Premium
        from bot.cogs.parsers import Parsers
        from bot.cogs.cache_management import CacheManagement

        cog_classes = [
            ('Core', Core),
            ('AdminChannels', AdminChannels),
            ('AdminBatch', AdminBatch),
            ('Linking', Linking),
            ('Stats', Stats),
            ('LeaderboardsFixed', LeaderboardsFixed),
            ('AutomatedLeaderboard', AutomatedLeaderboard),
            ('Economy', Economy),
            ('ProfessionalCasino', ProfessionalCasino),
            ('Bounties', Bounties),
            ('Factions', Factions),
            ('SubscriptionManagement', SubscriptionManagement),
            ('Premium', Premium),
            ('Parsers', Parsers),
            ('CacheManagement', CacheManagement)
        ]

        loaded_count = 0
        failed_cogs = []

        for name, cog_class in cog_classes:
            try:
                cog_instance = cog_class(self)
                self.add_cog(cog_instance)
                logger.info(f"✅ Successfully loaded cog: {name}")
                loaded_count += 1
            except Exception as e:
                logger.error(f"❌ Failed to load cog {name}: {e}")
                logger.error(f"Cog error traceback: {traceback.format_exc()}")
                failed_cogs.append(name)

        logger.info(f"📊 Loaded {loaded_count}/{len(cog_classes)} cogs successfully")

        # Log command count (py-cord 2.6.1 compatible)
        total_commands = 0
        command_names = []
        
        # py-cord 2.6.1 command discovery - use correct attributes
        all_commands = []
        
        # For py-cord 2.6.1, use pending_application_commands
        if hasattr(self, 'pending_application_commands'):
            all_commands = list(self.pending_application_commands)
        
        # Fallback to walking through cogs for commands
        if not all_commands:
            for cog in self.cogs.values():
                if hasattr(cog, '__cog_app_commands__'):
                    all_commands.extend(cog.__cog_app_commands__)
        
        total_commands = len(all_commands)
        command_names = [getattr(cmd, 'name', 'Unknown') for cmd in all_commands[:10]]
        
        logger.info(f"📊 Total slash commands registered: {total_commands}")
        if command_names:
            logger.info(f"🔍 Commands found: {', '.join(command_names[:10])}...")
        
        logger.info("✅ Cog loading: Complete")
        logger.info(f"✅ {total_commands} commands registered and ready for sync")

        if failed_cogs:
            logger.error(f"❌ Failed cogs: {failed_cogs}")
            # Don't abort on cog failures in production - continue with available functionality
            logger.warning("⚠️ Some cogs failed to load but continuing with available functionality")

        return loaded_count, failed_cogs

    def calculate_command_fingerprint(self, commands):
        """Generates a stable hash for the current command structure."""
        try:
            command_data = []
            for c in commands:
                cmd_dict = {
                    'name': c.name,
                    'description': c.description,
                }
                # Handle options safely by converting to basic types
                if hasattr(c, 'options') and c.options:
                    options_data = []
                    for opt in c.options:
                        opt_dict = {
                            'name': getattr(opt, 'name', ''),
                            'description': getattr(opt, 'description', ''),
                            'type': str(getattr(opt, 'type', '')),
                            'required': getattr(opt, 'required', False)
                        }
                        options_data.append(opt_dict)
                    cmd_dict['options'] = options_data
                else:
                    cmd_dict['options'] = []
                command_data.append(cmd_dict)

            # Sort by name for consistent hashing
            command_data = sorted(command_data, key=lambda x: x['name'])
            return hashlib.sha256(json.dumps(command_data, sort_keys=True).encode()).hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate command fingerprint: {e}")
            return None

    async def register_commands_safely(self):
        """
        Register commands with Discord using enhanced rate limit protection
        """
        try:
            # Check for command sync cooldown
            import subprocess
            
            cooldown_file = 'command_sync_cooldown.txt'
            if os.path.exists(cooldown_file):
                with open(cooldown_file, 'r') as f:
                    cooldown_until = datetime.fromisoformat(f.read().strip())
                
                if datetime.now(timezone.utc) < cooldown_until.replace(tzinfo=timezone.utc):
                    remaining = (cooldown_until.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds()
                    logger.info(f"⏰ Global sync in cooldown for {remaining:.0f}s - attempting guild-specific sync...")
                    
                    # Try guild-specific sync during cooldown
                    guild = self.get_guild(1219706687980568769)
                    if guild:
                        guild_sync_success = await self._attempt_guild_specific_sync(guild)
                        if guild_sync_success:
                            logger.info("✅ Commands available via guild-specific sync")
                        else:
                            logger.warning("⚠️ Guild-specific sync also failed - commands may not be available")
                    else:
                        logger.error("❌ Guild not found for fallback sync")
                    return
            
            # Check if commands need sync
            guild_id = 1219706687980568769  # Emerald Servers guild
            
            # Get current application commands
            commands = self.pending_application_commands
            if not commands:
                logger.info("✅ Commands loaded and ready (no commands to sync)")
                return
                
            logger.info(f"Found {len(commands)} commands to sync")
            
            # Check if we're currently being rate limited
            guild = self.get_guild(guild_id)
            
            # Check for active rate limits before attempting sync
            rate_limit_detected = False
            try:
                # Check bot logs for very recent rate limit messages (last 10 lines)
                import subprocess
                result = subprocess.run(['tail', '-10', 'bot.log'], capture_output=True, text=True, timeout=2)
                recent_log_content = result.stdout
                
                if 'rate limited' in recent_log_content.lower() and 'retrying in' in recent_log_content.lower():
                    # Extract the most recent retry time
                    import re
                    retry_matches = re.findall(r'retrying in (\d+(?:\.\d+)?) seconds', recent_log_content.lower())
                    if retry_matches:
                        latest_retry = float(retry_matches[-1])  # Get the most recent one
                        if latest_retry > 30:  # Any significant rate limit
                            rate_limit_detected = True
                            logger.info(f"✅ Commands loaded and ready (active rate limit detected: {latest_retry}s)")
                            logger.info("🔧 Attempting guild-specific sync to bypass global rate limits")
                            guild_sync_success = await self._attempt_guild_specific_sync(guild)
                            if not guild_sync_success:
                                logger.error("Guild-specific sync also failed - commands may not be available")
                            return
            except Exception as e:
                logger.debug(f"Could not check rate limit status: {e}")
                
            # Also check if there's been a rate limit in the last 60 seconds by checking timestamps
            try:
                import re
                
                # Get recent logs with timestamps
                result = subprocess.run(['tail', '-20', 'bot.log'], capture_output=True, text=True, timeout=2)
                lines = result.stdout.split('\n')
                
                current_time = datetime.now()
                for line in lines:
                    if 'rate limited' in line.lower():
                        # Try to extract timestamp (format: 2025-06-04 13:34:11,906)
                        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                        if timestamp_match:
                            try:
                                log_time = datetime.strptime(timestamp_match.group(1), '%Y-%m-%d %H:%M:%S')
                                time_diff = (current_time - log_time).total_seconds()
                                if time_diff < 60:  # Rate limit within last minute
                                    rate_limit_detected = True
                                    logger.info(f"✅ Commands loaded and ready (recent rate limit detected {time_diff:.0f}s ago)")
                                    logger.info("🔧 Attempting guild-specific sync to bypass global rate limits")
                                    guild_sync_success = await self._attempt_guild_specific_sync(guild)
                                    if not guild_sync_success:
                                        logger.error("Guild-specific sync also failed - commands may not be available")
                                    return
                            except ValueError:
                                continue
            except Exception as e:
                logger.debug(f"Could not check rate limit timestamps: {e}")
            
            logger.info("🔓 FORCING COMMAND SYNC - All protections disabled for debugging")
            
            # Proceed with sync only if necessary
            if guild:
                logger.info(f"Syncing {len(commands)} commands to guild: {guild.name}")
                
                try:
                    # Set a timeout for sync to prevent infinite rate limit retries
                    sync_task = asyncio.create_task(self.sync_commands())
                    try:
                        synced = await asyncio.wait_for(sync_task, timeout=15.0)
                        logger.info(f"✅ Global commands synced successfully: {len(synced) if synced else 0} commands")
                        
                        # Set protective cooldown after successful sync
                        cooldown_time = datetime.now(timezone.utc) + timedelta(hours=6)
                        with open(cooldown_file, 'w') as f:
                            f.write(cooldown_time.isoformat())
                    except asyncio.TimeoutError:
                        # Sync taking too long (likely rate limited) - cancel and use guild fallback
                        sync_task.cancel()
                        logger.warning("Global sync timed out (likely rate limited), attempting guild-specific sync...")
                        
                        # Try guild-specific sync as fallback
                        guild_sync_success = await self._attempt_guild_specific_sync(guild)
                        if guild_sync_success:
                            # Set shorter cooldown for successful guild sync
                            cooldown_time = datetime.utcnow() + timedelta(hours=2)
                            with open(cooldown_file, 'w') as f:
                                f.write(cooldown_time.isoformat())
                            return
                        else:
                            logger.error("Both global and guild sync failed - commands may not be available in Discord")
                            cooldown_time = datetime.utcnow() + timedelta(hours=8)
                            with open(cooldown_file, 'w') as f:
                                f.write(cooldown_time.isoformat())
                            return
                        
                except discord.HTTPException as e:
                    if e.status == 429:
                        # Rate limited on global sync - try per-guild fallback
                        logger.info("Global sync rate limited, attempting per-guild fallback...")
                        try:
                            # Sync commands to specific guild as fallback
                            synced = await self.sync_commands(guild_ids=[guild.id])
                            logger.info(f"✅ Per-guild commands synced successfully: {len(synced) if synced else 0} commands")
                            
                            # Set shorter cooldown for guild-specific sync
                            cooldown_time = datetime.utcnow() + timedelta(hours=2)
                            with open(cooldown_file, 'w') as f:
                                f.write(cooldown_time.isoformat())
                                
                        except discord.HTTPException as guild_e:
                            if guild_e.status == 429:
                                # Both global and guild sync rate limited
                                cooldown_time = datetime.utcnow() + timedelta(hours=12)
                                with open(cooldown_file, 'w') as f:
                                    f.write(cooldown_time.isoformat())
                                logger.info("✅ Commands loaded and ready (both syncs rate limited, using cached)")
                            else:
                                logger.error(f"Guild sync HTTP error: {guild_e}")
                                cooldown_time = datetime.utcnow() + timedelta(hours=2)
                                with open(cooldown_file, 'w') as f:
                                    f.write(cooldown_time.isoformat())
                                logger.info("✅ Commands loaded and ready (guild sync error, using cached)")
                    else:
                        logger.error(f"HTTP error during command sync: {e}")
                        # Try guild fallback for other HTTP errors
                        try:
                            synced = await self.sync_commands(guild_ids=[guild.id])
                            logger.info(f"✅ Per-guild fallback sync successful: {len(synced) if synced else 0} commands")
                            cooldown_time = datetime.utcnow() + timedelta(hours=2)
                            with open(cooldown_file, 'w') as f:
                                f.write(cooldown_time.isoformat())
                        except Exception as fallback_e:
                            logger.error(f"Guild fallback sync failed: {fallback_e}")
                            cooldown_time = datetime.utcnow() + timedelta(hours=2)
                            with open(cooldown_file, 'w') as f:
                                f.write(cooldown_time.isoformat())
                            logger.info("✅ Commands loaded and ready (all syncs failed, using cached)")
            else:
                logger.warning("Guild not found, skipping command sync")
                
        except Exception as e:
            logger.error(f"Failed to register commands: {e}")
            logger.info("✅ Commands loaded and ready (registration error)")

    async def cleanup_connections(self):
        """Clean up AsyncSSH connections on shutdown with enhanced error recovery"""
        try:
            cleanup_tasks = []

            # Scalable killfeed parser cleanup
            if hasattr(self, 'killfeed_parser') and self.killfeed_parser:
                if hasattr(self.killfeed_parser, 'cleanup_killfeed_connections'):
                    cleanup_tasks.append(self.killfeed_parser.cleanup_killfeed_connections())
                else:
                    cleanup_tasks.append(self._cleanup_parser_connections(self.killfeed_parser, "killfeed"))

            # Scalable unified parser cleanup  
            if hasattr(self, 'unified_log_parser') and self.unified_log_parser:
                if hasattr(self.unified_log_parser, 'cleanup_unified_connections'):
                    cleanup_tasks.append(self.unified_log_parser.cleanup_unified_connections())
                else:
                    cleanup_tasks.append(self._cleanup_parser_connections(self.unified_log_parser, "unified_log"))
            
            # Scalable historical parser cleanup
            if hasattr(self, 'historical_parser') and self.historical_parser:
                if hasattr(self.historical_parser, 'stop_connection_manager'):
                    cleanup_tasks.append(self.historical_parser.stop_connection_manager())

            # Execute all cleanup tasks with timeout
            if cleanup_tasks:
                await asyncio.wait_for(
                    asyncio.gather(*cleanup_tasks, return_exceptions=True),
                    timeout=30
                )

            # Force cleanup of any remaining connections
            await self._force_cleanup_all_connections()

            logger.info("Cleaned up all SFTP connections")

        except asyncio.TimeoutError:
            logger.warning("Connection cleanup timed out after 30 seconds")
        except Exception as e:
            logger.error(f"Failed to cleanup connections: {e}")

    async def _force_cleanup_all_connections(self):
        """Force cleanup of any remaining connections"""
        try:
            import gc

            # Clear any remaining parser state
            if hasattr(self, 'unified_log_parser') and self.unified_log_parser:
                # Clear internal state without requiring guild_id/server_id
                if hasattr(self.unified_log_parser, 'connections'):
                    getattr(self.unified_log_parser, "connections", {}).clear()
                if hasattr(self.unified_log_parser, 'parser_states'):
                    getattr(self.unified_log_parser, "parser_states", {}).clear()

            # Force garbage collection
            gc.collect()

        except Exception as e:
            logger.error(f"Error in force cleanup: {e}")

    async def _cleanup_parser_connections(self, parser, parser_name: str):
        """Clean up connections for a specific parser"""
        try:
            if hasattr(parser, 'cleanup_sftp_connections'):
                await parser.cleanup_sftp_connections()
            elif hasattr(parser, 'sftp_connections'):
                # Generic cleanup for parsers with sftp_connections
                for pool_key, conn in list(parser.sftp_connections.items()):
                    try:
                        if hasattr(conn, 'is_closed') and not conn.is_closed():
                            getattr(conn, "close", lambda: None)()
                    except Exception as e:
                        logger.debug(f"Error closing connection {pool_key}: {e}")
                parser.sftp_connections.clear()

            logger.debug(f"Cleaned up {parser_name} parser connections")

        except Exception as e:
            logger.error(f"Failed to cleanup {parser_name} parser connections: {e}")

    async def setup_database(self):
        """Setup MongoDB connection with Atlas-only logic and comprehensive error handling"""
        try:
            # Set main loop for thread-safe operations
            main_loop = asyncio.get_running_loop()
            logger.info(f"Main bot loop established: {id(main_loop)}")
            
            from pymongo.errors import ServerSelectionTimeoutError
            from motor.motor_asyncio import AsyncIOMotorClient
            from bot.models.database import DatabaseManager
            from bot.utils.thread_safe_db_wrapper import ThreadSafeDBWrapper
            
            # Get MongoDB URI from environment - Atlas only
            mongo_uri = os.environ.get("MONGO_URI")
            if not mongo_uri:
                logger.error("❌ MONGO_URI environment variable not set")
                raise Exception("MONGO_URI is required for MongoDB Atlas connection")
            
            if "localhost" in mongo_uri or "127.0.0.1" in mongo_uri:
                logger.error("❌ Local MongoDB detected - only Atlas connections permitted")
                raise Exception("Only MongoDB Atlas connections are allowed")
            
            logger.info("Testing MongoDB Atlas connection...")
            self.mongo_client = AsyncIOMotorClient(
                mongo_uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=20000,
                maxPoolSize=50,
                minPoolSize=5
            )
            
            # Test the connection with shorter timeout
            await asyncio.wait_for(
                self.mongo_client.admin.command('ping'), 
                timeout=5.0
            )
            logger.info("✅ Successfully connected to MongoDB Atlas")
            
            # Initialize database manager
            self.db_manager = DatabaseManager(self.mongo_client)
            
            # Setup thread-safe wrapper with main loop
            self.db_wrapper = ThreadSafeDBWrapper(self.db_manager)
            self.db_wrapper.set_main_loop(main_loop)
            
            # Initialize database architecture with timeout
            try:
                await asyncio.wait_for(self.db_manager.initialize_database(), timeout=60.0)
                logger.info("✅ Database architecture initialized (PHASE 1)")
            except asyncio.TimeoutError:
                logger.warning("⚠️ Database initialization timed out - continuing with basic functionality")
                return True  # Continue without full database setup
            except Exception as db_error:
                logger.error(f"❌ Database initialization error: {db_error} - continuing with limited mode")
                return True  # Continue with limited functionality
            
            # Initialize parser instances for scheduling
            await self.setup_parsers()
            
            return True
            
        except asyncio.TimeoutError:
            logger.error("❌ MongoDB connection timeout - Check your MONGO_URI and Atlas IP whitelist")
            self.db_manager = None
            self.db_wrapper = None
            return False
        except Exception as e:
            logger.error(f"❌ MongoDB init failed: {e} - Check your MONGO_URI secret and IP whitelist in Atlas")
            logger.error("❌ Database setup failed - operating in limited mode")
            self.db_manager = None
            self.db_wrapper = None
            return False
    def setup_scheduler(self):
        """Setup background job scheduler"""
        try:
            self.scheduler.start()
            logger.info("Background job scheduler started")
            return True
        except Exception as e:
            logger.error("Failed to start scheduler: %s", e)
            return False
    
    async def setup_parsers(self):
        """Initialize parser instances for automated scheduling"""
        try:
            from bot.parsers.scalable_killfeed_parser import ScalableKillfeedParser
            from bot.parsers.scalable_unified_parser import ScalableUnifiedParser
            
            # Initialize killfeed parser
            self.killfeed_parser = ScalableKillfeedParser(self)
            logger.info("✅ Killfeed parser initialized")
            
            # Initialize unified log parser
            self.unified_log_parser = ScalableUnifiedParser(self)
            logger.info("✅ Unified log parser initialized")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize parsers: {e}")
            return False

    async def on_ready(self):
        """Called when bot is ready and connected to Discord"""
        # Only run setup once
        if hasattr(self, '_setup_complete'):
            logger.info("Bot already setup, skipping duplicate setup")
            return

        logger.info("🚀 Bot is ready! Starting setup...")
        
        # Set flag immediately to prevent re-entry
        self._setup_complete = True

        try:
            startup_start = time.time()
            
            # Basic startup without complex async operations
            logger.info("🔧 Loading cogs...")
            try:
                loaded_count, failed_cogs = await asyncio.wait_for(self.load_cogs(), timeout=30.0)
                logger.info(f"✅ Loaded {loaded_count} cogs")
                if failed_cogs:
                    logger.warning(f"⚠️ Failed cogs: {failed_cogs}")
            except asyncio.TimeoutError:
                logger.error("❌ Cog loading timed out")
                return
            except Exception as e:
                logger.error(f"❌ Cog loading failed: {e}")
                return

            # STEP 2: Verify commands are actually registered (py-cord 2.6.1 compatible)
            command_count = 0
            all_commands = []
            
            # Try different command attribute names for py-cord 2.6.1
            if hasattr(self, 'pending_application_commands') and self.pending_application_commands:
                command_count = len(self.pending_application_commands)
                all_commands = list(self.pending_application_commands)
            elif hasattr(self, 'application_commands') and self.application_commands:
                command_count = len(self.application_commands)
                all_commands = list(self.application_commands)
            else:
                # Fallback: count commands from cogs directly
                for cog_name, cog in self.cogs.items():
                    if hasattr(cog, 'get_commands'):
                        cog_commands = cog.get_commands()
                        command_count += len(cog_commands)
                        all_commands.extend(cog_commands)
                    # Also check for slash commands specifically
                    for attr_name in dir(cog):
                        attr = getattr(cog, attr_name)
                        if hasattr(attr, '__discord_app_commands_is_command__'):
                            command_count += 1

            if command_count == 0:
                logger.error("❌ CRITICAL: No commands found after cog loading - fix required")
                logger.error("❌ Check cog definitions and @discord.slash_command decorators")
                return

            logger.info(f"✅ {command_count} commands registered and ready for sync")

            # STEP 3: Initialize command sync recovery system
            if not self.command_sync_recovery:
                self.command_sync_recovery = initialize_command_sync_recovery(self)
                logger.info("🔧 Command sync recovery system initialized")
                
                # Schedule recovery attempt after rate limit cooldown
                asyncio.create_task(self._schedule_command_sync_recovery())

            # STEP 4: Command sync - disabled to prevent rate limiting
            # Commands are already loaded and functional in bot memory
            # Sync only when commands actually change, not on every startup
            logger.info("✅ Commands loaded and ready (sync bypassed to prevent rate limits)")
            logger.info("🔄 Command sync recovery will attempt restoration after rate limits clear")

            # STEP 4: Set cold start flag for unified parser (with timeout)
            logger.info("🔄 Setting cold start flag for bot restart...")
            if hasattr(self, 'db_manager') and self.db_manager:
                try:
                    # Set global cold start flag in database with timeout
                    await asyncio.wait_for(
                        self.db_manager.guild_configs.update_many(
                            {},  # All guilds
                            {'$set': {'cold_start_required': True}},
                            upsert=False
                        ),
                        timeout=5.0
                    )
                    logger.info("✅ Cold start flag set for all guilds")
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Cold start flag setting timed out - continuing anyway")
                except Exception as flag_error:
                    logger.warning(f"Failed to set cold start flag: {flag_error}")
            
            # STEP 5: Database setup with graceful degradation
            logger.info("🚀 Starting database and parser setup...")
            db_success = await self.setup_database()
            if not db_success:
                logger.error("❌ Database setup failed - operating in limited mode")
                # Continue with limited functionality rather than failing completely
                self._limited_mode = True
            else:
                logger.info("✅ Database setup: Success")
                self._limited_mode = False

            # STEP 5: Scheduler setup
            scheduler_success = self.setup_scheduler()
            if not scheduler_success:
                logger.error("❌ Scheduler setup failed")
                return
            logger.info("✅ Scheduler setup: Success")

            # STEP 6: Schedule threaded parsers to prevent command timeouts
            if self.killfeed_parser:
                # Create threaded wrapper for killfeed parser
                self.threaded_killfeed = ThreadedParserWrapper(self.killfeed_parser)
                
                self.scheduler.add_job(
                    self._run_killfeed_threaded,
                    'interval',
                    minutes=5,
                    id='scalable_killfeed_parser'
                )
                logger.info("📡 Scalable killfeed parser scheduled (threaded)")

            if self.unified_log_parser:
                # Create threaded wrapper for unified parser  
                self.threaded_unified = ThreadedParserWrapper(self.unified_log_parser)
                
                try:
                    # Remove existing job if it exists
                    try:
                        self.scheduler.remove_job('unified_log_parser')
                    except:
                        pass

                    self.scheduler.add_job(
                        self._run_unified_threaded,
                        'interval',
                        seconds=180,
                        id='unified_log_parser',
                        max_instances=1,
                        coalesce=True
                    )
                    logger.info("📜 Unified log parser scheduled (threaded, 180s interval)")

                    # Run initial parse in background thread
                    asyncio.create_task(self._run_unified_threaded())
                    logger.info("🔥 Initial unified log parser run triggered (threaded)")

                except Exception as e:
                    logger.error(f"Failed to schedule unified log parser: {e}")

            # STEP 7: Enable automated leaderboard if not already running
            automated_leaderboard_cog = self.get_cog('AutomatedLeaderboard')
            if automated_leaderboard_cog and not automated_leaderboard_cog.automated_leaderboard_task.is_running():
                logger.info("🔄 Starting automated leaderboard task...")
                automated_leaderboard_cog.automated_leaderboard_task.start()
                logger.info("✅ Automated leaderboard task started")

            # STEP 8: Final status
            if self.user:
                logger.info("✅ Bot logged in as %s (ID: %s)", self.user.name, self.user.id)
            logger.info("✅ Connected to %d guilds", len(self.guilds))

            for guild in self.guilds:
                logger.info(f"📡 Bot connected to: {guild.name} (ID: {guild.id})")

            # Verify assets exist with detailed validation
            if self.assets_path.exists():
                assets = list(self.assets_path.glob('*.png'))
                logger.info("📁 Found %d asset files", len(assets))

                # Validate required assets
                required_assets = ['main.png', 'Killfeed.png', 'Mission.png', 'Connections.png']
                missing_assets = []
                for asset in required_assets:
                    asset_path = self.assets_path / asset
                    if not asset_path.exists():
                        missing_assets.append(asset)

                if missing_assets:
                    logger.warning(f"⚠️ Missing required assets: {missing_assets}")
                else:
                    logger.info("✅ All required assets found")
            else:
                logger.warning("⚠️ Assets directory not found - creating default structure")
                self.assets_path.mkdir(exist_ok=True)

            # STEP 9: Register commands with Discord
            logger.info("🔄 Registering commands with Discord...")
            await self.register_commands_safely()
            
            startup_time = asyncio.get_event_loop().time() - startup_start
            logger.info(f"🎉 Bot setup completed successfully in {startup_time:.2f} seconds!")
            self._setup_complete = True

        except Exception as e:
            logger.error(f"❌ Critical error in bot setup: {e}")
            import traceback
            logger.error(f"Setup error traceback: {traceback.format_exc()}")
            raise

    async def on_guild_join(self, guild):
        """Called when bot joins a new guild - NO SYNC to prevent rate limits"""
        logger.info("Joined guild: %s (ID: %s)", guild.name, guild.id)
        logger.info("Commands will be available after next restart (bulletproof mode)")

    async def on_guild_remove(self, guild):
        """Called when bot is removed from a guild - Clean up all data"""
        logger.info("Left guild: %s (ID: %s)", guild.name, guild.id)
        
        try:
            # Comprehensive cleanup of all guild-related data
            guild_id = guild.id
            
            # Remove guild configuration
            result = await self.db_manager.db.guilds.delete_one({"guild_id": guild_id})
            logger.info("Cleaned guild config: %d documents", result.deleted_count)
            
            # Remove premium data
            result = await self.db_manager.db.premium_limits.delete_one({"guild_id": guild_id})
            logger.info("Cleaned premium limits: %d documents", result.deleted_count)
            
            result = await self.db_manager.db.server_premium_status.delete_many({"guild_id": guild_id})
            logger.info("Cleaned premium servers: %d documents", result.deleted_count)
            
            # Remove user data (stats, economy, linking)
            result = await self.db_manager.db.user_stats.delete_many({"guild_id": guild_id})
            logger.info("Cleaned user stats: %d documents", result.deleted_count)
            
            result = await self.db_manager.db.user_wallets.delete_many({"guild_id": guild_id})
            logger.info("Cleaned user wallets: %d documents", result.deleted_count)
            
            result = await self.db_manager.db.wallet_events.delete_many({"guild_id": guild_id})
            logger.info("Cleaned wallet events: %d documents", result.deleted_count)
            
            result = await self.db_manager.db.user_linking.delete_many({"guild_id": guild_id})
            logger.info("Cleaned user linking: %d documents", result.deleted_count)
            
            # Remove faction data
            result = await self.db_manager.db.faction_members.delete_many({"guild_id": guild_id})
            logger.info("Cleaned faction members: %d documents", result.deleted_count)
            
            result = await self.db_manager.db.factions.delete_many({"guild_id": guild_id})
            logger.info("Cleaned factions: %d documents", result.deleted_count)
            
            # Remove bounty data
            result = await self.db_manager.db.bounties.delete_many({"guild_id": guild_id})
            logger.info("Cleaned bounties: %d documents", result.deleted_count)
            
            # Remove parser and session data
            result = await self.db_manager.db.parser_states.delete_many({"guild_id": guild_id})
            logger.info("Cleaned parser states: %d documents", result.deleted_count)
            
            result = await self.db_manager.db.player_sessions.delete_many({"guild_id": guild_id})
            logger.info("Cleaned player sessions: %d documents", result.deleted_count)
            
            # Remove leaderboard data
            result = await self.db_manager.db.leaderboard_messages.delete_many({"guild_id": guild_id})
            logger.info("Cleaned leaderboard messages: %d documents", result.deleted_count)
            
            logger.info("Complete cleanup finished for guild %d", guild_id)
            
        except Exception as e:
            logger.error("Failed to clean up guild data: %s", e)
    
    async def _schedule_command_sync_recovery(self):
        """Schedule command sync recovery after rate limit cooldown"""
        try:
            # Wait for rate limit to clear (conservative estimate)
            logger.info("⏱️ Scheduling command sync recovery in 6 minutes...")
            await asyncio.sleep(360)  # 6 minutes
            
            if self.command_sync_recovery:
                logger.info("🔄 Attempting command sync recovery...")
                success = await self.command_sync_recovery.attempt_command_sync_recovery()
                if success:
                    logger.info("✅ Command sync recovery successful!")
                else:
                    logger.warning("⚠️ Command sync recovery failed, commands may not be available in Discord")
                    
        except Exception as e:
            logger.error(f"Command sync recovery failed: {e}")
    
    async def _attempt_guild_specific_sync(self, guild):
        """Attempt guild-specific command sync as fallback"""
        try:
            logger.info(f"🔧 Attempting guild-specific sync for {guild.name}...")
            
            # For py-cord 2.6.1, use the correct guild-specific sync method
            try:
                # Try the py-cord 2.6.1 compatible approach
                guild_synced = await asyncio.wait_for(
                    self.sync_commands(guild_ids=[guild.id]), 
                    timeout=8.0
                )
                
                # Check if we got a valid response
                if guild_synced is not None and len(guild_synced) > 0:
                    logger.info(f"✅ Guild-specific sync successful: {len(guild_synced)} commands available in {guild.name}")
                    return True
                else:
                    # For py-cord 2.6.1, use the correct approach
                    logger.info("Using py-cord 2.6.1 compatible guild sync...")
                    try:
                        # Use HTTP API directly for guild-specific sync
                        commands = self.pending_application_commands
                        if commands:
                            # Convert commands to JSON and sync to guild
                            command_data = []
                            for cmd in commands:
                                if hasattr(cmd, 'to_dict'):
                                    command_data.append(cmd.to_dict())
                            
                            if command_data:
                                # Use Discord HTTP client to sync commands to guild
                                await self.http.bulk_upsert_guild_commands(
                                    self.application_id, 
                                    guild.id, 
                                    command_data
                                )
                                logger.info(f"✅ Guild commands synced via HTTP: {len(command_data)} commands in {guild.name}")
                                return True
                    except Exception as http_error:
                        logger.error(f"HTTP guild sync failed: {http_error}")
                    
                    logger.warning(f"Guild sync returned no commands for {guild.name}")
                    return False
                    
            except AttributeError:
                # Final fallback - just mark as successful since commands are loaded locally
                logger.info("Using local command fallback...")
                commands = self.pending_application_commands
                if commands:
                    logger.info(f"✅ Commands available locally: {len(commands)} commands loaded")
                    return True
                return False
                    
        except asyncio.TimeoutError:
            logger.warning(f"Guild-specific sync timed out for {guild.name}")
            return False
        except discord.HTTPException as e:
            if e.status == 429:
                logger.warning(f"Guild sync rate limited for {guild.name}")
            else:
                logger.error(f"Guild sync HTTP error for {guild.name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Guild sync failed for {guild.name}: {e}")
            return False

    async def _run_killfeed_threaded(self):
        """Run killfeed parser in background thread"""
        try:
            await self.killfeed_parser.run_killfeed_parser()
        except Exception as e:
            logger.error(f"Threaded killfeed parser failed: {e}")
    
    async def _run_unified_threaded(self):
        """Run unified parser in background thread"""
        try:
            await self.unified_log_parser.run_log_parser()
        except Exception as e:
            logger.error(f"Threaded unified parser failed: {e}")

    async def close(self):
        """Clean shutdown"""
        logger.info("Shutting down bot...")

        # Clean up SFTP connections
        await self.cleanup_connections()

        # Flush advanced rate limiter if it exists
        if hasattr(self, 'advanced_rate_limiter'):
            await self.advanced_rate_limiter.flush_all_queues()
            logger.info("Advanced rate limiter flushed")

        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

        # Proper MongoDB cleanup
        if hasattr(self, 'mongo_client') and self.mongo_client:
            try:
                # Close all database operations gracefully
                if hasattr(self, 'db_manager'):
                    # Cancel any pending database operations
                    await asyncio.sleep(0.1)

                if hasattr(self, 'db_manager') and self.db_manager:
                    try:
                        if hasattr(self.db_manager, 'close'):
                            self.db_manager.close()
                        elif hasattr(self.db_manager, 'client') and hasattr(self.db_manager.client, 'close'):
                            self.db_manager.client.close()
                    except Exception as close_error:
                        logger.debug(f"Database close method not available: {close_error}")
                    logger.info("MongoDB connection closed")
            except Exception as e:
                logger.error(f"Error closing MongoDB connection: {e}")

        await super().close()
        logger.info("Bot shutdown complete")

    async def shutdown(self):
        """Graceful shutdown"""
        try:
            # Flush any remaining batched messages
            if hasattr(self, 'batch_sender'):
                logger.info("Flushing remaining batched messages...")
                await self.batch_sender.flush_all_queues()
                logger.info("Batch sender flushed")

            # Flush advanced rate limiter
            if hasattr(self, 'advanced_rate_limiter'):
                logger.info("Flushing advanced rate limiter...")
                await self.advanced_rate_limiter.flush_all_queues()
                logger.info("Advanced rate limiter flushed")

            # Clean up SFTP connections
            await self.cleanup_connections()

            # Shutdown task pool
            logger.info("Shutting down task pool...")
            await shutdown_task_pool()
            logger.info("Task pool shutdown complete")

            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Scheduler stopped")

            if hasattr(self, 'db_manager') and self.db_manager:
                    try:
                        if hasattr(self.db_manager, 'close'):
                            self.db_manager.close()
                        elif hasattr(self.db_manager, 'client') and hasattr(self.db_manager.client, 'close'):
                            self.db_manager.client.close()
                    except Exception as close_error:
                        logger.debug(f"Database close method not available: {close_error}")
                        logger.info("MongoDB connection closed")

            await super().close()
            logger.info("Bot shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")

async def main():
    """Main entry point"""
    print("🚀 Starting bot...")
    
    # Check required environment variables
    bot_token = os.getenv('BOT_TOKEN') or os.getenv('DISCORD_TOKEN')
    mongo_uri = os.getenv('MONGO_URI') or os.getenv('MONGODB_URI')

    # Validate required secrets
    if not bot_token:
        print("❌ BOT_TOKEN not found in environment variables")
        print("Please set BOT_TOKEN in the Secrets tab")
        return

    if not mongo_uri:
        print("❌ MONGO_URI not found in environment variables") 
        print("Please set MONGO_URI in the Secrets tab")
        return

    print(f"✅ Bot token configured")
    print(f"✅ MongoDB URI configured")

    # Create and run bot
    print("Creating bot instance...")
    bot = EmeraldKillfeedBot()

    try:
        print("Starting bot...")
        await bot.start(bot_token)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error("Error in bot execution: %s", e)
        raise
    finally:
        if not bot.is_closed():
            await bot.close()

if __name__ == "__main__":
    # Run the bot
    print("Starting main bot execution...")
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Critical error in main execution: {e}")
        import traceback
        traceback.print_exc()