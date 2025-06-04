
"""
Batch Sender - Efficiently batch and send messages to reduce API calls
"""

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import discord

logger = logging.getLogger(__name__)

class BatchSender:
    """
    Intelligent batch message sender with:
    - Message batching to reduce API calls
    - Channel-specific queuing
    - Automatic flushing based on time and count
    - Rate limit awareness
    """

    def __init__(self, bot):
        self.bot = bot
        
        # Batching configuration - increased intervals to reduce API calls
        self.MAX_BATCH_SIZE = 5
        self.MAX_BATCH_TIME = 120  # 2 minutes instead of 30 seconds
        self.FLUSH_INTERVAL = 60   # 1 minute instead of 5 seconds
        
        # Channel queues for batching
        self.channel_queues: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        self.channel_last_flush: Dict[int, float] = {}
        
        # Start the flush task
        self.flush_task = asyncio.create_task(self._periodic_flush())

    async def queue_message(self, channel_id: int, embed: discord.Embed, 
                          file: discord.File = None, content: str = None,
                          priority: str = "normal"):
        """Queue a message for batching"""
        try:
            message_data = {
                'embed': embed,
                'file': file,
                'content': content,
                'priority': priority,
                'timestamp': time.time()
            }
            
            self.channel_queues[channel_id].append(message_data)
            
            # Check if we should flush this channel
            if (len(self.channel_queues[channel_id]) >= self.MAX_BATCH_SIZE or
                self._should_flush_channel(channel_id)):
                await self._flush_channel(channel_id)
                
        except Exception as e:
            logger.error(f"Failed to queue message: {e}")

    def _should_flush_channel(self, channel_id: int) -> bool:
        """Check if channel should be flushed based on time"""
        queue = self.channel_queues[channel_id]
        if not queue:
            return False
        
        oldest_message_time = queue[0]['timestamp']
        return time.time() - oldest_message_time >= self.MAX_BATCH_TIME

    async def _flush_channel(self, channel_id: int):
        """Flush all queued messages for a channel"""
        if channel_id not in self.channel_queues or not self.channel_queues[channel_id]:
            return
        
        try:
            channel = self.bot.get_channel(channel_id)
            if not channel:
                logger.warning(f"Channel {channel_id} not found, clearing queue")
                self.channel_queues[channel_id].clear()
                return
            
            messages = self.channel_queues[channel_id].copy()
            self.channel_queues[channel_id].clear()
            self.channel_last_flush[channel_id] = time.time()
            
            logger.info(f"Batch sender: Flushing {len(messages)} messages to channel {channel.name} ({channel_id})")
            
            # Send messages with proper rate limiting
            sent_count = 0
            for i, message_data in enumerate(messages):
                try:
                    kwargs = {}
                    if message_data['embed']:
                        kwargs['embed'] = message_data['embed']
                    if message_data['file']:
                        kwargs['file'] = message_data['file']
                    if message_data['content']:
                        kwargs['content'] = message_data['content']
                    
                    if kwargs:  # Only send if there's something to send
                        logger.info(f"Batch sender: Sending message {i+1}/{len(messages)} to #{channel.name}")
                        sent_message = await channel.send(**kwargs)
                        sent_count += 1
                        logger.info(f"Batch sender: Successfully sent message {sent_message.id} to #{channel.name}")
                        await asyncio.sleep(0.1)  # Small delay between messages
                    
                except discord.Forbidden as e:
                    logger.error(f"Permission denied sending to channel #{channel.name} ({channel_id}): {e}")
                except discord.HTTPException as e:
                    if e.status == 429:  # Rate limited
                        logger.warning(f"Rate limited on channel #{channel.name} ({channel_id}) - stopping batch send")
                        # Stop sending more messages to this channel when rate limited
                        break
                    else:
                        logger.error(f"HTTP error sending message to #{channel.name}: {e}")
                except Exception as e:
                    error_str = str(e).lower()
                    if "rate limit" in error_str or "429" in error_str:
                        logger.warning(f"Rate limited on channel #{channel.name} ({channel_id}) - stopping batch send")
                        break
                    else:
                        logger.error(f"Error sending message to #{channel.name}: {e}")
            
            logger.info(f"Batch sender: Successfully sent {sent_count}/{len(messages)} messages to #{channel.name}")
            
        except Exception as e:
            logger.error(f"Error flushing channel {channel_id}: {e}")

    async def _periodic_flush(self):
        """Periodically flush channels based on time"""
        while True:
            try:
                current_time = time.time()
                
                for channel_id in list(self.channel_queues.keys()):
                    if self._should_flush_channel(channel_id):
                        await self._flush_channel(channel_id)
                
                await asyncio.sleep(self.FLUSH_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")
                await asyncio.sleep(1)

    async def flush_all_queues(self):
        """Flush all pending messages (for shutdown)"""
        try:
            tasks = []
            for channel_id in list(self.channel_queues.keys()):
                if self.channel_queues[channel_id]:
                    tasks.append(asyncio.create_task(self._flush_channel(channel_id)))
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
                logger.info("Flushed all batch queues")
            
        except Exception as e:
            logger.error(f"Error flushing all queues: {e}")

    def get_queue_stats(self) -> Dict[str, Any]:
        """Get batch queue statistics"""
        total_queued = sum(len(queue) for queue in self.channel_queues.values())
        active_channels = len([q for q in self.channel_queues.values() if q])
        
        return {
            'total_queued': total_queued,
            'active_channels': active_channels,
            'channels_with_messages': list(self.channel_queues.keys())
        }

    def __del__(self):
        """Cleanup on destruction"""
        if hasattr(self, 'flush_task') and not self.flush_task.done():
            self.flush_task.cancel()
