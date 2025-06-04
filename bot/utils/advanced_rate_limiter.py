"""
Emerald's Killfeed - Advanced Rate Limiter
BULLETPROOF rate limiting with priority queues and batching
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import deque, defaultdict
from enum import Enum
import discord

class MessagePriority(Enum):
    """Message priority levels"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

logger = logging.getLogger(__name__)

class AdvancedRateLimiter:
    """
    Advanced rate limiter with priority queues and error recovery
    """

    def __init__(self, bot):
        self.bot = bot
        self.channel_queues: Dict[int, List[Dict[str, Any]]] = {}
        self.processing_locks: Dict[int, asyncio.Lock] = {}
        self.last_send_times: Dict[int, datetime] = {}
        self.error_counts: Dict[int, int] = {}
        self.max_queue_size = 50  # Per channel
        self.max_error_count = 5

        # Start background processor
        asyncio.create_task(self._background_processor())

    async def queue_message(self, channel_id: int, embed: discord.Embed = None, 
                          file: discord.File = None, content: str = None,
                          priority: MessagePriority = MessagePriority.NORMAL) -> bool:
        """Queue a message for sending with rate limiting"""
        try:
            if not content and not embed and not file:
                logger.warning("Attempted to queue empty message")
                return False

            # Validate channel exists and bot has permissions
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"Channel {channel_id} not found for message queue")
                return False

            # Check bot permissions
            if isinstance(channel, discord.TextChannel):
                if not channel.permissions_for(channel.guild.me).send_messages:
                    logger.warning(f"No permission to send messages in channel {channel_id}")
                    return False

            message_data = {
                'channel_id': channel_id,
                'content': content,
                'embed': embed,
                'file': file,
                'priority': priority,
                'timestamp': datetime.now(timezone.utc),
                'attempts': 0
            }

            # Initialize channel queue if needed
            if channel_id not in self.channel_queues:
                self.channel_queues[channel_id] = []
                self.processing_locks[channel_id] = asyncio.Lock()
                self.error_counts[channel_id] = 0

            # Check queue size limits
            if len(self.channel_queues[channel_id]) >= self.max_queue_size:
                logger.warning(f"Queue full for channel {channel_id}, dropping oldest message")
                self.channel_queues[channel_id].pop(0)

            # Create message entry
            message_entry = {
                'embed': embed,
                'file': file,
                'content': content,
                'priority': priority,
                'timestamp': datetime.now(timezone.utc),
                'retries': 0
            }

            # Insert based on priority
            queue = self.channel_queues[channel_id]
            insert_pos = len(queue)

            for i, existing_msg in enumerate(queue):
                if existing_msg['priority'].value < priority.value:
                    insert_pos = i
                    break

            queue.insert(insert_pos, message_entry)

            logger.debug(f"Queued {priority.value} priority message for channel {channel_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to queue message: {e}")
            return False

    async def _validate_channel(self, channel_id: int) -> bool:
        """Validate that a channel exists and is accessible"""
        try:
            if not self.bot:
                return False

            channel = self.bot.get_channel(channel_id)
            if not channel:
                return False

            # Check basic permissions
            if hasattr(channel, 'permissions_for') and hasattr(self.bot, 'user'):
                permissions = channel.permissions_for(channel.guild.me if hasattr(channel, 'guild') else self.bot.user)
                if not permissions.send_messages:
                    return False

            return True

        except Exception as e:
            logger.error(f"Channel validation failed for {channel_id}: {e}")
            return False

    async def _background_processor(self):
        """Background task to process queued messages"""
        while True:
            try:
                await asyncio.sleep(1)  # Check every second

                for channel_id in list(self.channel_queues.keys()):
                    try:
                        await self._process_channel_queue(channel_id)
                    except Exception as e:
                        logger.error(f"Error processing queue for channel {channel_id}: {e}")
                        # Increment error count and disable channel if too many errors
                        self.error_counts[channel_id] = self.error_counts.get(channel_id, 0) + 1
                        if self.error_counts[channel_id] > self.max_error_count:
                            logger.warning(f"Disabling channel {channel_id} due to excessive errors")
                            del self.channel_queues[channel_id]
                            if channel_id in self.processing_locks:
                                del self.processing_locks[channel_id]
                            if channel_id in self.error_counts:
                                del self.error_counts[channel_id]

            except Exception as e:
                logger.error(f"Background processor error: {e}")
                await asyncio.sleep(5)  # Wait longer on major errors

    async def _process_channel_queue(self, channel_id: int):
        """Process messages for a specific channel with rate limiting"""
        if channel_id not in self.channel_queues or not self.channel_queues[channel_id]:
            return

        # Acquire lock for this channel
        if channel_id not in self.processing_locks:
            self.processing_locks[channel_id] = asyncio.Lock()

        async with self.processing_locks[channel_id]:
            # Check rate limit
            last_send = self.last_send_times.get(channel_id)
            if last_send:
                time_since_last = (datetime.now(timezone.utc) - last_send).total_seconds()
                if time_since_last < 1.0:  # 1 second rate limit
                    return

            # Get next message
            message_entry = self.channel_queues[channel_id].pop(0)

            try:
                channel = self.bot.get_channel(channel_id)
                if not channel:
                    logger.warning(f"Channel {channel_id} not found, dropping message")
                    return

                # Prepare send arguments
                send_kwargs = {}
                if message_entry['content']:
                    send_kwargs['content'] = message_entry['content']
                if message_entry['embed']:
                    send_kwargs['embed'] = message_entry['embed']
                if message_entry['file']:
                    send_kwargs['file'] = message_entry['file']

                # Send message
                await channel.send(**send_kwargs)
                self.last_send_times[channel_id] = datetime.now(timezone.utc)

                # Reset error count on success
                self.error_counts[channel_id] = 0

                logger.debug(f"Successfully sent message to channel {channel_id}")

            except discord.HTTPException as e:
                if e.status == 429:  # Rate limited
                    # Re-queue the message with increased retry count
                    message_entry['retries'] += 1
                    if message_entry['retries'] < 3:
                        self.channel_queues[channel_id].insert(0, message_entry)
                        logger.debug(f"Rate limited, re-queued message for channel {channel_id}")
                    else:
                        logger.warning(f"Dropping message for channel {channel_id} after max retries")
                elif e.status == 403:  # Forbidden
                    logger.warning(f"No permission to send to channel {channel_id}")
                elif e.status == 404:  # Not found
                    logger.warning(f"Channel {channel_id} not found")
                else:
                    logger.error(f"HTTP error sending to channel {channel_id}: {e}")

            except Exception as e:
                logger.error(f"Unexpected error sending to channel {channel_id}: {e}")
                message_entry['retries'] += 1
                if message_entry['retries'] < 3:
                    self.channel_queues[channel_id].insert(0, message_entry)

    async def flush_all_queues(self):
        """Flush all pending messages immediately"""
        try:
            logger.info("Flushing all rate limiter queues...")

            for channel_id in list(self.channel_queues.keys()):
                try:
                    while self.channel_queues.get(channel_id, []):
                        await self._process_channel_queue(channel_id)
                        await asyncio.sleep(0.1)  # Small delay between messages
                except Exception as e:
                    logger.error(f"Error flushing queue for channel {channel_id}: {e}")

            logger.info("Rate limiter queue flush completed")

        except Exception as e:
            logger.error(f"Error flushing rate limiter queues: {e}")

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status for monitoring"""
        try:
            total_queued = sum(len(queue) for queue in self.channel_queues.values())
            channel_stats = {}

            for channel_id, queue in self.channel_queues.items():
                channel_stats[channel_id] = {
                    'queued_messages': len(queue),
                    'error_count': self.error_counts.get(channel_id, 0),
                    'last_send': self.last_send_times.get(channel_id)
                }

            return {
                'total_queued': total_queued,
                'active_channels': len(self.channel_queues),
                'channel_stats': channel_stats
            }

        except Exception as e:
            logger.error(f"Error getting queue status: {e}")
            return {'error': str(e)}