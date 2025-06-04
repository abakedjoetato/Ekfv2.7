"""
Scalable Unified Processor - Fixed Version
Handles log parsing and event detection with proper syntax
"""

import asyncio
import asyncssh
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class ScalableUnifiedProcessor:
    """Unified processor for parsing game server logs"""

    def __init__(self, bot):
        self.bot = bot
        self.connection_patterns = self._compile_connection_patterns()
        self.event_patterns = self._compile_event_patterns()

    def _compile_connection_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for connection events - Real Deadside server format"""
        return {
            # Queue state - player joining (updated to handle password field correctly)
            'player_queue': re.compile(r'LogNet: Join request: /Game/Maps/world_[^?]*\?.*?login=([^?&]+)\?password=[^?]*\?eosid=\|([a-f0-9]+).*?Name=([^?&]+)', re.IGNORECASE),
            # Connected state - player registered (based on actual log format)
            'player_connect': re.compile(r'LogOnline: Warning: Player \|([a-f0-9]+) successfully registered!', re.IGNORECASE),
            # Disconnected state - player left (based on actual log format)
            'player_disconnect': re.compile(r'LogNet: UChannel::Close:.*?UniqueId: EOS:\|([a-f0-9]+)', re.IGNORECASE)
        }

    def _compile_event_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for game events - Based on real Deadside log format"""
        return {
            # Mission events - exact format from logs
            'mission_start': re.compile(r'LogSFPS: Mission (GA_[^_]+_[^_]+_[^_\s]+(?:_[^_\s]+)*) switched to READY', re.IGNORECASE),
            'mission_end': re.compile(r'LogSFPS: Mission (GA_[^_]+_[^_]+_[^_\s]+(?:_[^_\s]+)*) switched to WAITING', re.IGNORECASE),
            # Airdrop events - exact format from logs  
            'airdrop_flying': re.compile(r'LogSFPS: AirDrop switched to Flying', re.IGNORECASE),
            'airdrop_dropping': re.compile(r'LogSFPS: AirDrop switched to Dropping', re.IGNORECASE),
            'airdrop_dead': re.compile(r'LogSFPS: AirDrop switched to Dead', re.IGNORECASE),
            # Helicrash events (if they exist in logs)
            'helicrash_ready': re.compile(r'LogSFPS: Helicopter.*switched to READY', re.IGNORECASE),
            'helicrash_crash': re.compile(r'LogSFPS: Helicopter.*crash', re.IGNORECASE),
            # Trader events (if they exist in logs)
            'trader_arrival': re.compile(r'LogSFPS: Trader.*arrived', re.IGNORECASE),
            'trader_departure': re.compile(r'LogSFPS: Trader.*departure', re.IGNORECASE),
            # Vehicle events
            'vehicle_add': re.compile(r'LogSFPS: \[ASFPSGameMode::NewVehicle_Add\] Add vehicle.*Total (\d+)', re.IGNORECASE),
            'vehicle_del': re.compile(r'LogSFPS: \[ASFPSGameMode::DelVehicle\].*Total (\d+)', re.IGNORECASE)
        }

    def parse_log_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single log line and extract relevant information"""
        line = line.strip()
        if not line:
            return None

        try:
            # Extract timestamp
            if not line.startswith('['):
                return None

            timestamp_end = line.find(']')
            if timestamp_end == -1:
                return None

            timestamp_str = line[1:timestamp_end]
            message = line[timestamp_end + 1:].strip()

            # Parse timestamp
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y.%m.%d-%H.%M.%S:%f')
            except ValueError:
                return None

            # Check connection patterns
            for event_type, pattern in self.connection_patterns.items():
                match = pattern.search(message)
                if match:
                    if event_type == 'player_queue':
                        # Queue: login=PlayerName, eosid=PlayerID, Name=PlayerName
                        login_name = match.group(1).strip()
                        eos_id = match.group(2).strip()
                        name_field = match.group(3).strip()
                        
                        # Use best available name with fallback logic
                        resolved_name = self._resolve_player_name(login_name, name_field)
                        
                        return {
                            'timestamp': timestamp,
                            'type': 'connection',
                            'event': event_type,
                            'player_name': resolved_name,
                            'login_name': login_name,
                            'eos_id': eos_id,
                            'raw_message': message
                        }
                    elif event_type == 'player_connect':
                        # Connect: Player |EOS_ID successfully registered
                        return {
                            'timestamp': timestamp,
                            'type': 'connection',
                            'event': event_type,
                            'eos_id': match.group(1),
                            'raw_message': message
                        }
                    elif event_type == 'player_disconnect':
                        # Disconnect: UniqueId: EOS:|EOS_ID
                        return {
                            'timestamp': timestamp,
                            'type': 'connection',
                            'event': event_type,
                            'eos_id': match.group(1),
                            'raw_message': message
                        }

            # Check event patterns
            for event_type, pattern in self.event_patterns.items():
                match = pattern.search(message)
                if match:
                    # Apply advanced normalization for events (may return None for filtered missions)
                    normalized_event = self._normalize_event_data(event_type, match.groups(), timestamp, message)
                    if normalized_event is not None:
                        return normalized_event

            return None

        except Exception as e:
            logger.error(f"Error parsing log line: {e}")
            return None

    async def process_log_data(self, log_data: str, server_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process multiple log lines and return parsed events"""
        events = []
        lines = log_data.split('\n')

        logger.info(f"Processing {len(lines)} log lines from {server_config.get('name', 'Unknown')}")

        connection_count = 0
        event_count = 0

        for line in lines:
            parsed = self.parse_log_line(line)
            if parsed:
                parsed['server_name'] = server_config.get('name', 'Unknown')
                parsed['guild_id'] = server_config.get('guild_id')
                parsed['server_id'] = server_config.get('server_id', 'Unknown')
                events.append(parsed)

                if parsed['type'] == 'connection':
                    connection_count += 1
                elif parsed['type'] == 'event':
                    event_count += 1

        logger.info(f"Parsed {len(events)} total events: {connection_count} connections, {event_count} game events")

        # Log sample of first few lines for debugging
        if not events and len(lines) > 10:
            logger.info("Sample log lines for debugging:")
            for i, line in enumerate(lines[:5]):
                if line.strip():
                    logger.info(f"  Line {i}: {line[:100]}...")

        return events

    async def update_player_sessions(self, events: List[Dict[str, Any]]) -> bool:
        """Update player session states based on connection events using EOS ID tracking"""
        if not self.bot.db_manager:
            return False

        try:
            state_changes = []  # Track actual state changes for embed sending

            for event in events:
                if event['type'] != 'connection':
                    continue

                eos_id = event.get('eos_id')
                guild_id = event['guild_id']
                server_id = event['server_id']
                timestamp = event['timestamp']
                event_type = event['event']

                if not eos_id:
                    continue

                # Get current player state
                current_session = await self.bot.db_manager.player_sessions.find_one({
                    'eos_id': eos_id,
                    'guild_id': guild_id,
                    'server_id': server_id
                })

                current_state = current_session.get('state', 'offline') if current_session else 'offline'
                new_state = current_state
                player_data = {}

                if event_type == 'player_queue':
                    # Player is queuing to join
                    new_state = 'queued'
                    resolved_name = event.get('player_name', 'Unknown')
                    player_data = {
                        'eos_id': eos_id,
                        'player_name': resolved_name,
                        'login_name': event.get('login_name', 'Unknown'),
                        'character_name': resolved_name,  # For /online compatibility
                        'guild_id': guild_id,
                        'server_id': server_id,
                        'state': 'queued',
                        'queued_at': timestamp,
                        'last_seen': timestamp
                    }

                elif event_type == 'player_connect':
                    # Player successfully registered (queued -> online)
                    new_state = 'online'
                    player_data = {
                        'state': 'online',
                        'joined_at': timestamp,
                        'last_seen': timestamp
                    }

                elif event_type == 'player_disconnect':
                    # Player disconnected (online -> offline)
                    new_state = 'offline'
                    player_data = {
                        'state': 'offline',
                        'left_at': timestamp,
                        'last_seen': timestamp
                    }

                # Only update if state actually changed
                if new_state != current_state:
                    await self.bot.db_manager.player_sessions.update_one(
                        {
                            'eos_id': eos_id,
                            'guild_id': guild_id,
                            'server_id': server_id
                        },
                        {'$set': player_data},
                        upsert=True
                    )

                    # Track state change for embed sending
                    state_changes.append({
                        'eos_id': eos_id,
                        'player_name': event.get('player_name') or (current_session.get('player_name', 'Unknown') if current_session else 'Unknown'),
                        'old_state': current_state,
                        'new_state': new_state,
                        'timestamp': timestamp,
                        'guild_id': guild_id,
                        'server_id': server_id
                    })

                    logger.info(f"Player state change: {eos_id[:8]}... {current_state} -> {new_state}")

            # Send embeds for actual state changes
            if state_changes:
                await self._send_connection_embeds(state_changes)

            return True

        except Exception as e:
            logger.error(f"Failed to update player sessions: {e}")
            return False

    async def _send_connection_embeds(self, state_changes: List[Dict[str, Any]]) -> bool:
        """Send connection embeds using themed embed factory"""
        try:
            from bot.utils.channel_router import ChannelRouter
            from bot.utils.embed_factory import EmbedFactory

            channel_router = ChannelRouter(self.bot)

            for change in state_changes:
                embed = None
                channel_type = 'connections'  # Use connections channel for player events

                # Only send embeds for specific state transitions
                if change['old_state'] == 'queued' and change['new_state'] == 'online':
                    # Player connected (queued -> online)
                    embed_data = {
                        'player_name': change['player_name'],
                        'eos_id': change['eos_id'],
                        'server_name': change.get('server_name', 'Unknown'),
                        'timestamp': change.get('timestamp')
                    }
                    embed = EmbedFactory.create_player_connect_embed(embed_data)

                elif change['old_state'] == 'online' and change['new_state'] == 'offline':
                    # Player disconnected (online -> offline)
                    embed_data = {
                        'player_name': change['player_name'],
                        'eos_id': change['eos_id'],
                        'server_name': change.get('server_name', 'Unknown'),
                        'timestamp': change.get('timestamp')
                    }
                    embed = EmbedFactory.create_player_disconnect_embed(embed_data)

                if embed:
                    await channel_router.send_embed_to_channel(
                        guild_id=change['guild_id'],
                        server_id=change['server_id'],
                        channel_type=channel_type,
                        embed=embed
                    )

            return True

        except Exception as e:
            logger.error(f"Error sending connection embeds batch: {e}")
            return False

    async def send_event_embeds(self, events: List[Dict[str, Any]]) -> bool:
        """Send Discord embeds for game events using themed embed factory"""
        if not events:
            return True

        try:
            from bot.utils.channel_router import ChannelRouter
            from bot.utils.embed_factory import EmbedFactory

            channel_router = ChannelRouter(self.bot)

            for event in events:
                if event['type'] == 'event':
                    embed = await self._create_themed_embed(event)
                    if embed:
                        channel_type = self._map_event_to_channel_type(event['event'])
                        await channel_router.send_embed_to_channel(
                            guild_id=event['guild_id'],
                            server_id=event['server_id'],
                            channel_type=channel_type,
                            embed=embed
                        )

            return True

        except Exception as e:
            logger.error(f"Failed to send event embeds: {e}")
            return False

    async def _create_themed_embed(self, event: Dict[str, Any]):
        """Create themed embed using embed factory"""
        try:
            from bot.utils.embed_factory import EmbedFactory
            event_type = event['event']

            if event_type == 'mission_start':
                mission_name = event['details'][0] if event['details'] else 'Unknown Mission'
                embed_data = {
                    'mission_name': mission_name,
                    'server_name': event.get('server_name', 'Unknown'),
                    'timestamp': event.get('timestamp')
                }
                return await EmbedFactory.build_mission_embed(embed_data)

            elif event_type == 'mission_end':
                mission_name = event['details'][0] if event['details'] else 'Unknown Mission'
                embed_data = {
                    'mission_name': mission_name,
                    'state': 'WAITING',
                    'server_name': event.get('server_name', 'Unknown'),
                    'timestamp': event.get('timestamp')
                }
                return await EmbedFactory.build_mission_embed(embed_data)

            elif event_type in ['airdrop_flying', 'airdrop_dropping']:
                embed_data = {
                    'server_name': event.get('server_name', 'Unknown'),
                    'timestamp': event.get('timestamp')
                }
                return await EmbedFactory.build_airdrop_embed(embed_data)

            elif event_type in ['helicrash_ready', 'helicrash_crash']:
                embed_data = {
                    'server_name': event.get('server_name', 'Unknown'),
                    'timestamp': event.get('timestamp')
                }
                return await EmbedFactory.build_helicrash_embed(embed_data)

            elif event_type in ['trader_arrival', 'trader_departure']:
                embed_data = {
                    'trader_name': 'Trader',
                    'server_name': event.get('server_name', 'Unknown'),
                    'timestamp': event.get('timestamp')
                }
                return await EmbedFactory.build_trader_embed(embed_data)

            return None

        except Exception as e:
            logger.error(f"Error creating themed embed: {e}")
            return None

    def _map_event_to_channel_type(self, event_type: str) -> str:
        """Map event types to channel types"""
        mapping = {
            'mission_start': 'missions',
            'mission_end': 'missions',
            'airdrop_flying': 'events',
            'airdrop_dropping': 'events',
            'airdrop_dead': 'events',
            'helicrash_ready': 'events',
            'helicrash_crash': 'events',
            'trader_arrival': 'events',
            'trader_departure': 'events',
            'vehicle_add': 'events',
            'vehicle_del': 'events'
        }
        return mapping.get(event_type, 'events')

    def _normalize_event_data(self, event_type: str, match_groups: tuple, timestamp: datetime, raw_message: str) -> Optional[Dict[str, Any]]:
        """Advanced normalization for mission and event data"""
        normalized = {
            'timestamp': timestamp,
            'type': 'event',
            'event': event_type,
            'details': match_groups,
            'raw_message': raw_message
        }

        # Mission normalization with level and state filtering
        if event_type in ['mission_start', 'mission_end']:
            mission_name = match_groups[0] if match_groups else 'Unknown Mission'
            mission_level = self._extract_mission_level(mission_name)

            # Block missions below level 3
            if mission_level < 3:
                return None  # Skip low-level missions

            # Only output missions in READY state (mission_start), skip WAITING state
            if event_type == 'mission_end':
                return None  # Skip mission end events

            # Normalize mission names for consistent display
            normalized['mission_name'] = self._normalize_mission_name(mission_name)
            normalized['mission_state'] = 'READY'
            normalized['mission_level'] = mission_level

        # Airdrop normalization - only output when Flying (spawn event)
        elif event_type in ['airdrop_flying', 'airdrop_dropping', 'airdrop_dead']:
            # Only output airdrop when it starts flying (spawn event), skip other states
            if event_type != 'airdrop_flying':
                return None  # Skip dropping and dead states

            normalized['airdrop_state'] = 'FLYING'
            normalized['event_priority'] = 'high'

        # Helicrash normalization - only output when spawning/ready
        elif event_type in ['helicrash_ready', 'helicrash_crash']:
            # Only output helicrash when it becomes ready (spawn event), skip crash state
            if event_type != 'helicrash_ready':
                return None  # Skip crash events

            normalized['helicrash_state'] = 'READY'
            normalized['event_priority'] = 'high'

        # Trader normalization - only output when arriving/spawning
        elif event_type in ['trader_arrival', 'trader_departure']:
            # Only output trader when arriving (spawn event), skip departure
            if event_type != 'trader_arrival':
                return None  # Skip departure events

            normalized['trader_state'] = 'ARRIVED'
            normalized['event_priority'] = 'medium'

        # Vehicle event normalization
        elif event_type in ['vehicle_add', 'vehicle_del']:
            vehicle_count = int(match_groups[0]) if match_groups and match_groups[0].isdigit() else 0
            normalized['vehicle_count'] = vehicle_count
            normalized['vehicle_action'] = 'added' if event_type == 'vehicle_add' else 'removed'

        return normalized

    def _normalize_mission_name(self, mission_name: str) -> str:
        """Normalize mission names for consistent display"""
        # Remove GA_ prefix and convert to readable format
        if mission_name.startswith('GA_'):
            mission_name = mission_name[3:]

        # Convert underscores to spaces and capitalize
        parts = mission_name.split('_')
        normalized_parts = []

        for part in parts:
            if part.lower() == 'mis' or part.lower().startswith('mis'):
                continue  # Skip mission indicators
            if part.isdigit():
                normalized_parts.append(f"#{part}")
            else:
                normalized_parts.append(part.capitalize())

        return ' '.join(normalized_parts) if normalized_parts else mission_name

    def _extract_mission_level(self, mission_name: str) -> int:
        """Extract mission difficulty level from name"""
        # Look for numbers in mission name that indicate level
        import re
        numbers = re.findall(r'\d+', mission_name)
        if numbers:
            # Use the last number as level indicator
            return min(int(numbers[-1]), 5)  # Cap at level 5
        return 1  # Default level

    async def process_log_data_cold_start(self, server_config: Dict[str, Any], guild_id: int) -> List[Dict[str, Any]]:
        """Process all log data chronologically from beginning for cold start"""
        try:
            # Fetch all log data from server
            log_data = await self._fetch_server_logs(server_config)
            if not log_data:
                return []

            events = []
            for line in log_data.split('\n'):
                parsed = self.parse_log_line(line)
                if parsed:
                    parsed['guild_id'] = guild_id
                    parsed['server_id'] = server_config.get('server_id', 'default')
                    parsed['server_name'] = server_config.get('server_name', 'Unknown')
                    events.append(parsed)

            # Sort chronologically
            events.sort(key=lambda x: x.get('timestamp', ''))
            return events

        except Exception as e:
            logger.error(f"Error in cold start processing: {e}")
            return []

    async def process_log_data_hot_start(self, server_config: Dict[str, Any], guild_id: int, last_timestamp: Optional[str]) -> List[Dict[str, Any]]:
        """Process only new log data since last timestamp for hot start"""
        try:
            # Fetch all log data from server
            log_data = await self._fetch_server_logs(server_config)
            if not log_data:
                return []

            events = []
            for line in log_data.split('\n'):
                parsed = self.parse_log_line(line)
                if parsed:
                    # Only include events newer than last timestamp
                    if last_timestamp and parsed.get('timestamp', '') <= last_timestamp:
                        continue

                    parsed['guild_id'] = guild_id
                    parsed['server_id'] = server_config.get('server_id', 'default')
                    parsed['server_name'] = server_config.get('server_name', 'Unknown')
                    events.append(parsed)

            # Sort chronologically
            events.sort(key=lambda x: x.get('timestamp', ''))
            return events

        except Exception as e:
            logger.error(f"Error in hot start processing: {e}")
            return []

    async def update_player_sessions_cold(self, events: List[Dict[str, Any]], guild_id: int, server_id: str):
        """Update player sessions for cold start - chronological processing to determine current state"""
        try:
            # Track player states chronologically
            player_states = {}
            valid_events = 0

            # Process events chronologically to determine final states
            for event in events:
                if event.get('type') != 'connection' or not event.get('eos_id'):
                    continue

                eos_id = event.get('eos_id')
                event_type = event.get('event')
                timestamp = event.get('timestamp')

                # Initialize player if not seen before
                if eos_id not in player_states:
                    resolved_name = event.get('player_name', 'Unknown')
                    player_states[eos_id] = {
                        'eos_id': eos_id,
                        'player_name': resolved_name,
                        'login_name': event.get('login_name', 'Unknown'),
                        'character_name': resolved_name,  # For /online compatibility
                        'guild_id': guild_id,
                        'server_id': server_id,
                        'state': 'offline',
                        'last_updated': timestamp,
                        'last_seen': timestamp
                    }
                else:
                    # Update name if we get a better one
                    current_name = player_states[eos_id].get('player_name', 'Unknown')
                    new_name = event.get('player_name', 'Unknown')
                    if new_name != 'Unknown' and (current_name == 'Unknown' or len(new_name) > len(current_name)):
                        player_states[eos_id]['player_name'] = new_name
                        player_states[eos_id]['character_name'] = new_name

                # Update state based on event type
                if event_type == 'player_queue':
                    player_states[eos_id]['state'] = 'queued'
                    player_states[eos_id]['queued_at'] = timestamp
                elif event_type == 'player_connect':
                    player_states[eos_id]['state'] = 'online'
                    player_states[eos_id]['joined_at'] = timestamp
                elif event_type == 'player_disconnect':
                    player_states[eos_id]['state'] = 'offline'
                    player_states[eos_id]['left_at'] = timestamp

                player_states[eos_id]['last_seen'] = timestamp
                player_states[eos_id]['last_updated'] = timestamp
                valid_events += 1

            # Clear existing sessions for this server
            await self.bot.db_manager.player_sessions.delete_many({
                'guild_id': guild_id,
                'server_id': server_id
            })

            # Insert final states (only active players)
            active_sessions = []
            for eos_id, player_data in player_states.items():
                if player_data['state'] in ['online', 'queued']:  # Only store active players
                    active_sessions.append(player_data)

            if active_sessions:
                await self.bot.db_manager.player_sessions.insert_many(active_sessions)

            # Count final states
            online_count = sum(1 for p in player_states.values() if p['state'] == 'online')
            queued_count = sum(1 for p in player_states.values() if p['state'] == 'queued')

            logger.info(f"Cold start: Updated player sessions for {valid_events} valid events out of {len(events)} total")
            logger.info(f"Cold start: Final state - {online_count} online, {queued_count} queued players")

            return online_count, queued_count

        except Exception as e:
            logger.error(f"Error updating player sessions in cold start: {e}")
            return 0, 0

    async def send_connection_embeds_batch(self, state_changes: List[Dict]):
        """Send connection embeds using batch processing with proper EmbedFactory integration"""
        try:
            if not state_changes:
                return

            from bot.utils.embed_factory import EmbedFactory

            for change in state_changes:
                guild_id = change.get('guild_id')
                server_id = change.get('server_id')

                if change.get('event_type') == 'connect':
                    embed_data = {
                        'player_name': change.get('player_name'),
                        'platform': change.get('platform', 'PC'),
                        'server_name': change.get('server_name', 'Unknown'),
                        'guild_id': guild_id
                    }

                    # Use EmbedFactory to build connection embed
                    embed, file_attachment = await EmbedFactory.build('connection', embed_data)

                    # Use channel router to send to appropriate channel
                    if hasattr(self.bot, 'channel_router'):
                        success = await self.bot.channel_router.send_embed_to_channel(
                            guild_id, server_id, 'events', embed, file_attachment
                        )
                        if not success:
                            logger.warning(f"Failed to send connection embed for {change.get('player_name')}")

                elif change.get('event_type') == 'disconnect':
                    embed_data = {
                        'player_name': change.get('player_name'),
                        'platform': change.get('platform', 'PC'),
                        'server_name': change.get('server_name', 'Unknown'),
                        'guild_id': guild_id
                    }

                    # Use EmbedFactory to build disconnection embed
                    embed, file_attachment = await EmbedFactory.build('disconnection', embed_data)

                    # Use channel router to send to appropriate channel
                    if hasattr(self.bot, 'channel_router'):
                        success = await self.bot.channel_router.send_embed_to_channel(
                            guild_id, server_id, 'events', embed, file_attachment
                        )
                        if not success:
                            logger.warning(f"Failed to send disconnection embed for {change.get('player_name')}")

        except Exception as e:
            logger.error(f"Error sending connection embeds batch: {e}")

    async def send_event_embeds_batch(self, game_events: List[Dict]):
        """Send game event embeds using batch processing with proper EmbedFactory integration"""
        try:
            if not game_events:
                return

            from bot.utils.embed_factory import EmbedFactory

            for event in game_events:
                guild_id = event.get('guild_id')
                server_id = event.get('server_id')
                event_type = event.get('event')

                if event_type == 'mission_start':
                    embed_data = {
                        'mission_id': event.get('mission_id', 'Unknown'),
                        'state': 'READY',
                        'level': event.get('level', 1),
                        'guild_id': guild_id
                    }

                    # Use EmbedFactory to build mission embed
                    embed, file_attachment = await EmbedFactory.build('mission', embed_data)

                    # Use channel router to send to missions channel
                    if hasattr(self.bot, 'channel_router'):
                        success = await self.bot.channel_router.send_embed_to_channel(
                            guild_id, server_id, 'missions', embed, file_attachment
                        )
                        if not success:
                            logger.warning(f"Failed to send mission embed for {event.get('mission_id')}")

                elif event_type == 'airdrop':
                    embed_data = {
                        'guild_id': guild_id
                    }

                    # Use EmbedFactory to build airdrop embed
                    embed, file_attachment = await EmbedFactory.build('airdrop', embed_data)

                    # Use channel router to send to airdrop channel
                    if hasattr(self.bot, 'channel_router'):
                        success = await self.bot.channel_router.send_embed_to_channel(
                            guild_id, server_id, 'airdrop', embed, file_attachment
                        )
                        if not success:
                            logger.warning(f"Failed to send airdrop embed")

                elif event_type == 'helicrash':
                    embed_data = {
                        'guild_id': guild_id
                    }

                    # Use EmbedFactory to build helicrash embed
                    embed, file_attachment = await EmbedFactory.build('helicrash', embed_data)

                    # Use channel router to send to helicrash channel
                    if hasattr(self.bot, 'channel_router'):
                        success = await self.bot.channel_router.send_embed_to_channel(
                            guild_id, server_id, 'helicrash', embed, file_attachment
                        )
                        if not success:
                            logger.warning(f"Failed to send helicrash embed")

                elif event_type == 'trader':
                    embed_data = {
                        'guild_id': guild_id
                    }

                    # Use EmbedFactory to build trader embed
                    embed, file_attachment = await EmbedFactory.build('trader', embed_data)

                    # Use channel router to send to trader channel
                    if hasattr(self.bot, 'channel_router'):
                        success = await self.bot.channel_router.send_embed_to_channel(
                            guild_id, server_id, 'trader', embed, file_attachment
                        )
                        if not success:
                            logger.warning(f"Failed to send trader embed")

        except Exception as e:
            logger.error(f"Error sending event embeds batch: {e}")

    async def _create_event_embed(self, event: Dict[str, Any]) -> Optional[tuple]:
        """Create professional Discord embed using embed factory"""
        try:
            from bot.utils.embed_factory import EmbedFactory

            event_type = event.get('event')

            if event_type in ['mission_start', 'mission_ready']:
                embed_data = {
                    'mission_id': event.get('mission_name', event.get('mission_id', 'Unknown')),
                    'state': 'READY',
                    'level': event.get('level', 1),
                    'server_name': event.get('server_name', 'Unknown'),
                    'timestamp': event.get('timestamp')
                }
                return await EmbedFactory.build_mission_embed(embed_data)

            elif event_type in ['mission_end', 'mission_complete']:
                embed_data = {
                    'mission_id': event.get('mission_name', event.get('mission_id', 'Unknown')),
                    'state': 'COMPLETE',
                    'level': event.get('level', 1),
                    'server_name': event.get('server_name', 'Unknown'),
                    'timestamp': event.get('timestamp')
                }
                return await EmbedFactory.build_mission_embed(embed_data)

            elif event_type == 'airdrop':
                embed_data = {
                    'server_name': event.get('server_name', 'Unknown'),
                    'location': event.get('location', 'Unknown'),
                    'timestamp': event.get('timestamp')
                }
                return await EmbedFactory.build_airdrop_embed(embed_data)

            elif event_type == 'helicrash':
                embed_data = {
                    'server_name': event.get('server_name', 'Unknown'),
                    'location': event.get('location', 'Unknown'),
                    'timestamp': event.get('timestamp')
                }
                return await EmbedFactory.build_helicrash_embed(embed_data)

            elif event_type == 'trader':
                embed_data = {
                    'trader_name': event.get('trader_name', 'Unknown Trader'),
                    'server_name': event.get('server_name', 'Unknown'),
                    'timestamp': event.get('timestamp')
                }
                return await EmbedFactory.build_trader_embed(embed_data)

            else:
                return None

        except Exception as e:
            logger.error(f"Error creating event embed with factory: {e}")
            return None

    def _get_channel_type_for_event(self, event_type: str) -> str:
        """Get appropriate channel type for event"""
        if event_type in ['mission_start', 'mission_end']:
            return 'missions'
        elif event_type == 'airdrop':
            return 'events'
        else:
            return 'events'

    async def _update_single_player_session(self, event: Dict[str, Any], send_embeds: bool = True):
        """Update a single player session based on connection event"""
        try:
            from datetime import timezone

            eos_id = event.get('eos_id')
            guild_id = event.get('guild_id')
            server_id = event.get('server_id')

            # Skip events with missing critical data to prevent database errors
            if not eos_id or not guild_id or not server_id:
                logger.debug(f"Skipping event with missing data: eos_id={eos_id}, guild_id={guild_id}, server_id={server_id}")
                return

            event_type = event.get('event')

            if event_type == 'player_queue':
                # Player joined queue
                await self.bot.db_manager.player_sessions.update_one(
                    {'eos_id': eos_id, 'guild_id': event['guild_id'], 'server_id': event['server_id']},
                    {
                        '$set': {
                            'state': 'queued',
                            'player_name': event.get('player_name', 'Unknown'),
                            'last_updated': datetime.now(timezone.utc)
                        }
                    },
                    upsert=True
                )

            elif event_type == 'player_connect':
                # Player connected
                await self.bot.db_manager.player_sessions.update_one(
                    {'eos_id': eos_id, 'guild_id': event['guild_id'], 'server_id': event['server_id']},
                    {
                        '$set': {
                            'state': 'online',
                            'last_updated': datetime.now(timezone.utc)
                        }
                    }
                )

            elif event_type == 'player_disconnect':
                # Player disconnected
                await self.bot.db_manager.player_sessions.update_one(
                    {'eos_id': eos_id, 'guild_id': event['guild_id'], 'server_id': event['server_id']},
                    {
                        '$set': {
                            'state': 'offline',
                            'last_updated': datetime.now(timezone.utc)
                        }
                    }
                )

        except Exception as e:
            # Skip duplicate key errors silently during cold start processing
            if "duplicate key error" not in str(e):
                logger.error(f"Error updating player session: {e}")

    def _resolve_player_name(self, login_name: str, name_field: str) -> str:
        """Resolve the best player name from available fields with validation"""
        try:
            import urllib.parse
            
            # Decode URL-encoded names
            def decode_name(name):
                try:
                    return urllib.parse.unquote_plus(name) if name else ""
                except:
                    return name or ""
            
            decoded_login = decode_name(login_name)
            decoded_name = decode_name(name_field)
            
            # Validation function
            def is_valid_name(name):
                if not name or len(name) < 2 or len(name) > 32:
                    return False
                # Reject numeric-only names
                if name.replace('.', '').replace('-', '').isdigit():
                    return False
                # Must contain at least one letter
                if not any(c.isalpha() for c in name):
                    return False
                return True
            
            # Priority: Name field first, then login field
            if is_valid_name(decoded_name):
                return decoded_name
            elif is_valid_name(decoded_login):
                return decoded_login
            elif decoded_name:
                return decoded_name
            elif decoded_login:
                return decoded_login
            else:
                return "Unknown"
                
        except Exception as e:
            logger.debug(f"Name resolution failed: {e}")
            return name_field or login_name or "Unknown"

    async def _fetch_server_logs(self, server_config: Dict[str, Any]) -> str:
        """Fetch log data from server via SFTP using robust connection strategies"""
        try:
            import asyncssh
            from bot.utils.connection_pool import connection_manager

            # Priority order for SSH credentials:
            # 1. sftp_credentials (preferred)
            # 2. individual ssh_* fields
            # 3. legacy host/username/password fields

            sftp_creds = server_config.get('sftp_credentials', {})
            if sftp_creds:
                ssh_host = sftp_creds.get('host', '').strip()
                ssh_username = sftp_creds.get('username')
                ssh_password = sftp_creds.get('password')
                ssh_port = sftp_creds.get('port', 22)
            else:
                # Fallback to individual fields
                ssh_host = server_config.get('ssh_host') or server_config.get('host')
                ssh_username = server_config.get('ssh_username') or server_config.get('username')
                ssh_password = server_config.get('ssh_password') or server_config.get('password')
                ssh_port = server_config.get('ssh_port') or server_config.get('port', 22)

            if not all([ssh_host, ssh_username, ssh_password]):
                logger.error(f"Server {server_config.get('server_name', 'Unknown')} missing SSH credentials in database")
                return ""

            # Build dynamic log path: ./{host}_{_id}/Logs/Deadside.log
            server_id = server_config.get('_id') or server_config.get('server_id')
            log_path = f"./{ssh_host}_{server_id}/Logs/Deadside.log"

            logger.info(f"Connecting to {ssh_host}:{ssh_port} as {ssh_username} for {server_config.get('server_name', 'Unknown')}")
            logger.info(f"Using dynamic log path: {log_path}")

            # Create connection config for the robust connection manager
            connection_config = {
                'host': ssh_host,
                'port': ssh_port,
                'username': ssh_username,
                'password': ssh_password
            }

            # Use the same robust connection manager as killfeed parser
            guild_id = server_config.get('guild_id', 1219706687980568769)
            async with connection_manager.get_connection(guild_id, connection_config) as conn:
                async with conn.start_sftp_client() as sftp:
                    # Read the log file
                    try:
                        async with sftp.open(log_path, 'r') as f:
                            log_data = await f.read()
                            return log_data
                    except Exception as e:
                        logger.error(f"Failed to read log file {log_path}: {e}")
                        return ""

        except Exception as e:
            logger.error(f"Error fetching server logs: {e}")
            return ""