"""
Chronological Data Processing Engine
Handles three-phase processing: Discovery -> Cache -> Chronological Processing
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, NamedTuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
import re
from bot.utils.connection_pool import connection_manager

logger = logging.getLogger(__name__)

@dataclass
class KillRecord:
    """Represents a single kill record with parsed timestamp"""
    timestamp: datetime
    raw_line: str
    killer: str
    victim: str
    weapon: str
    distance: int
    killer_platform: str
    victim_platform: str
    file_source: str

class ProcessingPhase:
    """Tracks processing phase status"""
    DISCOVERY = "discovery"
    CACHING = "caching"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"

@dataclass
class ProcessingStats:
    """Statistics for processing session"""
    phase: str = ProcessingPhase.DISCOVERY
    files_discovered: int = 0
    files_cached: int = 0
    total_lines: int = 0
    valid_kills: int = 0
    processed_kills: int = 0
    start_time: Optional[datetime] = None
    current_file: str = ""
    errors: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.start_time is None:
            self.start_time = datetime.now(timezone.utc)

class ChronologicalProcessor:
    """Manages chronological processing for a single server"""
    
    def __init__(self, guild_id: int, server_config: Dict[str, Any], db_manager=None):
        self.guild_id = guild_id
        self.server_config = server_config
        self.server_id = str(server_config.get('_id', 'unknown'))
        self.db_manager = db_manager
        self.stats = ProcessingStats()
        self.kill_cache: List[KillRecord] = []
        self._cancelled = False
        
    async def process_server_data(self, progress_callback=None) -> Dict[str, Any]:
        """Main entry point for three-phase processing"""
        try:
            # Phase 0: Clear existing data for this server (historical processing only)
            if self.db_manager:
                await self._clear_existing_server_data()
            
            # Phase 1: File Discovery
            self.stats.phase = ProcessingPhase.DISCOVERY
            if progress_callback:
                await progress_callback(self.stats)
                
            file_paths = await self._discover_csv_files()
            self.stats.files_discovered = len(file_paths)
            
            if not file_paths:
                self.stats.phase = ProcessingPhase.FAILED
                self.stats.errors.append("No CSV files found")
                return self._get_results()
            
            # Phase 2: Content Caching
            self.stats.phase = ProcessingPhase.CACHING
            if progress_callback:
                await progress_callback(self.stats)
                
            await self._cache_all_content(file_paths, progress_callback)
            
            if self._cancelled:
                return self._get_results()
            
            # Phase 3: Chronological Processing
            self.stats.phase = ProcessingPhase.PROCESSING
            if progress_callback:
                await progress_callback(self.stats)
                
            await self._process_chronologically(progress_callback)
            
            self.stats.phase = ProcessingPhase.COMPLETE
            return self._get_results()
            
        except Exception as e:
            self.stats.phase = ProcessingPhase.FAILED
            self.stats.errors.append(f"Processing failed: {str(e)}")
            logger.error(f"Server processing failed for {self.server_id}: {e}")
            return self._get_results()
    
    async def _discover_csv_files(self) -> List[str]:
        """Phase 1: Discover all CSV files for the server"""
        file_paths = []
        
        try:
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                sftp = await conn.start_sftp_client()
                
                server_id = self.server_id
                sftp_host = self.server_config.get('host')
                remote_path = f"./{sftp_host}_{server_id}/actual1/deathlogs/"
                
                pattern = f"{remote_path}**/*.csv"
                logger.info(f"Discovering CSV files with pattern: {pattern}")
                
                try:
                    paths = await sftp.glob(pattern)
                    logger.info(f"Discovered {len(paths)} CSV files for server {server_id}")
                    
                    # Sort by path to get rough chronological order
                    file_paths = sorted(paths)
                    
                except Exception as e:
                    logger.error(f"Failed to discover files: {e}")
                    self.stats.errors.append(f"File discovery failed: {str(e)}")
                
                sftp.exit()
                
        except Exception as e:
            logger.error(f"Connection failed during discovery: {e}")
            self.stats.errors.append(f"Connection failed: {str(e)}")
        
        return file_paths
    
    async def _cache_all_content(self, file_paths: List[str], progress_callback=None):
        """Phase 2: Cache all CSV content and parse kill records"""
        self.kill_cache = []
        
        for i, file_path in enumerate(file_paths):
            if self._cancelled:
                break
                
            self.stats.current_file = file_path.split('/')[-1]
            
            try:
                kill_records = await self._process_single_file(file_path)
                self.kill_cache.extend(kill_records)
                self.stats.files_cached += 1
                self.stats.total_lines += len(kill_records)
                
                if progress_callback and i % 10 == 0:  # Update every 10 files
                    await progress_callback(self.stats)
                    
            except Exception as e:
                error_msg = f"Failed to cache {file_path}: {str(e)}"
                self.stats.errors.append(error_msg)
                logger.error(error_msg)
        
        # Sort all cached records chronologically
        self.kill_cache.sort(key=lambda x: x.timestamp)
        self.stats.valid_kills = len(self.kill_cache)
        
        logger.info(f"Cached {len(self.kill_cache)} kill records in chronological order for server {self.server_id}")
    
    async def _process_single_file(self, file_path: str) -> List[KillRecord]:
        """Process a single CSV file and extract kill records"""
        kill_records = []
        
        try:
            async with connection_manager.get_connection(self.guild_id, self.server_config) as conn:
                sftp = await conn.start_sftp_client()
                
                # Read file content
                async with sftp.open(file_path, 'r') as file:
                    content = await file.read()
                
                sftp.exit()
                
                # Parse lines into kill records
                lines = content.strip().split('\n')
                for line in lines:
                    if line.strip():
                        kill_record = self._parse_kill_line(line, file_path)
                        if kill_record:
                            kill_records.append(kill_record)
                
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            raise
        
        return kill_records
    
    def _parse_kill_line(self, line: str, file_source: str) -> Optional[KillRecord]:
        """Parse a CSV line into a KillRecord"""
        try:
            parts = line.split(';')
            if len(parts) < 8:
                return None
            
            # Parse timestamp from first part
            timestamp_str = parts[0]
            timestamp = self._parse_timestamp(timestamp_str)
            if not timestamp:
                return None
            
            return KillRecord(
                timestamp=timestamp,
                raw_line=line,
                killer=parts[1] if len(parts) > 1 else "",
                victim=parts[3] if len(parts) > 3 else "",
                weapon=parts[5] if len(parts) > 5 else "",
                distance=int(parts[6]) if len(parts) > 6 and parts[6].isdigit() else 0,
                killer_platform=parts[7] if len(parts) > 7 else "",
                victim_platform=parts[8] if len(parts) > 8 else "",
                file_source=file_source.split('/')[-1]
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse kill line: {line} - {e}")
            return None
    
    def _parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp from various formats"""
        try:
            # Try common formats
            formats = [
                "%Y.%m.%d-%H.%M.%S",
                "%Y-%m-%d-%H.%M.%S",
                "%Y.%m.%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S"
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(timestamp_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
                    
            return None
            
        except Exception:
            return None
    
    async def _process_chronologically(self, progress_callback=None):
        """Phase 3: Process all cached records in chronological order"""
        batch_size = 250  # Optimized for hybrid processing efficiency
        processed = 0
        
        for i in range(0, len(self.kill_cache), batch_size):
            if self._cancelled:
                break
                
            batch = self.kill_cache[i:i + batch_size]
            
            # Process batch of chronologically ordered kills
            await self._process_kill_batch(batch)
            
            processed += len(batch)
            self.stats.processed_kills = processed
            
            if progress_callback and i % (batch_size * 10) == 0:  # Update every 1000 records
                await progress_callback(self.stats)
        
        logger.info(f"Processed {processed} kills chronologically for server {self.server_id}")
    
    async def _process_kill_batch(self, kill_batch: List[KillRecord]):
        """Process a batch of chronologically ordered kills with hybrid bulk + sequential operations"""
        valid_records = 0
        skipped_records = 0
        
        try:
            # Phase 1: Bulk operations for simple statistics
            kill_events_to_insert = []
            simple_stats = {}  # {player_name: {kills: int, deaths: int, suicides: int, distance_sum: int}}
            
            # Phase 2: Sequential processing for state-dependent statistics
            player_states = {}  # {player_name: {current_streak: int, best_streak: int, last_event: str}}
            
            processed_at = datetime.now(timezone.utc)
            
            # Build bulk data and process chronologically for streaks
            for kill_record in kill_batch:
                # Validate player names before processing
                killer_valid = kill_record.killer and kill_record.killer.strip()
                victim_valid = kill_record.victim and kill_record.victim.strip()
                
                if not killer_valid or not victim_valid:
                    skipped_records += 1
                    continue
                
                killer_name = kill_record.killer.strip()
                victim_name = kill_record.victim.strip()
                is_suicide = killer_name.lower() == victim_name.lower()
                
                # Validate and parse distance
                try:
                    distance = int(kill_record.distance) if kill_record.distance else 0
                    if distance < 0 or distance > 50000:  # Sanity check: max 50km shots
                        distance = 0
                except (ValueError, TypeError):
                    distance = 0
                
                # Prepare kill event for bulk insert
                kill_event = {
                    'guild_id': self.guild_id,
                    'server_id': self.server_id,
                    'killer': killer_name,
                    'victim': victim_name,
                    'weapon': kill_record.weapon or 'Unknown',
                    'distance': distance,
                    'killer_platform': kill_record.killer_platform or 'Unknown',
                    'victim_platform': kill_record.victim_platform or 'Unknown',
                    'timestamp': kill_record.timestamp,
                    'file_source': kill_record.file_source,
                    'is_suicide': is_suicide,
                    'processed_at': processed_at
                }
                kill_events_to_insert.append(kill_event)
                
                # Phase 1: Aggregate simple statistics
                if is_suicide:
                    # Track suicides separately
                    if killer_name not in simple_stats:
                        simple_stats[killer_name] = {'kills': 0, 'deaths': 0, 'suicides': 0, 'distance_sum': 0}
                    simple_stats[killer_name]['suicides'] += 1
                else:
                    # Track kills and deaths
                    if killer_name not in simple_stats:
                        simple_stats[killer_name] = {'kills': 0, 'deaths': 0, 'suicides': 0, 'distance_sum': 0}
                    if victim_name not in simple_stats:
                        simple_stats[victim_name] = {'kills': 0, 'deaths': 0, 'suicides': 0, 'distance_sum': 0}
                    
                    simple_stats[killer_name]['kills'] += 1
                    simple_stats[killer_name]['distance_sum'] += distance
                    simple_stats[victim_name]['deaths'] += 1
                
                # Phase 2: Sequential streak processing
                await self._process_streak_update(killer_name, victim_name, is_suicide, distance, player_states)
                
                valid_records += 1
            
            # Execute operations if database manager is available
            if self.db_manager and kill_events_to_insert:
                # Bulk insert kill events
                await self.db_manager.kill_events.insert_many(kill_events_to_insert, ordered=True)
                
                # Bulk update simple statistics
                await self._bulk_update_simple_stats(simple_stats)
                
                # Update streak statistics
                await self._update_streak_stats(player_states)
            
            if valid_records > 0:
                logger.info(f"Hybrid processed {valid_records} valid kill records for server {self.server_id}")
            if skipped_records > 0:
                logger.debug(f"Skipped {skipped_records} records with invalid player names")
                
        except Exception as e:
            logger.error(f"Failed to process kill batch: {e}")
            self.stats.errors.append(f"Batch processing error: {str(e)}")
    
    async def _process_streak_update(self, killer_name: str, victim_name: str, is_suicide: bool, 
                                   distance: int, player_states: Dict[str, Dict]):
        """Process streak updates in chronological order"""
        try:
            if is_suicide:
                # Suicide resets killer's streak
                if killer_name not in player_states:
                    player_states[killer_name] = {'current_streak': 0, 'best_streak': 0, 'longest_shot': 0}
                player_states[killer_name]['current_streak'] = 0
            else:
                # Initialize states if needed
                if killer_name not in player_states:
                    player_states[killer_name] = {'current_streak': 0, 'best_streak': 0, 'longest_shot': 0}
                if victim_name not in player_states:
                    player_states[victim_name] = {'current_streak': 0, 'best_streak': 0, 'longest_shot': 0}
                
                # Killer gets a kill - increment streak
                player_states[killer_name]['current_streak'] += 1
                if player_states[killer_name]['current_streak'] > player_states[killer_name]['best_streak']:
                    player_states[killer_name]['best_streak'] = player_states[killer_name]['current_streak']
                
                # Update longest shot
                if distance > player_states[killer_name]['longest_shot']:
                    player_states[killer_name]['longest_shot'] = distance
                
                # Victim dies - reset their streak
                player_states[victim_name]['current_streak'] = 0
                
        except Exception as e:
            logger.error(f"Failed to process streak update: {e}")
    
    async def _bulk_update_simple_stats(self, simple_stats: Dict[str, Dict]):
        """Efficiently update simple player statistics in bulk"""
        try:
            bulk_operations = []
            
            for player_name, stats in simple_stats.items():
                filter_query = {
                    'guild_id': self.guild_id,
                    'server_id': self.server_id,
                    'player_name': player_name
                }
                
                update_ops = {
                    '$inc': {
                        'kills': stats['kills'],
                        'deaths': stats['deaths'],
                        'suicides': stats['suicides'],
                        'total_distance': stats['distance_sum']
                    },
                    '$set': {
                        'last_updated': datetime.now(timezone.utc)
                    }
                }
                
                from pymongo import UpdateOne
                bulk_operations.append(
                    UpdateOne(filter_query, update_ops, upsert=True)
                )
            
            if bulk_operations:
                result = await self.db_manager.pvp_data.bulk_write(bulk_operations, ordered=False)
                logger.debug(f"Bulk updated {len(bulk_operations)} simple stat records")
                
        except Exception as e:
            logger.error(f"Failed to bulk update simple stats: {e}")
    
    async def _update_streak_stats(self, player_states: Dict[str, Dict]):
        """Update streak statistics for players"""
        try:
            for player_name, state in player_states.items():
                filter_query = {
                    'guild_id': self.guild_id,
                    'server_id': self.server_id,
                    'player_name': player_name
                }
                
                update_ops = {
                    '$set': {
                        'current_streak': state['current_streak'],
                        'last_updated': datetime.now(timezone.utc)
                    },
                    '$max': {
                        'best_streak': state['best_streak'],
                        'personal_best_distance': state['longest_shot']
                    }
                }
                
                await self.db_manager.pvp_data.update_one(filter_query, update_ops, upsert=True)
            
            if player_states:
                logger.debug(f"Updated streak stats for {len(player_states)} players")
                
        except Exception as e:
            logger.error(f"Failed to update streak stats: {e}")
    
    async def _clear_existing_server_data(self):
        """Clear existing PVP data and kill events for this server before historical processing"""
        try:
            logger.info(f"Clearing existing data for server {self.server_id} before historical processing")
            
            # Clear PVP statistics for this server
            pvp_delete_result = await self.db_manager.pvp_data.delete_many({
                'guild_id': self.guild_id,
                'server_id': self.server_id
            })
            
            # Clear kill events for this server
            kills_delete_result = await self.db_manager.kill_events.delete_many({
                'guild_id': self.guild_id,
                'server_id': self.server_id
            })
            
            logger.info(f"Cleared {pvp_delete_result.deleted_count} PVP records and {kills_delete_result.deleted_count} kill events for server {self.server_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear existing data for server {self.server_id}: {e}")
            # Don't fail the entire process if clearing fails
    
    def cancel(self):
        """Cancel the processing"""
        self._cancelled = True
    
    def _get_results(self) -> Dict[str, Any]:
        """Get processing results"""
        end_time = datetime.now(timezone.utc)
        duration = (end_time - self.stats.start_time).total_seconds() if self.stats.start_time else 0
        
        return {
            'server_id': self.server_id,
            'phase': self.stats.phase,
            'files_discovered': self.stats.files_discovered,
            'files_cached': self.stats.files_cached,
            'total_lines': self.stats.total_lines,
            'valid_kills': self.stats.valid_kills,
            'processed_kills': self.stats.processed_kills,
            'duration_seconds': duration,
            'success': self.stats.phase == ProcessingPhase.COMPLETE,
            'errors': self.stats.errors,
            'cancelled': self._cancelled
        }

class MultiServerProcessor:
    """Manages parallel processing across multiple servers"""
    
    def __init__(self, guild_id: int, db_manager=None):
        self.guild_id = guild_id
        self.db_manager = db_manager
        self.processors: Dict[str, ChronologicalProcessor] = {}
        self.results: Dict[str, Dict[str, Any]] = {}
        
    async def process_servers(self, server_configs: List[Dict[str, Any]], 
                            progress_callback=None) -> Dict[str, Any]:
        """Process multiple servers in parallel"""
        # Create processors for each server
        for server_config in server_configs:
            server_id = str(server_config.get('_id', 'unknown'))
            self.processors[server_id] = ChronologicalProcessor(self.guild_id, server_config, self.db_manager)
        
        # Process servers in parallel
        tasks = []
        for server_id, processor in self.processors.items():
            task = asyncio.create_task(
                processor.process_server_data(progress_callback),
                name=f"server_{server_id}"
            )
            tasks.append(task)
        
        # Wait for all servers to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for i, (server_id, result) in enumerate(zip(self.processors.keys(), results)):
            if isinstance(result, Exception):
                self.results[server_id] = {
                    'server_id': server_id,
                    'success': False,
                    'error': str(result)
                }
            else:
                self.results[server_id] = result
        
        return self._get_summary()
    
    def _get_summary(self) -> Dict[str, Any]:
        """Get summary of all server processing results"""
        total_files = sum(r.get('files_discovered', 0) for r in self.results.values())
        total_kills = sum(r.get('processed_kills', 0) for r in self.results.values())
        successful_servers = sum(1 for r in self.results.values() if r.get('success', False))
        
        return {
            'guild_id': self.guild_id,
            'total_servers': len(self.processors),
            'successful_servers': successful_servers,
            'total_files_processed': total_files,
            'total_kills_processed': total_kills,
            'server_results': self.results
        }