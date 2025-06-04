"""
Discord Message Rate Limiter
Prevents API flooding by batching and rate-limiting Discord messages
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class QueuedMessage:
    """Represents a queued Discord message"""
    guild_id: int
    server_id: str
    channel_type: str
    embed: Any
    file: Optional[Any] = None
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

class DiscordMessageRateLimiter:
    """Manages Discord message rate limiting and batching"""
    
    def __init__(self, max_messages_per_minute: int = 20, batch_delay: float = 2.0):
        self.max_messages_per_minute = max_messages_per_minute
        self.batch_delay = batch_delay
        self.message_queue: deque = deque()
        self.sent_messages: deque = deque()
        self.processing = False
        self.bot = None
        
        # Cooldown tracking for specific event types
        self.mission_cooldowns: Dict[str, datetime] = {}
        self.mission_cooldown_duration = 30  # 30 seconds between same mission events
        
    def set_bot(self, bot):
        """Set the bot instance for message sending"""
        self.bot = bot
        
    async def queue_message(self, guild_id: int, server_id: str, channel_type: str, 
                           embed: Any, file: Optional[Any] = None, 
                           event_key: Optional[str] = None) -> bool:
        """Queue a message for rate-limited sending"""
        
        # Check mission cooldown if event_key provided
        if event_key and self._is_on_cooldown(event_key):
            logger.debug(f"Skipping message for {event_key} - on cooldown")
            return False
        
        # Create queued message
        queued_msg = QueuedMessage(
            guild_id=guild_id,
            server_id=server_id,
            channel_type=channel_type,
            embed=embed,
            file=file
        )
        
        # Add to queue
        self.message_queue.append(queued_msg)
        
        # Set cooldown if event_key provided
        if event_key:
            self.mission_cooldowns[event_key] = datetime.utcnow()
        
        logger.debug(f"Queued message for {channel_type} in guild {guild_id} (queue size: {len(self.message_queue)})")
        
        # Start processing if not already running
        if not self.processing:
            asyncio.create_task(self._process_queue())
        
        return True
    
    def _is_on_cooldown(self, event_key: str) -> bool:
        """Check if an event is on cooldown"""
        if event_key not in self.mission_cooldowns:
            return False
        
        last_sent = self.mission_cooldowns[event_key]
        cooldown_expires = last_sent + timedelta(seconds=self.mission_cooldown_duration)
        
        return datetime.utcnow() < cooldown_expires
    
    async def _process_queue(self):
        """Process the message queue with rate limiting"""
        if self.processing:
            return
        
        self.processing = True
        
        try:
            while self.message_queue:
                # Check rate limit
                if not self._can_send_message():
                    # Wait before checking again
                    await asyncio.sleep(1.0)
                    continue
                
                # Get next batch of messages
                batch = self._get_next_batch()
                
                if not batch:
                    await asyncio.sleep(0.1)
                    continue
                
                # Send batch with delay between messages
                for message in batch:
                    try:
                        await self._send_message(message)
                        self._record_sent_message()
                        
                        # Small delay between messages in batch
                        if len(batch) > 1:
                            await asyncio.sleep(0.5)
                            
                    except Exception as e:
                        logger.error(f"Failed to send queued message: {e}")
                
                # Delay between batches
                if self.message_queue:
                    await asyncio.sleep(self.batch_delay)
                    
        except Exception as e:
            logger.error(f"Error in message queue processing: {e}")
        finally:
            self.processing = False
    
    def _can_send_message(self) -> bool:
        """Check if we can send a message within rate limits"""
        now = datetime.utcnow()
        cutoff_time = now - timedelta(minutes=1)
        
        # Clean old sent messages
        while self.sent_messages and self.sent_messages[0] < cutoff_time:
            self.sent_messages.popleft()
        
        # Check if under rate limit
        return len(self.sent_messages) < self.max_messages_per_minute
    
    def _get_next_batch(self) -> List[QueuedMessage]:
        """Get next batch of messages to send"""
        batch = []
        batch_size = min(3, len(self.message_queue))  # Max 3 messages per batch
        
        for _ in range(batch_size):
            if self.message_queue:
                batch.append(self.message_queue.popleft())
        
        return batch
    
    async def _send_message(self, message: QueuedMessage):
        """Send a single message through the bot's channel router"""
        if not self.bot or not hasattr(self.bot, 'channel_router'):
            logger.error("Bot or channel_router not available for message sending")
            return
        
        try:
            await self.bot.channel_router.send_embed_to_channel(
                guild_id=message.guild_id,
                server_id=message.server_id,
                channel_type=message.channel_type,
                embed=message.embed,
                file=message.file
            )
            
            logger.debug(f"Sent rate-limited message to {message.channel_type} for guild {message.guild_id}")
            
        except Exception as e:
            logger.error(f"Failed to send message via channel_router: {e}")
            raise
    
    def _record_sent_message(self):
        """Record that a message was sent for rate limiting"""
        self.sent_messages.append(datetime.utcnow())
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            'queue_size': len(self.message_queue),
            'messages_sent_last_minute': len(self.sent_messages),
            'rate_limit': self.max_messages_per_minute,
            'processing': self.processing,
            'active_cooldowns': len(self.mission_cooldowns)
        }
    
    def clear_old_cooldowns(self):
        """Clean up old mission cooldowns"""
        now = datetime.utcnow()
        expired_keys = [
            key for key, timestamp in self.mission_cooldowns.items()
            if now - timestamp > timedelta(seconds=self.mission_cooldown_duration + 60)
        ]
        
        for key in expired_keys:
            del self.mission_cooldowns[key]

# Global rate limiter instance
_rate_limiter: Optional[DiscordMessageRateLimiter] = None

def get_rate_limiter() -> DiscordMessageRateLimiter:
    """Get the global rate limiter instance"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = DiscordMessageRateLimiter(
            max_messages_per_minute=15,  # Conservative limit
            batch_delay=3.0  # 3 second delay between batches
        )
    return _rate_limiter