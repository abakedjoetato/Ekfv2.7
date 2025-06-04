"""
Roulette gambling game implementation
"""

import discord
import random
import logging
from typing import List, Dict, Any
from ..utils.embed_factory import EmbedFactory
from .core import GamblingCore

logger = logging.getLogger(__name__)

class BetValidation:
    """Bet validation utility"""
    
    @staticmethod
    def validate_bet_amount(bet_amount: int, balance: int) -> tuple[bool, str]:
        """Validate bet amount against balance"""
        if bet_amount <= 0:
            return False, "Bet amount must be positive"
        if bet_amount > balance:
            return False, f"Insufficient balance. You have ${balance:,}"
        return True, ""



class RouletteGame:
    """European Roulette implementation"""
    
    def __init__(self, core: GamblingCore):
        self.core = core
        self.numbers = list(range(37))  # 0-36
        self.red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
        self.black_numbers = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]
    
    def get_number_color(self, number: int) -> str:
        """Get color of a roulette number"""
        if number == 0:
            return "green"
        elif number in self.red_numbers:
            return "red"
        else:
            return "black"
    
    def calculate_payout(self, bet_choice: str, winning_number: int, bet_amount: int) -> int:
        """Calculate payout based on bet type and winning number"""
        bet_choice = bet_choice.lower()
        
        # Straight number bet (35:1)
        if bet_choice.isdigit():
            if int(bet_choice) == winning_number:
                return bet_amount * 35
            return 0
        
        # Color bets (1:1)
        if bet_choice in ["red", "black"]:
            if self.get_number_color(winning_number) == bet_choice:
                return bet_amount * 2
            return 0
        
        # Even/Odd bets (1:1)
        if bet_choice == "even" and winning_number != 0 and winning_number % 2 == 0:
            return bet_amount * 2
        if bet_choice == "odd" and winning_number % 2 == 1:
            return bet_amount * 2
        
        # High/Low bets (1:1)
        if bet_choice == "high" and 19 <= winning_number <= 36:
            return bet_amount * 2
        if bet_choice == "low" and 1 <= winning_number <= 18:
            return bet_amount * 2
        
        return 0
    
    async def play(self, ctx: discord.ApplicationContext, bet_amount: int, bet_choice: str) -> discord.Embed:
        """Play roulette game"""
        try:
            # Validate guild context
            if not ctx.guild:
                return discord.Embed(
                    title="❌ Error", 
                    description="This command must be used in a server", 
                    color=0xff0000
                )
            
            # Validate bet amount
            balance = await self.core.get_user_balance(ctx.guild.id, ctx.user.id)
            valid, error_msg = BetValidation.validate_bet_amount(bet_amount, balance)
            
            if not valid:
                embed = discord.Embed(
                    title="❌ Invalid Bet",
                    description=error_msg,
                    color=0xff0000
                )
                return embed
            
            # Deduct bet amount
            await self.core.update_user_balance(
                ctx.guild.id, ctx.user.id, -bet_amount, f"Roulette bet: ${bet_amount:,}"
            )
            
            # Spin the wheel
            winning_number = random.randint(0, 36)
            
            # Calculate payout
            payout = self.calculate_payout(bet_choice, winning_number, bet_amount)
            
            # Process winnings
            if payout > 0:
                await self.core.update_user_balance(
                    ctx.guild.id, ctx.user.id, payout, f"Roulette win: ${payout:,}"
                )
                
            # Get updated balance
            new_balance = await self.core.get_user_balance(ctx.guild.id, ctx.user.id)
            net_change = payout - bet_amount
            
            # Create result embed
            color = self.get_number_color(winning_number)
            embed_color = 0xff0000 if color == "red" else 0x000000 if color == "black" else 0x00ff00
            
            embed = discord.Embed(
                title="🎰 Roulette Results",
                color=embed_color
            )
            
            embed.add_field(
                name="🎯 Winning Number",
                value=f"**{winning_number}** ({color.title()})",
                inline=True
            )
            
            embed.add_field(
                name="💰 Your Bet",
                value=f"${bet_amount:,} on {bet_choice}",
                inline=True
            )
            
            if payout > 0:
                embed.add_field(
                    name="🎉 Payout",
                    value=f"${payout:,}",
                    inline=True
                )
                embed.add_field(
                    name="📈 Net Gain",
                    value=f"+${net_change:,}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="💸 Result",
                    value="No win this time!",
                    inline=True
                )
                embed.add_field(
                    name="📉 Net Loss",
                    value=f"-${bet_amount:,}",
                    inline=False
                )
            
            embed.add_field(
                name="💳 New Balance",
                value=f"${new_balance:,}",
                inline=False
            )
            
            return embed
            
        except Exception as e:
            logger.error(f"Roulette game error: {e}")
            return discord.Embed(
                title="❌ Game Error",
                description="An error occurred while playing roulette. Please try again.",
                color=0xff0000
            )
