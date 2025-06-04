"""
Voice Channel Batch Updater
Prevents rate limiting by batching voice channel updates
"""
import asyncio
import logging
from typing import Dict, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class VoiceChannelBatcher:
    """Batch voice channel updates to prevent rate limiting"""
    
    def __init__(self, bot):
        self.bot = bot
        self.pending_updates: Dict[int, Dict[str, any]] = {}  # channel_id -> update_data
        self.last_update_times: Dict[int, datetime] = {}
        self.update_lock = asyncio.Lock()
        self.min_update_interval = timedelta(minutes=5)  # Minimum 5 minutes between updates to reduce API calls
        
    async def queue_voice_channel_update(self, channel_id: int, server_name: str, player_count: int, max_players: int = 50):
        """Queue a voice channel update - will be processed with strict rate limiting"""
        async with self.update_lock:
            # Check if we're within cooldown period
            import os
            import time
            cooldown_file = "voice_channel_cooldown.txt"
            if os.path.exists(cooldown_file):
                try:
                    with open(cooldown_file, 'r') as f:
                        until = float(f.read().strip())
                        if time.time() < until:
                            # Skip this update due to rate limiting
                            return
                        else:
                            os.remove(cooldown_file)
                except Exception:
                    pass
            
            # Determine status
            if player_count == 0:
                status = "OFFLINE"
                color = "🔴"
            elif player_count < max_players * 0.3:
                status = "LOW"
                color = "🔵"
            elif player_count < max_players * 0.7:
                status = "MEDIUM"
                color = "🟡"
            else:
                status = "HIGH"
                color = "🟠"
            
            new_name = f"{color} {server_name} [{status}] • {player_count}/{max_players}"
            
            # Store the update data
            self.pending_updates[channel_id] = {
                'new_name': new_name,
                'server_name': server_name,
                'player_count': player_count,
                'queued_at': datetime.utcnow()
            }
            
            # Schedule processing with enhanced rate limiting
            last_update = self.last_update_times.get(channel_id)
            if not last_update or datetime.utcnow() - last_update >= self.min_update_interval:
                asyncio.create_task(self._process_pending_update(channel_id))
    
    async def _process_pending_update(self, channel_id: int):
        """Process a pending voice channel update with rate limit protection"""
        try:
            await asyncio.sleep(1)  # Small delay to allow batching
            
            async with self.update_lock:
                if channel_id not in self.pending_updates:
                    return
                    
                update_data = self.pending_updates.pop(channel_id)
                
                # Check rate limit
                last_update = self.last_update_times.get(channel_id)
                if last_update and datetime.utcnow() - last_update < self.min_update_interval:
                    # Too soon, skip this update
                    return
                
                try:
                    channel = self.bot.get_channel(channel_id)
                    if channel and hasattr(channel, 'edit'):
                        current_name = getattr(channel, 'name', '')
                        new_name = update_data['new_name']
                        
                        # Only update if name actually changed
                        if current_name != new_name:
                            await channel.edit(name=new_name)
                            self.last_update_times[channel_id] = datetime.utcnow()
                            logger.info(f"Voice channel updated: {update_data['server_name']} -> {update_data['player_count']} players")
                        
                except Exception as e:
                    if "rate limited" in str(e).lower():
                        logger.warning(f"Voice channel rate limited for {update_data['server_name']}")
                    else:
                        logger.error(f"Failed to update voice channel: {e}")
                        
        except Exception as e:
            logger.error(f"Error processing voice channel update: {e}")
    
    async def flush_all_pending(self):
        """Force flush all pending updates (used during shutdown)"""
        async with self.update_lock:
            for channel_id in list(self.pending_updates.keys()):
                await self._process_pending_update(channel_id)