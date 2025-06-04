"""
Scalable Unified Log Parser
Enterprise-grade unified log processing with Deadside.log focus, file rotation detection, and proper channel delivery
"""

import asyncio
import logging
import discord
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from bot.utils.scalable_unified_processor import ScalableUnifiedProcessor
from bot.utils.shared_parser_state import get_shared_state_manager

logger = logging.getLogger(__name__)

class ScalableUnifiedParser:
    """Scalable unified parser with connection pooling and channel delivery integration"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions: Dict[int, ScalableUnifiedProcessor] = {}
        self.state_manager = get_shared_state_manager()
        self.activity_tracker = {}  # Track server activity levels
        self.last_activity_check = None
        self.bot_startup_time = datetime.now(timezone.utc)  # Track bot startup for cold start detection
        
    async def run_log_parser(self):
        """Main scheduled unified log parser execution with cold/hot start modes"""
        try:
            logger.info("🔍 Starting scalable unified log parser run...")
            
            # Get all guilds with servers configured
            guild_configs = await self._get_all_guild_configs()
            
            if not guild_configs:
                logger.info("🔍 Scalable unified parser: Found 0 guilds with servers configured")
                return
            
            total_servers = sum(len(servers) for servers in guild_configs.values())
            logger.info(f"🔍 Scalable unified parser: Processing {len(guild_configs)} guilds with {total_servers} total servers")
            
            # Determine cold vs hot start mode for each guild
            for guild_id, servers in guild_configs.items():
                try:
                    # MANDATORY COLD START: Force cold start for first 5 minutes after bot startup
                    time_since_startup = (datetime.now(timezone.utc) - self.bot_startup_time).total_seconds()
                    force_cold_start = time_since_startup < 300  # 5 minutes
                    
                    if force_cold_start:
                        logger.info(f"🔧 Guild {guild_id}: MANDATORY COLD START (bot startup < 5 min) for {len(servers)} servers")
                        processor = ScalableUnifiedProcessor(self.bot)
                        await self._process_guild_with_mode(guild_id, servers, processor, is_cold_start=True)
                        continue
                    
                    # Check if parser state exists for this guild AND all its servers
                    guild_parser_state = await self.bot.db_manager.parser_states.find_one({
                        'guild_id': guild_id,
                        'parser_type': 'unified'
                    })
                    
                    # Check if any servers are new (don't have parser state)
                    new_servers = []
                    existing_servers = []
                    
                    for server_config in servers:
                        server_id = server_config.get('server_id', 'default')
                        server_parser_state = await self.bot.db_manager.parser_states.find_one({
                            'guild_id': guild_id,
                            'server_id': server_id,
                            'parser_type': 'unified'
                        })
                        
                        if server_parser_state:
                            existing_servers.append(server_config)
                        else:
                            new_servers.append(server_config)
                    
                    # Process new servers with COLD start
                    if new_servers:
                        logger.info(f"🔧 Guild {guild_id}: COLD START for {len(new_servers)} new servers")
                        processor = ScalableUnifiedProcessor(self.bot)
                        await self._process_guild_with_mode(guild_id, new_servers, processor, is_cold_start=True)
                    
                    # Process existing servers with HOT start
                    if existing_servers:
                        logger.info(f"🔧 Guild {guild_id}: HOT START for {len(existing_servers)} existing servers")
                        processor = ScalableUnifiedProcessor(self.bot)
                        await self._process_guild_with_mode(guild_id, existing_servers, processor, is_cold_start=False)
                    
                except Exception as e:
                    logger.error(f"Failed to process guild {guild_id}: {e}")
                    continue
            
            logger.info(f"✅ Scalable unified parser completed processing for {len(guild_configs)} guilds")
            
        except Exception as e:
            logger.error(f"❌ Scalable unified parser error: {e}")
            import traceback
            logger.error(f"Parser traceback: {traceback.format_exc()}")
    

    
    async def _process_guild_with_mode(self, guild_id: int, servers: List[Dict], processor, is_cold_start: bool):
        """Process guild with cold or hot start mode"""
        try:
            for server_config in servers:
                server_id = server_config.get('server_id', 'default')
                server_name = server_config.get('server_name', 'Unknown')
                
                if is_cold_start:
                    # COLD START: Process all events, track states, send NO embeds, update voice channel once at end
                    logger.info(f"❄️ COLD START: {server_name} - Processing all events chronologically, no embeds")
                    
                    # Process all log data chronologically from beginning
                    events = await processor.process_log_data_cold_start(
                        server_config=server_config,
                        guild_id=guild_id
                    )
                    
                    if events:
                        # Update player sessions without sending embeds and get actual counts
                        online_count, queued_count = await processor.update_player_sessions_cold(events, guild_id, server_id)
                        
                        # Update voice channel with accurate counts
                        from bot.utils.voice_channel_manager import VoiceChannelManager
                        vc_manager = VoiceChannelManager(self.bot)
                        await vc_manager.update_voice_channel_count(guild_id, server_id, online_count, queued_count)
                        
                        # Set parser state for future hot starts
                        await self._set_parser_state(guild_id, server_id, events[-1].get('timestamp'))
                        
                        logger.info(f"❄️ COLD START complete: {server_name} - {len(events)} events processed, voice channel updated")
                        logger.info(f"🔊 Voice channel updated: {server_name} - {online_count} online, {queued_count} queued")
                    
                else:
                    # HOT START: Process new events since last run, send all embeds, update voice channel once at end
                    logger.info(f"🔥 HOT START: {server_name} - Processing new events, sending embeds")
                    
                    # Get last parser state
                    parser_state = await self.bot.db_manager.parser_states.find_one({
                        'guild_id': guild_id,
                        'server_id': server_id,
                        'parser_type': 'unified'
                    })
                    
                    last_timestamp = parser_state.get('last_timestamp') if parser_state else None
                    
                    # Process only new events since last run
                    events = await processor.process_log_data_hot_start(
                        server_config=server_config,
                        guild_id=guild_id,
                        last_timestamp=last_timestamp
                    )
                    
                    if events:
                        # Update player sessions and send connection embeds
                        state_changes = await processor.update_player_sessions(events)
                        
                        # Send connection embeds for state changes
                        if state_changes:
                            await processor.send_connection_embeds_batch(state_changes)
                        
                        # Send game event embeds
                        game_events = [e for e in events if e.get('type') == 'event']
                        if game_events:
                            await processor.send_event_embeds_batch(game_events)
                        
                        # Update voice channel count once at the end
                        await self._update_voice_channel_final(guild_id, server_id, server_name)
                        
                        # Update parser state for next run
                        await self._set_parser_state(guild_id, server_id, events[-1].get('timestamp'))
                        
                        logger.info(f"🔥 HOT START complete: {server_name} - {len(events)} events processed, embeds sent")
                    else:
                        logger.info(f"🔥 HOT START: {server_name} - No new events")
                        
        except Exception as e:
            logger.error(f"Failed to process guild {guild_id} with mode: {e}")
    
    async def _update_voice_channel_final(self, guild_id: int, server_id: str, server_name: str):
        """Update voice channel count once at the end to avoid spam"""
        try:
            # Get online and queued player counts separately
            online_count = await self.bot.db_manager.player_sessions.count_documents({
                'guild_id': guild_id,
                'server_id': server_id,
                'state': 'online'
            })
            
            queued_count = await self.bot.db_manager.player_sessions.count_documents({
                'guild_id': guild_id,
                'server_id': server_id,
                'state': 'queued'
            })
            
            # Update voice channel with separate counts
            from bot.utils.voice_channel_manager import VoiceChannelManager
            vc_manager = VoiceChannelManager(self.bot)
            await vc_manager.update_voice_channel_count(guild_id, server_id, online_count, queued_count)
            
            logger.info(f"🔊 Voice channel updated: {server_name} - {online_count} online, {queued_count} queued")
            
        except Exception as e:
            logger.error(f"Failed to update voice channel for {server_name}: {e}")
    
    async def _set_parser_state(self, guild_id: int, server_id: str, last_timestamp):
        """Set parser state for next run"""
        try:
            await self.bot.db_manager.parser_states.update_one(
                {
                    'guild_id': guild_id,
                    'server_id': server_id,
                    'parser_type': 'unified'
                },
                {
                    '$set': {
                        'last_timestamp': last_timestamp,
                        'last_updated': datetime.now(timezone.utc)
                    }
                },
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to set parser state: {e}")
    
    async def _process_all_guilds(self, guild_configs: Dict[int, List[Dict]], processor):
        """Process all guilds using the unified processor"""
        results = {}
        
        for guild_id, servers in guild_configs.items():
            try:
                guild_results = []
                for server in servers:
                    # Process log data for each server
                    log_data = await self._fetch_server_logs(server)
                    if log_data:
                        events = await processor.process_log_data(log_data, server)
                        if events:
                            # Update player sessions based on connection events
                            await processor.update_player_sessions(events)
                            
                            # Send event embeds for game events
                            await processor.send_event_embeds(events)
                            
                            # Update voice channel with current player count
                            await self._update_voice_channel_for_guild(guild_id)
                            
                            guild_results.extend(events)
                            logger.info(f"Processed {len(events)} events for {server.get('name', 'Unknown')}")
                
                results[guild_id] = guild_results
                
            except Exception as e:
                logger.error(f"Error processing guild {guild_id}: {e}")
                results[guild_id] = []
        
        return results
    
    async def _fetch_server_logs(self, server_config: Dict) -> str:
        """Fetch log data from server via SFTP using server-specific credentials"""
        try:
            import asyncssh
            
            # Get server-specific SSH credentials from server config
            host = server_config.get('host') or server_config.get('sftp_host')
            username = server_config.get('sftp_username') or server_config.get('username')
            password = server_config.get('sftp_password') or server_config.get('password')
            port = server_config.get('sftp_port', server_config.get('port', 22))
            
            if not host or not username or not password:
                logger.debug(f"Missing SSH credentials for server {server_config.get('name', 'Unknown')}")
                return ""
            
            # Build dynamic server-specific log path
            server_id = server_config.get('server_id', server_config.get('_id', '7020'))
            log_file_name = server_config.get('log_file', 'Deadside.log')
            
            # Use dynamic path pattern: ./{host}_{server_id}/Logs/Deadside.log
            if server_config.get('log_path'):
                log_file_path = f"{server_config['log_path']}/{log_file_name}"
                logger.info(f"Using hardcoded log_path: {log_file_path}")
            else:
                log_file_path = f"./{host}_{server_id}/Logs/{log_file_name}"
                logger.info(f"Using dynamic path pattern: {log_file_path}")
            
            # Connect via SFTP using server-specific credentials with compatibility parameters
            try:
                async with asyncssh.connect(
                    host, 
                    port=int(port),
                    username=username, 
                    password=password,
                    known_hosts=None,
                    kex_algs=['diffie-hellman-group1-sha1', 'diffie-hellman-group14-sha1', 'diffie-hellman-group14-sha256', 'diffie-hellman-group16-sha512', 'ecdh-sha2-nistp256', 'ecdh-sha2-nistp384', 'ecdh-sha2-nistp521'],
                    encryption_algs=['aes128-ctr', 'aes192-ctr', 'aes256-ctr', 'aes128-cbc', 'aes192-cbc', 'aes256-cbc'],
                    mac_algs=['hmac-sha1', 'hmac-sha2-256', 'hmac-sha2-512'],
                    compression_algs=['none'],
                    server_host_key_algs=['ssh-rsa', 'rsa-sha2-256', 'rsa-sha2-512', 'ssh-dss']
                ) as conn:
                    async with conn.start_sftp_client() as sftp:
                        try:
                            # Check if file exists and get size
                            file_stat = await sftp.stat(log_file_path)
                            file_size = file_stat.size
                            
                            if file_size == 0:
                                logger.debug(f"Log file is empty: {log_file_path}")
                                return ""
                            
                            # Read last 50KB for recent events
                            read_size = min(51200, file_size)  # 50KB
                            start_pos = max(0, file_size - read_size)
                            
                            # Read the log data
                            async with sftp.open(log_file_path, 'r') as f:
                                await f.seek(start_pos)
                                log_data = await f.read()
                                
                            logger.info(f"Fetched {len(log_data)} bytes from {server_config.get('name', 'Unknown')} ({host})")
                            return log_data
                            
                        except FileNotFoundError:
                            logger.debug(f"Log file not found: {log_file_path} on {host}")
                            return ""
                        except Exception as file_error:
                            logger.error(f"Error reading log file {log_file_path} on {host}: {file_error}")
                            return ""
                            
            except Exception as conn_error:
                logger.error(f"SSH connection failed to {host}:{port} - {conn_error}")
                return ""
                    
        except Exception as e:
            logger.error(f"Failed to fetch logs for server {server_config.get('name', 'Unknown')}: {e}")
            return ""
    
    async def _update_voice_channel_for_guild(self, guild_id: int):
        """Update voice channel with current player count for a guild"""
        try:
            # Get online player count from database
            online_count = await self.bot.db_manager.player_sessions.count_documents({
                'guild_id': guild_id,
                'state': 'online'
            })
            
            # Get guild configuration
            guild_config = await self.bot.db_manager.get_guild(guild_id)
            if not guild_config:
                return
            
            # Find voice channel ID
            voice_channel_id = None
            server_channels = guild_config.get('server_channels', {})
            
            # Check for voice channel in server configurations
            for server_key, channels in server_channels.items():
                if isinstance(channels, dict):
                    voice_channel_id = channels.get('voice_counter') or channels.get('playercountvc')
                    if voice_channel_id:
                        break
            
            # Check legacy channels if not found
            if not voice_channel_id:
                legacy_channels = guild_config.get('channels', {})
                voice_channel_id = legacy_channels.get('voice_counter') or legacy_channels.get('playercountvc')
            
            if not voice_channel_id:
                return
            
            # Get Discord guild and channel
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            
            voice_channel = guild.get_channel(voice_channel_id)
            if not voice_channel or voice_channel.type != discord.ChannelType.voice:
                return
            
            # Create channel name with player count
            server_name = "Emerald"  # Default server name
            servers = guild_config.get('servers', [])
            if servers:
                server_name = servers[0].get('name', 'Emerald').replace(' EU', '').replace(' Server', '')
            
            # Determine status emoji
            max_players = 60  # Default max players
            if servers:
                max_players = servers[0].get('max_players', 60)
            
            if online_count == 0:
                emoji = "🔴"
            elif online_count >= max_players * 0.8:
                emoji = "🟡"
            else:
                emoji = "🟢"
            
            new_name = f"{emoji} {server_name} | {online_count}/{max_players}"
            
            # Update channel name if different
            if voice_channel.name != new_name:
                await voice_channel.edit(name=new_name)
                logger.info(f"Updated voice channel to: {new_name}")
            
        except Exception as e:
            logger.error(f"Failed to update voice channel for guild {guild_id}: {e}")
    
    async def _update_activity_tracking(self, results: Dict[str, Any]):
        """Update server activity tracking for smart scheduling"""
        try:
            current_time = datetime.now(timezone.utc)
            
            # Process guild results to track activity
            for guild_id, guild_result in results.get('guild_results', {}).items():
                for server_result in guild_result.get('server_results', {}).values():
                    server_id = server_result.get('server_id', 'unknown')
                    processed_kills = server_result.get('processed_kills', 0)
                    
                    # Initialize tracking for new servers
                    if server_id not in self.activity_tracker:
                        self.activity_tracker[server_id] = {
                            'recent_activity': [],
                            'avg_kills_per_hour': 0,
                            'last_active': None,
                            'activity_level': 'idle'  # idle, moderate, active, high
                        }
                    
                    # Record this parsing session
                    self.activity_tracker[server_id]['recent_activity'].append({
                        'timestamp': current_time,
                        'kills_processed': processed_kills
                    })
                    
                    # Keep only last 20 sessions for analysis (last hour of data)
                    self.activity_tracker[server_id]['recent_activity'] = \
                        self.activity_tracker[server_id]['recent_activity'][-20:]
                    
                    # Update activity metrics
                    if processed_kills > 0:
                        self.activity_tracker[server_id]['last_active'] = current_time
                    
                    # Calculate activity level
                    await self._calculate_activity_level(server_id)
            
            self.last_activity_check = current_time
            
        except Exception as e:
            logger.error(f"Failed to update activity tracking: {e}")
    
    async def _calculate_activity_level(self, server_id: str):
        """Calculate activity level for a server based on recent data"""
        try:
            tracker = self.activity_tracker[server_id]
            recent_sessions = tracker['recent_activity']
            
            if not recent_sessions:
                tracker['activity_level'] = 'idle'
                tracker['avg_kills_per_hour'] = 0
                return
            
            # Calculate kills per hour over recent sessions
            current_time = datetime.now(timezone.utc)
            one_hour_ago = current_time.replace(hour=current_time.hour-1) if current_time.hour > 0 else current_time.replace(day=current_time.day-1, hour=23)
            
            recent_kills = sum(
                session['kills_processed'] 
                for session in recent_sessions 
                if session['timestamp'] >= one_hour_ago
            )
            
            # Estimate kills per hour (3-minute intervals = 20 sessions per hour)
            sessions_in_hour = len([s for s in recent_sessions if s['timestamp'] >= one_hour_ago])
            if sessions_in_hour > 0:
                estimated_kills_per_hour = (recent_kills / sessions_in_hour) * 20
            else:
                estimated_kills_per_hour = 0
            
            tracker['avg_kills_per_hour'] = estimated_kills_per_hour
            
            # Classify activity level
            if estimated_kills_per_hour >= 60:  # 1+ kills per minute
                tracker['activity_level'] = 'high'
            elif estimated_kills_per_hour >= 20:  # 1 kill per 3 minutes
                tracker['activity_level'] = 'active'
            elif estimated_kills_per_hour >= 5:   # 1 kill per 12 minutes
                tracker['activity_level'] = 'moderate'
            else:
                tracker['activity_level'] = 'idle'
                
        except Exception as e:
            logger.error(f"Failed to calculate activity level for server {server_id}: {e}")
    
    async def _get_activity_summary(self) -> str:
        """Get a summary of current server activity levels"""
        try:
            if not self.activity_tracker:
                return ""
            
            activity_counts = {'high': 0, 'active': 0, 'moderate': 0, 'idle': 0}
            
            for tracker in self.activity_tracker.values():
                level = tracker.get('activity_level', 'idle')
                activity_counts[level] += 1
            
            if activity_counts['high'] > 0 or activity_counts['active'] > 0:
                return f" | Activity: {activity_counts['high']} high, {activity_counts['active']} active, {activity_counts['moderate']} moderate, {activity_counts['idle']} idle"
            else:
                return f" | Activity: {activity_counts['moderate']} moderate, {activity_counts['idle']} idle servers"
                
        except Exception:
            return ""
    
    def get_recommended_interval(self) -> int:
        """Get recommended parsing interval based on current activity levels"""
        try:
            if not self.activity_tracker:
                return 180  # Default 3 minutes
            
            activity_counts = {'high': 0, 'active': 0, 'moderate': 0, 'idle': 0}
            
            for tracker in self.activity_tracker.values():
                level = tracker.get('activity_level', 'idle')
                activity_counts[level] += 1
            
            # Smart interval selection
            if activity_counts['high'] > 0:
                return 60   # 1 minute for high activity servers
            elif activity_counts['active'] > 0:
                return 120  # 2 minutes for active servers
            elif activity_counts['moderate'] > 0:
                return 180  # 3 minutes for moderate activity
            else:
                return 300  # 5 minutes for idle servers only
                
        except Exception:
            return 180  # Safe default
    
    async def _get_all_guild_configs(self) -> Dict[int, List[Dict[str, Any]]]:
        """Get all guild configurations with servers using direct database access"""
        guild_configs = {}
        
        try:
            # Use direct MongoDB connection for thread safety
            import os
            from motor.motor_asyncio import AsyncIOMotorClient
            
            mongo_uri = os.environ.get('MONGO_URI')
            if not mongo_uri:
                logger.error("MONGO_URI not available")
                return guild_configs
            
            client = AsyncIOMotorClient(mongo_uri)
            database = client.emerald_killfeed
            collection = database.guild_configs
            
            # Find guilds with enabled servers
            cursor = collection.find({
                'servers': {
                    '$exists': True,
                    '$not': {'$size': 0},
                    '$elemMatch': {'enabled': True}
                }
            })
            
            guild_docs = await cursor.to_list(length=None)
            
            for guild_doc in guild_docs:
                guild_id = guild_doc.get('guild_id')
                servers = guild_doc.get('servers', [])
                
                if guild_id and servers:
                    # Filter for enabled servers only
                    enabled_servers = [s for s in servers if s.get('enabled', False)]
                    
                    if enabled_servers:
                        # Add guild_id to each server config
                        for server in enabled_servers:
                            server['guild_id'] = guild_id
                        
                        guild_configs[guild_id] = enabled_servers
            
            logger.info(f"Found {len(guild_configs)} guilds with enabled servers")
            
        except Exception as e:
            logger.error(f"Failed to get guild configurations: {e}")
        
        return guild_configs
    
    async def process_guild_manual(self, guild_id: int) -> Dict[str, Any]:
        """Manually trigger unified processing for a specific guild"""
        try:
            # Get guild configuration
            guild_config = await getattr(self.bot, 'cached_db_manager', self.bot.db_manager).get_guild(guild_id)
            if not guild_config or not guild_config.get('servers'):
                return {
                    'success': False,
                    'error': 'No servers configured for this guild'
                }
            
            servers = guild_config.get('servers', [])
            # Add guild_id to server configs
            for server in servers:
                server['guild_id'] = guild_id
            
            # Process guild
            processor = ScalableUnifiedProcessor(guild_id, self.bot)
            self.active_sessions[guild_id] = processor
            
            try:
                results = await processor.process_guild_servers(servers)
                return {
                    'success': True,
                    'guild_id': guild_id,
                    'results': results
                }
            finally:
                if guild_id in self.active_sessions:
                    del self.active_sessions[guild_id]
            
        except Exception as e:
            logger.error(f"Manual unified processing failed for guild {guild_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def process_server_manual(self, guild_id: int, server_name: str) -> Dict[str, Any]:
        """Manually trigger unified processing for a specific server"""
        try:
            # Get guild configuration
            guild_config = await getattr(self.bot, 'cached_db_manager', self.bot.db_manager).get_guild(guild_id)
            if not guild_config or not guild_config.get('servers'):
                return {
                    'success': False,
                    'error': 'No servers configured for this guild'
                }
            
            # Find the specific server
            target_server = None
            for server in guild_config.get('servers', []):
                if server.get('name') == server_name or server.get('server_name') == server_name:
                    server['guild_id'] = guild_id
                    target_server = server
                    break
            
            if not target_server:
                return {
                    'success': False,
                    'error': f'Server {server_name} not found'
                }
            
            # Process single server
            processor = ScalableUnifiedProcessor(guild_id)
            results = await processor.process_guild_servers([target_server])
            
            return {
                'success': True,
                'server_name': server_name,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Manual server processing failed for {guild_id}/{server_name}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_processing_status(self, guild_id: int) -> Dict[str, Any]:
        """Get current processing status for a guild"""
        try:
            status = {
                'guild_id': guild_id,
                'active_session': guild_id in self.active_sessions,
                'servers_configured': 0,
                'historical_conflicts': 0
            }
            
            # Get guild configuration
            guild_config = await getattr(self.bot, 'cached_db_manager', self.bot.db_manager).get_guild(guild_id)
            if guild_config and guild_config.get('servers'):
                status['servers_configured'] = len(guild_config['servers'])
                
                servers = []
                for server in guild_config['servers']:
                    server['guild_id'] = guild_id
                    servers.append(server)
                
                # Check for historical processing conflicts
                if self.state_manager and servers:
                    available_servers = await self.state_manager.get_available_servers_for_killfeed(servers)
                    status['historical_conflicts'] = len(servers) - len(available_servers)
            
            return status
            
        except Exception as e:
            logger.error(f"Failed to get processing status for guild {guild_id}: {e}")
            return {
                'guild_id': guild_id,
                'error': str(e)
            }
    
    async def cleanup_unified_connections(self):
        """Cleanup unified parser connections"""
        try:
            # Cancel any active sessions
            for guild_id, processor in list(self.active_sessions.items()):
                processor.cancel()
                del self.active_sessions[guild_id]
            
            logger.info("Cleaned up scalable unified parser connections")
            
        except Exception as e:
            logger.error(f"Failed to cleanup unified connections: {e}")
    
    def get_active_sessions(self) -> Dict[int, Any]:
        """Get currently active processing sessions"""
        return {
            guild_id: {
                'guild_id': guild_id,
                'active': True
            }
            for guild_id in self.active_sessions.keys()
        }