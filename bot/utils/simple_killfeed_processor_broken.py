"""
Simple Killfeed Processor
Based on historical parser's proven CSV discovery and processing approach
Maintains state instead of clearing it like historical parser does
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from bot.utils.connection_pool import GlobalConnectionManager, connection_manager

logger = logging.getLogger(__name__)

@dataclass 
class KillfeedState:
    """Simple killfeed parser state"""
    last_file: str = ""
    last_line: int = 0
    last_byte_position: int = 0
    file_timestamp: str = ""

@dataclass
class KillfeedEvent:
    """Represents a single killfeed event"""
    timestamp: datetime
    killer: str
    victim: str
    weapon: str
    distance: int
    killer_platform: str
    victim_platform: str
    raw_line: str
    line_number: int
    filename: str

class SimpleKillfeedProcessor:
    """Simple killfeed processor that copies historical parser's working approach"""
    
    def __init__(self, guild_id: int, server_config: Dict[str, Any], bot=None):
        self.guild_id = guild_id
        self.server_config = server_config
        self.server_name = server_config.get('name', 'Unknown')
        self.state = KillfeedState()
        self.bot = bot
        self.cancelled = False
        
    def _get_killfeed_path(self) -> str:
        """Get the killfeed path for this server"""
        server_id = self.server_config.get('server_id', self.server_config.get('_id', 'unknown'))
        return f"/home/ds{server_id}/killfeed/"
    
    async def process_server_killfeed(self, progress_callback=None) -> Dict[str, Any]:
        """Main entry point for killfeed processing"""
        results = {
            'success': False,
            'events_found': 0,
            'lines_processed': 0,
            'newest_file': None,
            'file_transition': False,
            'error': None
        }
        
        try:
            # Register processing session
            if self.state_manager:
                await self.state_manager.register_session(self.guild_id, self.server_name, 'killfeed')
            
            # Get current state
            current_state = None
            if self.state_manager:
                current_state = await self.state_manager.get_parser_state(
                    self.guild_id, self.server_name
                )
            
            # Discover newest CSV file using historical parser's proven method
            newest_file_path = await self._discover_newest_csv_file()
            if not newest_file_path:
                logger.warning(f"No CSV files found for {self.server_name}")
                results['error'] = "No CSV files found"
                return results
            
            # Extract just filename from full path
            import os
            newest_file = os.path.basename(newest_file_path)
            results['newest_file'] = newest_file
            
            all_events = []
            
            # Check if we need to handle file transition
            if current_state and current_state.last_file and current_state.last_file != newest_file:
                logger.info(f"File transition detected: {current_state.last_file} -> {newest_file}")
                results['file_transition'] = True
                
                # First, finish processing the previous file
                previous_events = await self._finish_previous_file(current_state)
                all_events.extend(previous_events)
                
                # Then start processing the new file from beginning
                new_events = await self._process_csv_file(newest_file_path, None)
                all_events.extend(new_events)
            else:
                # Normal processing - continue from last known position
                events = await self._process_csv_file(newest_file_path, current_state)
                all_events.extend(events)
            
            results['events_found'] = len(all_events)
            results['success'] = True
            
            # Send events to Discord
            if all_events:
                logger.info(f"Delivering {len(all_events)} killfeed events to Discord")
                await self._deliver_killfeed_events(all_events)
            else:
                logger.warning("No killfeed events found to deliver")
            
        except Exception as e:
            logger.error(f"Killfeed processing failed for {self.server_name}: {e}")
            results['error'] = str(e)
        
        return results
    
    async def _finish_previous_file(self, current_state: KillfeedState) -> List[KillfeedEvent]:
        """Finish processing the previous file from last known position"""
        events = []
        
        try:
            # Construct path to previous file
            killfeed_path = self._get_killfeed_path()
            previous_file_path = f"{killfeed_path}world_0/{current_state.last_file}"
            
            logger.info(f"Finishing previous file: {current_state.last_file} from line {current_state.last_line}")
            
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                if not conn:
                    return events
                
                sftp = await conn.start_sftp_client()
                
                # Check if previous file still exists
                try:
                    await sftp.stat(previous_file_path)
                except:
                    logger.warning(f"Previous file {current_state.last_file} no longer exists")
                    return events
                
                # Read from last known position to end of file
                async with sftp.open(previous_file_path, 'rb') as file:
                    await file.seek(current_state.last_byte_position)
                    remaining_content = await file.read()
                    
                    if remaining_content:
                        lines = remaining_content.decode('utf-8', errors='ignore').splitlines()
                        
                        # Process remaining lines
                        for i, line in enumerate(lines):
                            if self.cancelled:
                                break
                            
                            line = line.strip()
                            if not line:
                                continue
                            
                            event = self._parse_killfeed_line(line, current_state.last_line + i, current_state.last_file)
                            if event:
                                events.append(event)
                        
                        # Update state to reflect completion of previous file
                        if self.state_manager and lines:
                            final_line = current_state.last_line + len(lines)
                            final_byte = current_state.last_byte_position + len(remaining_content)
                            
                            await self.state_manager.update_parser_state(
                                self.guild_id, self.server_name,
                                current_state.last_file, final_line, final_byte,
                                'killfeed', current_state.file_timestamp
                            )
                            
                            logger.info(f"Completed previous file: {current_state.last_file} - {len(events)} new events")
                
        except Exception as e:
            logger.error(f"Failed to finish previous file {current_state.last_file}: {e}")
        
        return events
    
    async def _discover_newest_csv_file(self) -> Optional[str]:
        """Discover newest CSV file using historical parser's proven glob method"""
        try:
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                if not conn:
                    return None
                
                sftp = await conn.start_sftp_client()
                killfeed_path = self._get_killfeed_path()
                
                # Use historical parser's proven glob pattern
                pattern = f"{killfeed_path}**/*.csv"
                logger.info(f"Discovering CSV files with pattern: {pattern}")
                
                paths = await sftp.glob(pattern)
                logger.info(f"Found {len(paths)} CSV files")
                
                if not paths:
                    return None
                
                # Get file stats and find newest by modification time
                newest_file = None
                newest_mtime = 0
                
                for path in paths:
                    try:
                        stat_result = await sftp.stat(path)
                        mtime = getattr(stat_result, 'mtime', 0)
                        if mtime > newest_mtime:
                            newest_mtime = mtime
                            newest_file = path
                    except Exception as e:
                        logger.warning(f"Failed to stat {path}: {e}")
                
                if newest_file:
                    logger.info(f"Newest CSV file: {newest_file}")
                
                return newest_file
                
        except Exception as e:
            logger.error(f"Failed to discover CSV files: {e}")
            return None
    
    async def _process_csv_file(self, file_path: str, current_state: Optional[ParserState]) -> List[KillfeedEvent]:
        """Process CSV file from last known position"""
        events = []
        
        try:
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                if not conn:
                    return events
                
                sftp = await conn.start_sftp_client()
                
                # Get filename for state tracking
                import os
                filename = os.path.basename(file_path)
                
                # Determine starting position
                start_line = 0
                start_byte = 0
                
                if current_state and current_state.last_file == filename:
                    # Continue from last known position
                    start_line = current_state.last_line
                    start_byte = current_state.last_byte_position
                    logger.info(f"Resuming from line {start_line}, byte {start_byte} in {filename}")
                else:
                    # New file or first run - start from beginning
                    logger.info(f"Processing {filename} from beginning")
                
                # Read file content from starting position
                async with sftp.open(file_path, 'rb') as file:
                    if start_byte > 0:
                        await file.seek(start_byte)
                    
                    content = await file.read()
                    
                    if content:
                        lines = content.decode('utf-8', errors='ignore').splitlines()
                        
                        # Process each line
                        logger.info(f"Processing {len(lines)} lines from {filename}")
                        for i, line in enumerate(lines):
                            if self.cancelled:
                                break
                            
                            line = line.strip()
                            if not line:
                                continue
                            
                            # Debug: Log ALL lines to understand what we're processing
                            logger.info(f"Line {i+1}: '{line}'")
                            
                            # Parse killfeed line
                            event = self._parse_killfeed_line(line, start_line + i, filename)
                            if event:
                                events.append(event)
                                logger.info(f"✅ Found killfeed event: {event.killer} killed {event.victim} with {event.weapon}")
                            else:
                                # Show detailed parsing failure for every line
                                parts_semicolon = line.split(';')
                                logger.warning(f"❌ Failed to parse line {i+1} (semicolon split: {len(parts_semicolon)} parts): '{line}'")
                        
                        # Update state
                        if self.state_manager and lines:
                            new_line_count = start_line + len(lines)
                            new_byte_position = start_byte + len(content)
                            
                            # Extract timestamp from filename for state
                            file_timestamp = self._extract_timestamp_from_filename(filename)
                            
                            await self.state_manager.update_parser_state(
                                self.guild_id, self.server_name,
                                filename, new_line_count, new_byte_position,
                                'killfeed', file_timestamp or ""
                            )
                            
                            logger.info(f"Updated state: {filename} - line {new_line_count}, byte {new_byte_position}")
                
        except Exception as e:
            logger.error(f"Failed to process CSV file {file_path}: {e}")
        
        return events
    
    def _parse_killfeed_line(self, line: str, line_number: int, filename: str) -> Optional[KillfeedEvent]:
        """Parse a single killfeed CSV line using historical parser's exact logic"""
        try:
            # Use historical parser's exact CSV parsing logic - but handle 10 columns
            parts = line.strip().split(';')
            if len(parts) < 9:  # Need at least 9 columns for the core data
                return None
                
            timestamp_str = parts[0].strip()
            killer = parts[1].strip()
            killer_id = parts[2].strip()
            victim = parts[3].strip()
            victim_id = parts[4].strip()
            weapon = parts[5].strip()
            distance = parts[6].strip() if len(parts) > 6 else '0'

            killer = killer.strip()
            victim = victim.strip()

            # Parse timestamp - handle multiple formats (from historical parser)
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y.%m.%d-%H.%M.%S')
                timestamp = timestamp.replace(tzinfo=timezone.utc)
            except ValueError:
                try:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                except ValueError:
                    timestamp = datetime.utcnow().replace(tzinfo=timezone.utc)

            # Parse distance (from historical parser)
            try:
                if distance and distance != '':
                    distance_float = float(distance)
                else:
                    distance_float = 0.0
            except ValueError:
                distance_float = 0.0

            # Get platform info if available (8th and 9th columns)
            killer_platform = parts[7].strip() if len(parts) > 7 else ""
            victim_platform = parts[8].strip() if len(parts) > 8 else ""

            return KillfeedEvent(
                timestamp=timestamp,
                killer=killer,
                victim=victim,
                weapon=weapon,
                distance=int(distance_float),
                killer_platform=killer_platform,
                victim_platform=victim_platform,
                raw_line=line,
                line_number=line_number,
                filename=filename
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse killfeed line {line_number}: {e}")
        
        return None
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from killfeed data"""
        try:
            # Common timestamp formats in killfeed data
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y/%m/%d %H:%M:%S',
                '%d/%m/%Y %H:%M:%S',
                '%Y-%m-%d %H:%M:%S.%f',
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            
            logger.debug(f"Could not parse timestamp: {timestamp_str}")
            return None
            
        except Exception as e:
            logger.debug(f"Timestamp parsing error: {e}")
            return None
    
    def _extract_timestamp_from_filename(self, filename: str) -> Optional[str]:
        """Extract timestamp from killfeed filename"""
        try:
            # Pattern: YYYY.MM.DD-HH.MM.SS.csv
            pattern = r'(\d{4}\.\d{2}\.\d{2}-\d{2}\.\d{2}\.\d{2})'
            match = re.search(pattern, filename)
            if match:
                return match.group(1)
            
            # Fallback patterns
            patterns = [
                r'(\d{4}-\d{2}-\d{2})',
                r'(\d{4}_\d{2}_\d{2})',
                r'(\d{8})',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, filename)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract timestamp from filename {filename}: {e}")
            return None
    
    async def _deliver_killfeed_events(self, events: List[KillfeedEvent]):
        """Deliver killfeed events to Discord channels"""
        try:
            logger.info(f"Starting delivery of {len(events)} killfeed events")
            logger.info(f"Bot instance check: {self.bot is not None} (type: {type(self.bot).__name__ if self.bot else 'None'})")
            
            if not self.bot:
                logger.error("CRITICAL: No bot instance available for killfeed delivery")
                return
                
            # Get killfeed channel directly from database
            guild_config = await self.bot.db_manager.get_guild(self.guild_id)
            if not guild_config:
                logger.warning(f"No guild config found for guild {self.guild_id}")
                return

            server_channels = guild_config.get('server_channels', {})
            channel_id = None
            
            # Try server-specific channel first
            if self.server_name in server_channels:
                channel_id = server_channels[self.server_name].get('killfeed')
            
            # Fall back to default server channel
            if not channel_id and 'default' in server_channels:
                channel_id = server_channels['default'].get('killfeed')
            
            # Legacy fallback to old channel structure
            if not channel_id:
                legacy_channels = guild_config.get('channels', {})
                channel_id = legacy_channels.get('killfeed')
            
            if not channel_id:
                logger.warning(f"No killfeed channel configured for {self.server_name}")
                return
            
            # Get Discord channel
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"Killfeed channel {channel_id} not found")
                return
            
            # Send events to channel
            for event in events:
                try:
                    # Create killfeed embed
                    embed = await self._create_killfeed_embed(event)
                    
                    # Send directly to channel
                    await channel.send(embed=embed)
                    logger.info(f"✅ Delivered killfeed event: {event.killer} killed {event.victim} with {event.weapon}")
                    
                except Exception as e:
                    logger.error(f"Failed to send killfeed event: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to deliver killfeed events: {e}")
    
    async def _create_killfeed_embed(self, event: KillfeedEvent):
        """Create Discord embed for killfeed event"""
        try:
            import discord
            
            # Determine embed color based on weapon or event type
            color = 0xFF0000  # Red for kills
            
            embed = discord.Embed(
                title="💀 Player Eliminated",
                color=color,
                timestamp=event.timestamp
            )
            
            embed.add_field(
                name="Killer",
                value=f"**{event.killer}**\n*{event.killer_platform}*",
                inline=True
            )
            
            embed.add_field(
                name="Victim", 
                value=f"**{event.victim}**\n*{event.victim_platform}*",
                inline=True
            )
            
            embed.add_field(
                name="Weapon",
                value=f"**{event.weapon}**\n*{event.distance}m*",
                inline=True
            )
            
            embed.set_footer(text=f"{self.server_name} • {event.filename}")
            
            return embed
            
        except Exception as e:
            logger.error(f"Failed to create killfeed embed: {e}")
            import discord
            return discord.Embed(
                title="💀 Killfeed Event",
                description=f"{event.killer} eliminated {event.victim}",
                color=0xFF0000
            )
    
    def cancel(self):
        """Cancel the processing"""
        self.cancelled = True

class MultiServerSimpleKillfeedProcessor:
    """Process killfeed for multiple servers using simple approach"""
    
    def __init__(self, guild_id: int, bot=None):
        self.guild_id = guild_id
        self.bot = bot
    
    async def process_available_servers(self, server_configs: List[Dict[str, Any]], 
                                      progress_callback=None) -> Dict[str, Any]:
        """Process all available servers for killfeed updates"""
        results = {
            'total_servers': len(server_configs),
            'processed_servers': 0,
            'failed_servers': 0,
            'total_events': 0,
            'server_results': {}
        }
        
        for server_config in server_configs:
            server_name = server_config.get('name', 'Unknown')
            
            try:
                processor = SimpleKillfeedProcessor(self.guild_id, server_config, self.bot)
                server_result = await processor.process_server_killfeed(progress_callback)
                
                results['server_results'][server_name] = server_result
                
                if server_result['success']:
                    results['processed_servers'] += 1
                    results['total_events'] += server_result['events_found']
                else:
                    results['failed_servers'] += 1
                
                logger.info(f"Killfeed processing complete for {server_name}: "
                           f"{server_result['events_found']} events")
                
            except Exception as e:
                logger.error(f"Failed to process killfeed for {server_name}: {e}")
                results['failed_servers'] += 1
                results['server_results'][server_name] = {
                    'success': False,
                    'error': str(e)
                }
        
        return results