"""
Gambling Core System
Base classes and shared utilities for all gambling games
"""

import asyncio
import random
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

import discord
import discord
from discord.ext import commands
from bot.utils.embed_factory import EmbedFactory

logger = logging.getLogger(__name__)

class GamblingCore:
    """Core gambling system with shared utilities"""
    
    def __init__(self, bot):
        self.bot = bot
        
    async def check_premium_access(self, guild_id: int) -> bool:
        """Check if guild has premium access - unified validation"""
        try:
            if hasattr(self.bot, 'premium_manager_v2'):
                return await self.bot.premium_manager_v2.has_premium_access(guild_id)
            else:
                return False
        except Exception as e:
            logger.error(f"Premium check failed: {e}")
            return False
            
    async def get_user_balance(self, guild_id: int, user_id: int) -> int:
        """Get user's current balance"""
        try:
            wallet = await self.bot.db_manager.get_wallet(guild_id, user_id)
            return wallet.get('balance', 0) if wallet else 0
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0
            
    async def update_user_balance(self, guild_id: int, user_id: int, 
                                 amount: int, description: str) -> bool:
        """Update user balance and log transaction"""
        try:
            current_balance = await self.get_user_balance(guild_id, user_id)
            new_balance = current_balance + amount
            
            if new_balance < 0:
                return False
                
            operation = "add" if amount >= 0 else "subtract"
            await self.bot.db_manager.update_wallet(guild_id, user_id, abs(amount), operation)
            
            # Log wallet event
            await self.add_wallet_event(guild_id, user_id, amount, 'gambling', description)
            
            return True
        except Exception as e:
            logger.error(f"Error updating balance: {e}")
            return False
            
    async def add_wallet_event(self, guild_id: int, discord_id: int, 
                              amount: int, event_type: str, description: str):
        """Add wallet transaction event for tracking"""
        try:
            event_data = {
                'guild_id': guild_id,
                'discord_id': discord_id,
                'amount': amount,
                'event_type': event_type,
                'description': description,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            await self.bot.db_manager.add_wallet_event(
                guild_id, discord_id, amount, event_type, description
            )
        except Exception as e:
            logger.error(f"Error adding wallet event: {e}")

class BetValidation:
    """Bet validation utilities"""
    
    @staticmethod
    def validate_bet_amount(amount: int, balance: int, min_bet: int = 10, max_bet: int = 50000) -> Tuple[bool, str]:
        """Validate bet amount"""
        if amount < min_bet:
            return False, f"Minimum bet is ${min_bet:,}"
        if amount > max_bet:
            return False, f"Maximum bet is ${max_bet:,}"
        if amount > balance:
            return False, "Insufficient balance"
        return True, ""
        
    @staticmethod
    def calculate_payout(bet_amount: int, multiplier: float) -> int:
        """Calculate payout with multiplier"""
        return int(bet_amount * multiplier)

class GameSession:
    """Base class for game sessions"""
    
    def __init__(self, user_id: int, guild_id: int, bet_amount: int):
        self.user_id = user_id
        self.guild_id = guild_id
        self.bet_amount = bet_amount
        self.start_time = datetime.now(timezone.utc)
        self.active = True
        
    def end_session(self):
        """End the game session"""
        self.active = False