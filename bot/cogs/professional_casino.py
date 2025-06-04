"""
Emerald's Killfeed - Professional Casino System
Sophisticated UI with modal integration, select menus, and intuitive workflows
"""
import discord
import asyncio
import random
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class CasinoMainView(discord.ui.View):
    """Main casino interface with professional UI"""
    
    def __init__(self, bot, guild_id: int, user_id: int, balance: int):
        super().__init__(timeout=600)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.balance = balance
        
        # Add game selection dropdown
        self.add_item(GameSelectionMenu(self))
    
    def create_main_embed(self):
        embed = discord.Embed(
            title="🎰 EMERALD ELITE CASINO",
            description="*Welcome to the premier gaming experience*",
            color=0x9932CC,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="💰 Account Balance",
            value=f"**${self.balance:,}**",
            inline=True
        )
        
        embed.add_field(
            name="🎮 Game Selection",
            value="Use the dropdown menu below to select your preferred game",
            inline=False
        )
        
        embed.add_field(
            name="🎯 Available Games",
            value="• **Slots** - Match symbols for big wins\n• **Roulette** - Predict numbers and colors\n• **Blackjack** - Beat the dealer to 21\n• **Coin Flip** - Simple heads or tails",
            inline=False
        )
        
        return embed
    
    @discord.ui.button(label="🔄 Refresh Balance", style=discord.ButtonStyle.secondary)
    async def refresh_balance(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This session belongs to another player.", ephemeral=True)
            return
        
        new_balance = await self.get_current_balance()
        self.balance = new_balance
        embed = self.create_main_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def get_current_balance(self):
        try:

            pass
            pass
            pass
            wallet = await self.bot.db_manager.get_wallet(self.guild_id, self.user_id)
            return wallet.get('balance', 0)
        except:
            return 0

class GameSelectionMenu(discord.ui.Select):
    """Professional game selection dropdown"""
    
    def __init__(self, casino_view):
        self.casino_view = casino_view
        
        options = [
            discord.SelectOption(
                label="🎰 Elite Slots",
                description="Match symbols across paylines for multiplied winnings",
                emoji="🎰",
                value="slots"
            ),
            discord.SelectOption(
                label="🎯 Roulette Wheel",
                description="Predict the winning number, color, or range",
                emoji="🎯",
                value="roulette"
            ),
            discord.SelectOption(
                label="🃏 Blackjack Table",
                description="Beat the dealer without going over 21",
                emoji="🃏",
                value="blackjack"
            ),
            discord.SelectOption(
                label="🪙 Coin Flip",
                description="Simple heads or tails probability game",
                emoji="🪙",
                value="coinflip"
            ),
            discord.SelectOption(
                label="🚀 Rocket Crash",
                description="Cash out before the rocket crashes for multiplied wins",
                emoji="🚀",
                value="rocket"
            )
        ]
        
        super().__init__(
            placeholder="🎲 Choose your game experience...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.casino_view.user_id:
            await interaction.response.send_message("This session belongs to another player.", ephemeral=True)
            return
        
        game_type = self.values[0]
        
        # Show bet selection for the chosen game
        bet_view = BetSelectionView(
            self.casino_view.bot,
            self.casino_view.guild_id,
            self.casino_view.user_id,
            self.casino_view.balance,
            game_type
        )
        
        embed = bet_view.create_bet_embed()
        await interaction.response.edit_message(embed=embed, view=bet_view)

class BetSelectionView(discord.ui.View):
    """Professional bet amount selection interface"""
    
    def __init__(self, bot, guild_id: int, user_id: int, balance: int, game_type: str):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.balance = balance
        self.game_type = game_type
        
        # Add bet amount dropdown
        self.add_item(BetAmountMenu(balance, self))
    
    def create_bet_embed(self):
        embed = discord.Embed(
            title=f"🎰 {self.game_type.title()} - Bet Selection",
            description="Choose your bet amount to start playing",
            color=0x00FF7F,
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="💰 Available Balance",
            value=f"**${self.balance:,}**",
            inline=True
        )
        
        game_info = {
            "slots": "🎰 Match 3 symbols for 2x-10x multipliers",
            "roulette": "🎯 Win 2x on colors, 36x on exact numbers",
            "blackjack": "🃏 Beat dealer for 2x, blackjack pays 2.5x",
            "coinflip": "🪙 Heads or tails for 2x payout"
        }
        
        embed.add_field(
            name="🎮 Game Rules",
            value=game_info.get(self.game_type, "Choose your bet amount"),
            inline=False
        )
        
        return embed
    
    @discord.ui.button(label="🏠 Back to Casino", style=discord.ButtonStyle.red)
    async def back_to_casino(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This session belongs to another player.", ephemeral=True)
            return
        
        casino_view = CasinoMainView(self.bot, self.guild_id, self.user_id, self.balance)
        embed = casino_view.create_main_embed()
        await interaction.response.edit_message(embed=embed, view=casino_view)

class BetAmountMenu(discord.ui.Select):
    """Smart bet amount selection with risk profiles"""
    
    def __init__(self, balance: int, bet_view):
        self.balance = balance
        self.bet_view = bet_view
        
        suggestions = []
        if balance >= 50:
            suggestions.append(("💰 Conservative ($50)", 50, "Low risk, steady play"))
        if balance >= 100:
            suggestions.append(("⚡ Moderate ($100)", 100, "Balanced risk and reward"))
        if balance >= 250:
            suggestions.append(("🔥 Aggressive ($250)", 250, "Higher risk for bigger wins"))
        if balance >= 500:
            suggestions.append(("💎 High Roller ($500)", 500, "Maximum risk and reward"))
        
        suggestions.append(("🎯 Custom Amount", 0, "Enter your own bet amount"))
        
        options = []
        for label, amount, desc in suggestions:
            options.append(discord.SelectOption(
                label=label,
                description=desc,
                value=str(amount)
            ))
        
        super().__init__(
            placeholder="💰 Select your betting strategy...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.bet_view.user_id:
            await interaction.response.send_message("This session belongs to another player.", ephemeral=True)
            return
        
        bet = int(self.values[0])
        
        if bet == 0:  # Custom amount
            modal = CustomBetModal(self.bet_view.game_type, self.balance, self.bet_view)
            await interaction.response.send_modal(modal)
        else:
            # Start the game with selected bet
            await self.start_game(interaction, bet)
    
    async def start_game(self, interaction: discord.Interaction, bet_amount: int):
        # Validate bet amount
        if bet_amount > self.balance:
            await interaction.response.send_message(f"Insufficient funds. You have ${self.balance:,} but tried to bet ${bet_amount:,}.", ephemeral=True)
            return
        
        # Create appropriate game view
        if self.bet_view.game_type == "slots":
            game_view = SlotsGameView(self.bet_view.bot, self.bet_view.guild_id, self.bet_view.user_id, self.balance, bet_amount)
        elif self.bet_view.game_type == "coinflip":
            game_view = CoinFlipGameView(self.bet_view.bot, self.bet_view.guild_id, self.bet_view.user_id, self.balance, bet_amount)
        elif self.bet_view.game_type == "roulette":
            game_view = RouletteGameView(self.bet_view.bot, self.bet_view.guild_id, self.bet_view.user_id, self.balance, bet_amount)
        elif self.bet_view.game_type == "rocket":
            game_view = RocketCrashGameView(self.bet_view.bot, self.bet_view.guild_id, self.bet_view.user_id, self.balance, bet_amount)
        elif self.bet_view.game_type == "blackjack":
            game_view = BlackjackGameView(self.bet_view.bot, self.bet_view.guild_id, self.bet_view.user_id, self.balance, bet_amount)
        else:
            await interaction.response.send_message("Game coming soon!", ephemeral=True)
            return
        
        embed = game_view.create_game_embed()
        await interaction.response.edit_message(embed=embed, view=game_view)

class CustomBetModal(discord.ui.Modal):
    """Modal for custom bet amount entry"""
    
    def __init__(self, game_type: str, max_balance: int, bet_view):
        super().__init__(title=f"Custom Bet - {game_type.title()}")
        self.game_type = game_type
        self.max_balance = max_balance
        self.bet_view = bet_view
        
        self.bet_input = discord.ui.TextInput(
            label="💰 Enter Bet Amount",
            placeholder=f"Amount between $1 and ${max_balance:,}",
            min_length=1,
            max_length=10,
            style=discord.TextInputStyle.short
        )
        self.add_item(self.bet_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:

            pass
            pass
            pass
            bet_str = self.bet_input.value.strip().replace(',', '').replace('$', '')
            
            if not bet_str.isdigit():
                await interaction.response.send_message("Invalid bet amount. Use numbers only.", ephemeral=True)
                return
            
            bet = int(bet_str)
            
            if bet <= 0:
                await interaction.response.send_message("Bet must be positive.", ephemeral=True)
                return
            
            if bet > self.max_balance:
                await interaction.response.send_message(f"Insufficient funds. Maximum bet: ${self.max_balance:,}", ephemeral=True)
                return
            
            # Start the game with custom bet
            bet_menu = self.bet_view.children[0]  # Get the BetAmountMenu
            await bet_menu.start_game(interaction, bet)
            
        except Exception as e:
            logger.error(f"Custom bet modal error: {e}")
            await interaction.response.send_message("Error processing bet. Please try again.", ephemeral=True)

class SlotsGameView(discord.ui.View):
    """Professional slots game interface"""
    
    def __init__(self, bot, guild_id: int, user_id: int, balance: int, bet_amount: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.balance = balance
        self.bet_amount = bet_amount
        self.symbols = ['🍒', '🍋', '🍊', '🍇', '⭐', '💎']
        self.multipliers = {'🍒': 2, '🍋': 3, '🍊': 4, '🍇': 5, '⭐': 8, '💎': 10}
    
    def create_game_embed(self, reels=None, result=None):
        embed = discord.Embed(
            title="🎰 ELITE SLOTS",
            color=0x00FF7F,
            timestamp=datetime.now(timezone.utc)
        )
        
        if reels:
            slots_display = f"**[ {reels[0]} | {reels[1]} | {reels[2]} ]**"
            embed.add_field(name="🎰 Reels", value=slots_display, inline=False)
            
            if result and result['win'] > 0:
                embed.add_field(name="🎉 Winner!", value=f"Won ${result['win']:,}! (+${result['profit']:,})", inline=True)
                embed.color = 0xFFD700
            else:
                embed.add_field(name="💔 No Match", value=f"Lost ${self.bet_amount}", inline=True)
                embed.color = 0xFF6B6B
        
        embed.add_field(name="💰 Balance", value=f"${self.balance:,}", inline=True)
        embed.add_field(name="🎯 Current Bet", value=f"${self.bet_amount:,}", inline=True)
        
        embed.add_field(
            name="💎 Paytable",
            value="🍒🍒🍒 = 2x\n🍋🍋🍋 = 3x\n🍊🍊🍊 = 4x\n🍇🍇🍇 = 5x\n⭐⭐⭐ = 8x\n💎💎💎 = 10x",
            inline=False
        )
        
        return embed
    
    @discord.ui.button(label="🎰 SPIN", style=discord.ButtonStyle.green, emoji="🎰")
    async def spin_slots(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your game session.", ephemeral=True)
            return
        
        current_balance = await self.get_current_balance()
        
        if current_balance < self.bet_amount:
            await interaction.response.send_message(f"Insufficient funds. You need ${self.bet_amount:,} but have ${current_balance:,}.", ephemeral=True)
            return
        
        # Generate reels
        reels = [random.choice(self.symbols) for _ in range(3)]
        
        # Calculate result
        win_amount = 0
        if reels[0] == reels[1] == reels[2]:  # Three of a kind
            multiplier = self.multipliers[reels[0]]
            win_amount = self.bet_amount * multiplier
        
        # Update balance
        balance_change = win_amount - self.bet_amount
        success = await self.update_balance(balance_change)
        
        if not success:
            await interaction.response.send_message("Error processing spin. Please try again.", ephemeral=True)
            return
        
        new_balance = current_balance + balance_change
        self.balance = new_balance
        
        result = {'win': win_amount, 'profit': balance_change}
        embed = self.create_game_embed(reels, result)
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="🏠 Back to Casino", style=discord.ButtonStyle.red)
    async def back_to_casino(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your game session.", ephemeral=True)
            return
        
        current_balance = await self.get_current_balance()
        casino_view = CasinoMainView(self.bot, self.guild_id, self.user_id, current_balance)
        embed = casino_view.create_main_embed()
        await interaction.response.edit_message(embed=embed, view=casino_view)
    
    async def get_current_balance(self):
        try:

            pass
            pass
            pass
            wallet = await self.bot.db_manager.get_wallet(self.guild_id, self.user_id)
            return wallet.get('balance', 0)
        except:
            return 0
    
    async def update_balance(self, amount):
        try:

            pass
            pass
            pass
            operation = "add" if amount >= 0 else "subtract"
            return await self.bot.db_manager.update_wallet(self.guild_id, self.user_id, abs(amount), operation)
        except:
            return False

class CoinFlipGameView(discord.ui.View):
    """Professional coin flip game interface"""
    
    def __init__(self, bot, guild_id: int, user_id: int, balance: int, bet_amount: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.balance = balance
        self.bet_amount = bet_amount
    
    def create_game_embed(self, result=None, choice=None):
        embed = discord.Embed(
            title="🪙 COIN FLIP",
            color=0xFFD700,
            timestamp=datetime.now(timezone.utc)
        )
        
        if result:
            coin_emoji = "👑" if result == "heads" else "🪙"
            embed.add_field(name="🪙 Result", value=f"{coin_emoji} **{result.upper()}**", inline=False)
            
            if choice:
                embed.add_field(name="Your Choice", value=choice.upper(), inline=True)
                
                if choice == result:
                    win_amount = self.bet_amount * 2
                    embed.add_field(name="🎉 Winner!", value=f"Won ${win_amount:,}! (+${self.bet_amount:,})", inline=True)
                    embed.color = 0x00FF7F
                else:
                    embed.add_field(name="💔 Lost", value=f"Lost ${self.bet_amount:,}", inline=True)
                    embed.color = 0xFF6B6B
        
        embed.add_field(name="💰 Balance", value=f"${self.balance:,}", inline=True)
        embed.add_field(name="🎯 Current Bet", value=f"${self.bet_amount:,}", inline=True)
        
        return embed
    
    @discord.ui.button(label="👑 HEADS", style=discord.ButtonStyle.primary, emoji="👑")
    async def bet_heads(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.play_coinflip(interaction, "heads")
    
    @discord.ui.button(label="🪙 TAILS", style=discord.ButtonStyle.primary, emoji="🪙")
    async def bet_tails(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.play_coinflip(interaction, "tails")
    
    @discord.ui.button(label="🏠 Back to Casino", style=discord.ButtonStyle.red)
    async def back_to_casino(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your game session.", ephemeral=True)
            return
        
        current_balance = await self.get_current_balance()
        casino_view = CasinoMainView(self.bot, self.guild_id, self.user_id, current_balance)
        embed = casino_view.create_main_embed()
        await interaction.response.edit_message(embed=embed, view=casino_view)
    
    async def play_coinflip(self, interaction: discord.Interaction, choice: str):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your game session.", ephemeral=True)
            return
        
        current_balance = await self.get_current_balance()
        
        if current_balance < self.bet_amount:
            await interaction.response.send_message(f"Insufficient funds. You need ${self.bet_amount:,} but have ${current_balance:,}.", ephemeral=True)
            return
        
        # Flip the coin
        result = random.choice(["heads", "tails"])
        
        # Calculate result
        win_amount = 0
        if choice == result:
            win_amount = self.bet_amount * 2
        
        # Update balance
        balance_change = win_amount - self.bet_amount
        success = await self.update_balance(balance_change)
        
        if not success:
            await interaction.response.send_message("Error processing flip. Please try again.", ephemeral=True)
            return
        
        new_balance = current_balance + balance_change
        self.balance = new_balance
        
        embed = self.create_game_embed(result, choice)
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def get_current_balance(self):
        try:

            pass
            pass
            pass
            wallet = await self.bot.db_manager.get_wallet(self.guild_id, self.user_id)
            return wallet.get('balance', 0)
        except:
            return 0
    
    async def update_balance(self, amount):
        try:

            pass
            pass
            pass
            operation = "add" if amount >= 0 else "subtract"
            return await self.bot.db_manager.update_wallet(self.guild_id, self.user_id, abs(amount), operation)
        except:
            return False

class RouletteGameView(discord.ui.View):
    """Professional roulette game interface"""
    
    def __init__(self, bot, guild_id: int, user_id: int, balance: int, bet_amount: int):
        super().__init__(timeout=300)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.balance = balance
        self.bet_amount = bet_amount
        
        # Add roulette betting options
        self.add_item(RouletteBetMenu(self))
    
    def create_game_embed(self, result=None, bet_type=None):
        embed = discord.Embed(
            title="🎯 ROULETTE WHEEL",
            color=0xDC143C,
            timestamp=datetime.now(timezone.utc)
        )
        
        if result is not None:
            color = "🔴" if result['color'] == "red" else "⚫" if result['color'] == "black" else "🟢"
            embed.add_field(name="🎯 Winning Number", value=f"{color} **{result['number']}**", inline=False)
            
            if bet_type and result.get('win_amount', 0) > 0:
                embed.add_field(name="🎉 Winner!", value=f"Won ${result['win_amount']:,}! (+${result['profit']:,})", inline=True)
                embed.color = 0x00FF7F
            elif bet_type:
                embed.add_field(name="💔 Lost", value=f"Lost ${self.bet_amount:,}", inline=True)
                embed.color = 0xFF6B6B
        
        embed.add_field(name="💰 Balance", value=f"${self.balance:,}", inline=True)
        embed.add_field(name="🎯 Current Bet", value=f"${self.bet_amount:,}", inline=True)
        
        embed.add_field(
            name="💰 Payouts",
            value="Red/Black: 2x\nEven/Odd: 2x\nLow/High: 2x\nExact Number: 36x",
            inline=False
        )
        
        return embed
    
    @discord.ui.button(label="🏠 Back to Casino", style=discord.ButtonStyle.red)
    async def back_to_casino(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This is not your game session.", ephemeral=True)
            return
        
        current_balance = await self.get_current_balance()
        casino_view = CasinoMainView(self.bot, self.guild_id, self.user_id, current_balance)
        embed = casino_view.create_main_embed()
        await interaction.response.edit_message(embed=embed, view=casino_view)
    
    async def get_current_balance(self):
        try:

            pass
            pass
            pass
            wallet = await self.bot.db_manager.get_wallet(self.guild_id, self.user_id)
            return wallet.get('balance', 0)
        except:
            return 0

class RouletteBetMenu(discord.ui.Select):
    """Roulette betting options dropdown"""
    
    def __init__(self, roulette_view):
        self.roulette_view = roulette_view
        
        options = [
            discord.SelectOption(label="🔴 Red", description="Bet on red numbers (2x payout)", value="red"),
            discord.SelectOption(label="⚫ Black", description="Bet on black numbers (2x payout)", value="black"),
            discord.SelectOption(label="🔢 Even", description="Bet on even numbers (2x payout)", value="even"),
            discord.SelectOption(label="🔢 Odd", description="Bet on odd numbers (2x payout)", value="odd"),
            discord.SelectOption(label="⬇️ Low (1-18)", description="Bet on low numbers (2x payout)", value="low"),
            discord.SelectOption(label="⬆️ High (19-36)", description="Bet on high numbers (2x payout)", value="high"),
        ]
        
        super().__init__(
            placeholder="🎯 Choose your roulette bet...",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.roulette_view.user_id:
            await interaction.response.send_message("This is not your game session.", ephemeral=True)
            return
        
        bet_type = self.values[0]
        await self.play_roulette(interaction, bet_type)
    
    async def play_roulette(self, interaction: discord.Interaction, bet_type: str):
        current_balance = await self.roulette_view.get_current_balance()
        
        if current_balance < self.roulette_view.bet_amount:
            await interaction.response.send_message(f"Insufficient funds. You need ${self.roulette_view.bet_amount:,} but have ${current_balance:,}.", ephemeral=True)
            return
        
        # Spin the roulette wheel
        number = random.randint(0, 36)
        
        # Determine color
        if number == 0:
            color = "green"
        elif number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
            color = "red"
        else:
            color = "black"
        
        # Check if bet wins
        win_amount = 0
        if (bet_type == "red" and color == "red") or \
           (bet_type == "black" and color == "black") or \
           (bet_type == "even" and number % 2 == 0 and number != 0) or \
           (bet_type == "odd" and number % 2 == 1) or \
           (bet_type == "low" and 1 <= number <= 18) or \
           (bet_type == "high" and 19 <= number <= 36):
            win_amount = self.roulette_view.bet_amount * 2
        
        # Update balance
        balance_change = win_amount - self.roulette_view.bet_amount
        success = await self.update_balance(balance_change)
        
        if not success:
            await interaction.response.send_message("Error processing bet. Please try again.", ephemeral=True)
            return
        
        new_balance = current_balance + balance_change
        self.roulette_view.balance = new_balance
        
        result = {
            'number': number,
            'color': color,
            'win_amount': win_amount,
            'profit': balance_change
        }
        
        embed = self.roulette_view.create_game_embed(result, bet_type)
        await interaction.response.edit_message(embed=embed, view=self.roulette_view)
    
    async def update_balance(self, amount):
        try:

            pass
            pass
            pass
            operation = "add" if amount >= 0 else "subtract"
            return await self.roulette_view.bot.db_manager.update_wallet(
                self.roulette_view.guild_id, 
                self.roulette_view.user_id, 
                abs(amount), 
                operation
            )
        except:
            return False

class RocketCrashGameView(discord.ui.View):
    """Professional rocket crash game with real-time multiplier action"""
    
    def __init__(self, bot, guild_id: int, user_id: int, balance: int, bet_amount: int):
        super().__init__(timeout=120)
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.balance = balance
        self.bet_amount = bet_amount
        self.multiplier = 1.00
        self.crashed = False
        self.cashed_out = False
        self.rocket_running = False
        self.crash_point = random.uniform(1.02, 15.0)  # Random crash between 1.02x and 15x
        
    def create_game_embed(self, status="ready"):
        """Create the rocket crash game embed"""
        if status == "ready":
            embed = discord.Embed(
                title="🚀 ROCKET CRASH MISSION",
                description=f"**Mission Investment:** ${self.bet_amount:,}\n**Current Multiplier:** {self.multiplier:.2f}x\n**Potential Payout:** ${int(self.bet_amount * self.multiplier):,}\n\n🛸 **Mission Control:** Rocket on standby - ready for launch!",
                color=0x00ff00
            )
        elif status == "flying":
            altitude = min(int((self.multiplier - 1) * 8), 12)
            rocket_display = "🚀" + "⬆️" * altitude
            
            embed = discord.Embed(
                title="🚀 ROCKET IN FLIGHT",
                description=f"**Altitude:** {rocket_display}\n**Live Multiplier:** {self.multiplier:.2f}x\n**Current Value:** ${int(self.bet_amount * self.multiplier):,}\n\n⚡ **Mission Control:** Rocket climbing! Cash out anytime!",
                color=0xff6600
            )
        elif status == "crashed":
            embed = discord.Embed(
                title="💥 ROCKET CRASHED",
                description=f"**Crash Point:** {self.crash_point:.2f}x\n**Your Multiplier:** {self.multiplier:.2f}x\n**Mission Result:** FAILED\n**Loss:** -${self.bet_amount:,}",
                color=0xff0000
            )
        else:  # cashed_out
            payout = int(self.bet_amount * self.multiplier)
            profit = payout - self.bet_amount
            embed = discord.Embed(
                title="💰 SUCCESSFUL CASH OUT",
                description=f"**Cash Out Multiplier:** {self.multiplier:.2f}x\n**Total Payout:** ${payout:,}\n**Mission Profit:** ${profit:+,}\n\n🎉 **Mission Control:** Successful extraction!",
                color=0x00ff00
            )
            
        return embed
    
    @discord.ui.button(label="🚀 LAUNCH ROCKET", style=discord.ButtonStyle.danger, row=0)
    async def launch_rocket(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This rocket mission belongs to another pilot.", ephemeral=True)
            return
            
        if self.rocket_running:
            return
            
        # Deduct bet amount
        success = await self.update_balance(-self.bet_amount)
        if not success:
            await interaction.response.send_message("Insufficient funds for rocket mission!", ephemeral=True)
            return
            
        await self._start_rocket_sequence(interaction)
        
    @discord.ui.button(label="💰 CASH OUT", style=discord.ButtonStyle.success, row=0, disabled=True)
    async def cash_out(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This rocket mission belongs to another pilot.", ephemeral=True)
            return
            
        if not self.crashed and not self.cashed_out and self.rocket_running:
            self.cashed_out = True
            await self._process_cash_out(interaction)
    
    @discord.ui.button(label="🔙 Back to Casino", style=discord.ButtonStyle.secondary, row=1)
    async def back_to_casino(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This session belongs to another player.", ephemeral=True)
            return
            
        current_balance = await self.get_current_balance()
        casino_view = CasinoMainView(self.bot, self.guild_id, self.user_id, current_balance)
        embed = casino_view.create_main_embed()
        await interaction.response.edit_message(embed=embed, view=casino_view)
    
    async def _start_rocket_sequence(self, interaction: discord.Interaction):
        """Start the rocket launch with real-time multiplier updates"""
        await interaction.response.defer()
        self.rocket_running = True
        
        # Enable cash out, disable launch
        for item in self.children:
            if hasattr(item, 'label'):
                if 'Cash Out' in item.label:
                    item.disabled = False
                elif 'Launch' in item.label:
                    item.disabled = True
        
        # Real-time rocket flight
        import asyncio
        while self.multiplier < self.crash_point and not self.cashed_out:
            # Dynamic speed based on altitude
            if self.multiplier < 2.0:
                increment = random.uniform(0.01, 0.04)
                delay = 0.8
            elif self.multiplier < 5.0:
                increment = random.uniform(0.02, 0.07)
                delay = 0.6
            else:
                increment = random.uniform(0.03, 0.12)
                delay = 0.4
                
            self.multiplier = round(self.multiplier + increment, 2)
            
            embed = self.create_game_embed("flying")
            try:

                pass
                pass
                pass
                await interaction.edit_original_response(embed=embed, view=self)
            except:
                break
                
            await asyncio.sleep(delay)
        
        # Handle crash if not cashed out
        if not self.cashed_out:
            self.crashed = True
            await self._process_crash(interaction)
    
    async def _process_cash_out(self, interaction: discord.Interaction):
        """Process successful cash out"""
        await interaction.response.defer()
        payout = int(self.bet_amount * self.multiplier)
        profit = payout - self.bet_amount
        
        # Add winnings to balance
        await self.update_balance(profit)
        
        embed = self.create_game_embed("cashed_out")
        self.clear_items()
        self.add_item(discord.ui.Button(label="🔙 Back to Casino", style=discord.ButtonStyle.secondary, custom_id="back"))
        
        await interaction.edit_original_response(embed=embed, view=self)
    
    async def _process_crash(self, interaction: discord.Interaction):
        """Process rocket crash"""
        embed = self.create_game_embed("crashed")
        self.clear_items()
        self.add_item(discord.ui.Button(label="🔙 Back to Casino", style=discord.ButtonStyle.secondary, custom_id="back"))
        
        try:

        
            pass
            pass
            pass
            await interaction.edit_original_response(embed=embed, view=self)
        except:
            pass
    
    async def get_current_balance(self):
        """Get user's current balance"""
        try:

            pass
            pass
            pass
            wallet = await self.bot.db_manager.get_wallet(self.guild_id, self.user_id)
            return wallet.get('balance', 0)
        except Exception:
            return 0
    
    async def update_balance(self, amount):
        """Update user's balance"""
        try:

            pass
            pass
            pass
            operation = "add" if amount >= 0 else "subtract"
            return await self.bot.db_manager.update_wallet(
                self.guild_id, self.user_id, abs(amount), operation
            )
        except Exception:
            return False

class BlackjackGameView(discord.ui.View):
    """Professional blackjack game with dealer AI"""
    
    def __init__(self, bot, guild_id: int, user_id: int, balance: int, bet_amount: int):
        super().__init__(timeout=300)  # 5 minute timeout for blackjack
        self.bot = bot
        self.guild_id = guild_id
        self.user_id = user_id
        self.balance = balance
        self.bet_amount = bet_amount
        self.deck = []
        self.player_cards = []
        self.dealer_cards = []
        self.game_over = False
        self.player_stood = False
        self._create_deck()
        self._deal_initial_cards()
        
    def _create_deck(self):
        """Create a standard 52-card deck"""
        suits = ['♠️', '♥️', '♦️', '♣️']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        self.deck = [f"{rank}{suit}" for suit in suits for rank in ranks]
        random.shuffle(self.deck)
    
    def _deal_initial_cards(self):
        """Deal initial 2 cards to player and dealer"""
        self.player_cards = [self.deck.pop(), self.deck.pop()]
        self.dealer_cards = [self.deck.pop(), self.deck.pop()]
    
    def _calculate_hand_value(self, cards):
        """Calculate the best possible value of a hand"""
        value = 0
        aces = 0
        
        for card in cards:
            rank = card[:-2]  # Remove suit
            if rank in ['J', 'Q', 'K']:
                value += 10
            elif rank == 'A':
                aces += 1
                value += 11
            else:
                value += int(rank)
        
        # Adjust for aces
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
            
        return value
    
    def _format_cards(self, cards, hide_first=False):
        """Format cards for display"""
        if hide_first and len(cards) > 0:
            return "🎴 " + " ".join(cards[1:])
        return " ".join(cards)
    
    def create_game_embed(self):
        """Create the blackjack game embed"""
        player_value = self._calculate_hand_value(self.player_cards)
        dealer_value = self._calculate_hand_value(self.dealer_cards)
        
        if self.game_over:
            # Show all cards when game is over
            dealer_display = self._format_cards(self.dealer_cards)
            dealer_value_display = f" (Value: {dealer_value})"
        else:
            # Hide dealer's first card during play
            dealer_display = self._format_cards(self.dealer_cards, hide_first=True)
            dealer_value_display = f" (Value: ?)"
        
        embed = discord.Embed(
            title="🃏 BLACKJACK TABLE",
            color=0x2b2d31
        )
        
        embed.add_field(
            name="🎩 Dealer's Hand",
            value=f"{dealer_display}{dealer_value_display}",
            inline=False
        )
        
        embed.add_field(
            name="👤 Your Hand",
            value=f"{self._format_cards(self.player_cards)} (Value: {player_value})",
            inline=False
        )
        
        embed.add_field(
            name="💰 Bet Amount",
            value=f"${self.bet_amount:,}",
            inline=True
        )
        
        # Check for game end conditions
        if self.game_over:
            result = self._determine_winner()
            embed.add_field(
                name="🎯 Result",
                value=result["message"],
                inline=False
            )
            embed.color = 0x00ff00 if result["player_wins"] else 0xff0000
        elif player_value > 21:
            embed.add_field(
                name="💥 BUST!",
                value="You went over 21. Dealer wins!",
                inline=False
            )
            embed.color = 0xff0000
        
        return embed
    
    def _determine_winner(self):
        """Determine the winner and calculate payout"""
        player_value = self._calculate_hand_value(self.player_cards)
        dealer_value = self._calculate_hand_value(self.dealer_cards)
        
        if player_value > 21:
            return {"player_wins": False, "message": "💥 BUST! You went over 21. Dealer wins!", "payout": 0}
        elif dealer_value > 21:
            return {"player_wins": True, "message": "🎉 Dealer busts! You win!", "payout": self.bet_amount * 2}
        elif player_value == 21 and len(self.player_cards) == 2:
            if dealer_value == 21 and len(self.dealer_cards) == 2:
                return {"player_wins": None, "message": "🤝 Push! Both have blackjack.", "payout": self.bet_amount}
            else:
                return {"player_wins": True, "message": "🔥 BLACKJACK! You win!", "payout": int(self.bet_amount * 2.5)}
        elif dealer_value == 21 and len(self.dealer_cards) == 2:
            return {"player_wins": False, "message": "🎩 Dealer has blackjack. Dealer wins!", "payout": 0}
        elif player_value > dealer_value:
            return {"player_wins": True, "message": "🎉 You win with a higher hand!", "payout": self.bet_amount * 2}
        elif dealer_value > player_value:
            return {"player_wins": False, "message": "🎩 Dealer wins with a higher hand!", "payout": 0}
        else:
            return {"player_wins": None, "message": "🤝 Push! It's a tie.", "payout": self.bet_amount}
    
    @discord.ui.button(label="🎯 HIT", style=discord.ButtonStyle.primary, row=0)
    async def hit(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This blackjack table belongs to another player.", ephemeral=True)
            return
            
        if self.game_over:
            return
            
        # Deal another card to player
        self.player_cards.append(self.deck.pop())
        player_value = self._calculate_hand_value(self.player_cards)
        
        if player_value > 21:
            # Player busts
            self.game_over = True
            await self._process_game_end(interaction, {"player_wins": False, "message": "💥 BUST! You went over 21.", "payout": 0})
        else:
            embed = self.create_game_embed()
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="✋ STAND", style=discord.ButtonStyle.secondary, row=0)
    async def stand(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This blackjack table belongs to another player.", ephemeral=True)
            return
            
        if self.game_over:
            return
            
        self.player_stood = True
        await self._dealer_play(interaction)
    
    @discord.ui.button(label="🔙 Back to Casino", style=discord.ButtonStyle.secondary, row=1)
    async def back_to_casino(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user and interaction.user.id != self.user_id:
            await interaction.response.send_message("This session belongs to another player.", ephemeral=True)
            return
            
        current_balance = await self.get_current_balance()
        casino_view = CasinoMainView(self.bot, self.guild_id, self.user_id, current_balance)
        embed = casino_view.create_main_embed()
        await interaction.response.edit_message(embed=embed, view=casino_view)
    
    async def _dealer_play(self, interaction: discord.Interaction):
        """Execute dealer's turn following standard blackjack rules"""
        await interaction.response.defer()
        
        # Dealer hits on 16 and below, stands on 17 and above
        while self._calculate_hand_value(self.dealer_cards) < 17:
            self.dealer_cards.append(self.deck.pop())
            await asyncio.sleep(1)  # Add suspense
        
        self.game_over = True
        result = self._determine_winner()
        await self._process_game_end(interaction, result)
    
    async def _process_game_end(self, interaction: discord.Interaction, result):
        """Process the end of the game and update balance"""
        # Deduct original bet
        await self.update_balance(-self.bet_amount)
        
        # Add payout if player wins or ties
        if result["payout"] > 0:
            await self.update_balance(result["payout"])
        
        embed = self.create_game_embed()
        
        # Remove hit/stand buttons
        self.clear_items()
        self.add_item(discord.ui.Button(label="🔙 Back to Casino", style=discord.ButtonStyle.secondary, custom_id="back"))
        
        try:

        
            pass
            pass
            pass
            await interaction.edit_original_response(embed=embed, view=self)
        except:
            await interaction.followup.edit_message(interaction.message.id, embed=embed, view=self)
    
    async def get_current_balance(self):
        """Get user's current balance"""
        try:

            pass
            pass
            pass
            wallet = await self.bot.db_manager.get_wallet(self.guild_id, self.user_id)
            return wallet.get('balance', 0)
        except Exception:
            return 0
    
    async def update_balance(self, amount):
        """Update user's balance"""
        try:

            pass
            pass
            pass
            operation = "add" if amount >= 0 else "subtract"
            return await self.bot.db_manager.update_wallet(
                self.guild_id, self.user_id, abs(amount), operation
            )
        except Exception:
            return False

class ProfessionalCasino(discord.Cog):
    """Professional casino system with sophisticated UI"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def check_premium_access(self, guild_id: int) -> bool:
        """Check if guild has premium access - unified validation"""
        try:

            pass
            pass
            pass
            if hasattr(self.bot, 'premium_manager_v2'):
                return await self.bot.premium_manager_v2.has_premium_access(guild_id)
            else:
                return False
        except Exception as e:
            logger.error(f"Premium access check failed: {e}")
            return False
    
    @discord.slash_command(name="casino", description="Enter the Emerald Elite Casino - Professional Gaming Experience")
    async def casino(self, ctx: discord.ApplicationContext):
        """Main casino command with professional interface"""
        # IMMEDIATE defer - must be first line to prevent timeout
        await ctx.defer()
        
        try:

        
            pass
            pass
            if not ctx.guild:
                await ctx.followup.send("This command can only be used in a server.", ephemeral=True)
                return
            
            guild_id = ctx.guild.id
            user_id = ctx.user.id
            
            # Check premium access
            if not await self.check_premium_access(guild_id):
                embed = discord.Embed(
                    title="🔒 Premium Access Required",
                    description="The Emerald Elite Casino requires premium subscription.",
                    color=0xFF6B6B
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            # Get user balance
            wallet = await self.bot.db_manager.get_wallet(guild_id, user_id)
            balance = wallet.get("balance", 0)
            
            if balance < 10:
                embed = discord.Embed(
                    title="⚠️ Insufficient Funds",
                    description="You need at least $10 to enter the casino. Use `/work` to earn money!",
                    color=0xFFD700
                )
                await ctx.respond(embed=embed, ephemeral=True)
                return
            
            # Create professional casino interface
            casino_view = CasinoMainView(self.bot, guild_id, user_id, balance)
            embed = casino_view.create_main_embed()
            
            await ctx.respond(embed=embed, view=casino_view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Casino error: {e}")
            await ctx.respond("Casino temporarily offline. Please try again.", ephemeral=True)

def setup(bot):
    bot.add_cog(ProfessionalCasino(bot))