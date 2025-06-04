"""
Slots Game Implementation
Advanced slot machine with dynamic reels and progressive payouts
"""

import random
import logging
from typing import Dict, List, Tuple
import discord
from .core import GamblingCore, BetValidation, GameSession

logger = logging.getLogger(__name__)

class SlotsGame:
    """Advanced slot machine implementation"""
    
    SYMBOLS = {
        '🍒': {'value': 2, 'frequency': 25},
        '🍋': {'value': 3, 'frequency': 20},
        '🍊': {'value': 4, 'frequency': 15},
        '🍇': {'value': 6, 'frequency': 12},
        '🔔': {'value': 10, 'frequency': 8},
        '⭐': {'value': 15, 'frequency': 5},
        '💎': {'value': 50, 'frequency': 2},
        '🎰': {'value': 100, 'frequency': 1}
    }
    
    def __init__(self, gambling_core: GamblingCore):
        self.core = gambling_core
        
    def generate_reel(self) -> str:
        """Generate weighted random symbol"""
        symbols = []
        for symbol, data in self.SYMBOLS.items():
            symbols.extend([symbol] * data['frequency'])
        return random.choice(symbols)
        
    def spin_reels(self) -> List[str]:
        """Spin all three reels"""
        return [self.generate_reel() for _ in range(3)]
        
    def calculate_payout(self, reels: List[str], bet_amount: int) -> Tuple[int, str]:
        """Calculate payout and result description"""
        if len(set(reels)) == 1:  # All same
            symbol = reels[0]
            multiplier = self.SYMBOLS[symbol]['value']
            payout = bet_amount * multiplier
            return payout, f"JACKPOT! Triple {symbol} - {multiplier}x multiplier!"
            
        elif len(set(reels)) == 2:  # Two same
            symbol_counts = {symbol: reels.count(symbol) for symbol in set(reels)}
            matching_symbol = max(symbol_counts.keys(), key=lambda x: symbol_counts[x])
            
            if symbol_counts[matching_symbol] == 2:
                multiplier = self.SYMBOLS[matching_symbol]['value'] * 0.3
                payout = int(bet_amount * multiplier)
                return payout, f"Double {matching_symbol} - {multiplier:.1f}x multiplier!"
                
        return 0, "No match - Better luck next time!"
        
    async def play(self, ctx: discord.ApplicationContext, bet_amount: int) -> discord.Embed:
        """Play a slots game"""
        try:
            # Validate bet
            if not ctx.guild_id:
                embed = discord.Embed(title="❌ Error", description="Guild context required", color=0xff0000)
                return embed
            balance = await self.core.get_user_balance(ctx.guild_id, ctx.user.id)
            valid, error_msg = BetValidation.validate_bet_amount(bet_amount, balance)
            
            if not valid:
                embed = discord.Embed(
                    title="❌ Invalid Bet",
                    description=error_msg,
                    color=0xff0000
                )
                return embed
                
            # Deduct bet amount
            success = await self.core.update_user_balance(
                ctx.guild_id, ctx.user.id, -bet_amount, f"Slots bet: ${bet_amount:,}"
            )
            
            if not success:
                embed = discord.Embed(
                    title="❌ Transaction Failed",
                    description="Unable to process bet",
                    color=0xff0000
                )
                return embed
                
            # Spin reels
            reels = self.spin_reels()
            payout, result_desc = self.calculate_payout(reels, bet_amount)
            
            # Process winnings
            if payout > 0:
                await self.core.update_user_balance(
                    ctx.guild_id, ctx.user.id, payout, f"Slots win: ${payout:,}"
                )
                
            # Get updated balance
            new_balance = await self.core.get_user_balance(ctx.guild_id, ctx.user.id)
            net_change = payout - bet_amount
            
            # Create result embed
            embed = discord.Embed(
                title="🎰 EMERALD SLOTS",
                description=f"**{' | '.join(reels)}**\n\n{result_desc}",
                color=0x00ff00 if payout > 0 else 0xff6b35
            )
            
            embed.add_field(
                name="💰 Results",
                value=f"**Bet:** ${bet_amount:,}\n**Payout:** ${payout:,}\n**Net:** ${net_change:+,}",
                inline=True
            )
            
            embed.add_field(
                name="💳 Balance",
                value=f"${new_balance:,}",
                inline=True
            )
            
            return embed
            
        except Exception as e:
            logger.error(f"Slots game error: {e}")
            embed = discord.Embed(
                title="❌ Game Error",
                description="An error occurred during the game",
                color=0xff0000
            )
            return embed

class SlotsView(discord.ui.View):
    """Interactive slots game view"""
    
    def __init__(self, slots_game: SlotsGame):
        super().__init__(timeout=60)
        self.slots_game = slots_game
        
    @discord.ui.button(label="🎰 Spin Again", style=discord.ButtonStyle.primary)
    async def spin_again(self, button: discord.ui.Button, interaction: discord.Interaction):
        """Spin again with the same bet"""
        await interaction.response.defer()
        # Implementation would handle repeat bet logic