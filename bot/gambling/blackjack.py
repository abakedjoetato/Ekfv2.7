"""
Blackjack Game Implementation
Advanced blackjack with dealer AI and card counting prevention
"""

import random
import logging
from typing import Dict, List, Tuple, Optional
import discord
from .core import GamblingCore, BetValidation, GameSession

logger = logging.getLogger(__name__)

class Card:
    """Playing card representation"""
    
    def __init__(self, suit: str, rank: str):
        self.suit = suit
        self.rank = rank
        
    @property
    def value(self) -> int:
        """Get card value for blackjack"""
        if self.rank in ['J', 'Q', 'K']:
            return 10
        elif self.rank == 'A':
            return 11  # Ace handling done in hand calculation
        else:
            return int(self.rank)
            
    def __str__(self) -> str:
        return f"{self.rank}{self.suit}"

class BlackjackHand:
    """Blackjack hand with ace handling"""
    
    def __init__(self):
        self.cards: List[Card] = []
        
    def add_card(self, card: Card):
        """Add card to hand"""
        self.cards.append(card)
        
    @property
    def value(self) -> int:
        """Calculate hand value with ace adjustment"""
        total = sum(card.value for card in self.cards)
        aces = sum(1 for card in self.cards if card.rank == 'A')
        
        # Adjust for aces
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
            
        return total
        
    @property
    def is_blackjack(self) -> bool:
        """Check if hand is blackjack"""
        return len(self.cards) == 2 and self.value == 21
        
    @property
    def is_bust(self) -> bool:
        """Check if hand is bust"""
        return self.value > 21
        
    def __str__(self) -> str:
        return " ".join(str(card) for card in self.cards)

class BlackjackGame:
    """Advanced blackjack implementation"""
    
    def __init__(self, gambling_core: GamblingCore):
        self.core = gambling_core
        self.deck = self._create_deck()
        self.sessions: Dict[int, 'BlackjackSession'] = {}
        
    def _create_deck(self) -> List[Card]:
        """Create shuffled deck"""
        suits = ['♠', '♥', '♦', '♣']
        ranks = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [Card(suit, rank) for suit in suits for rank in ranks]
        random.shuffle(deck)
        return deck
        
    def deal_card(self) -> Card:
        """Deal card from deck"""
        if len(self.deck) < 10:  # Reshuffle when low
            self.deck = self._create_deck()
        return self.deck.pop()
        
    async def start_game(self, ctx: discord.ApplicationContext, bet_amount: int) -> discord.Embed:
        """Start new blackjack game"""
        try:
            # Validate bet
            balance = await self.core.get_user_balance(ctx.guild_id, ctx.user.id if ctx.user else 0)
            valid, error_msg = BetValidation.validate_bet_amount(bet_amount, balance)
            
            if not valid:
                embed = discord.Embed(
                    title="❌ Invalid Bet",
                    description=error_msg,
                    color=0xff0000
                )
                return embed
                
            # Check for existing session
            if ctx.user.id if ctx.user else 0 in self.sessions:
                embed = discord.Embed(
                    title="⚠️ Game in Progress",
                    description="You already have an active blackjack game",
                    color=0xffaa00
                )
                return embed
                
            # Deduct bet
            success = await self.core.update_user_balance(
                ctx.guild_id, ctx.user.id if ctx.user else 0, -bet_amount, f"Blackjack bet: ${bet_amount:,}"
            )
            
            if not success:
                embed = discord.Embed(
                    title="❌ Transaction Failed", 
                    description="Unable to process bet",
                    color=0xff0000
                )
                return embed
                
            # Create game session
            session = BlackjackSession(ctx.user.id if ctx.user else 0, ctx.guild_id, bet_amount)
            
            # Deal initial cards
            session.player_hand.add_card(self.deal_card())
            session.dealer_hand.add_card(self.deal_card())
            session.player_hand.add_card(self.deal_card())
            session.dealer_hand.add_card(self.deal_card())
            
            self.sessions[ctx.user.id if ctx.user else 0] = session
            
            # Check for blackjack
            if session.player_hand.is_blackjack:
                return await self._handle_blackjack(session)
                
            return self._create_game_embed(session, False)
            
        except Exception as e:
            logger.error(f"Blackjack start error: {e}")
            embed = discord.Embed(
                title="❌ Game Error",
                description="Failed to start game",
                color=0xff0000
            )
            return embed
            
    def _create_game_embed(self, session: 'BlackjackSession', show_dealer: bool = False) -> discord.Embed:
        """Create game state embed"""
        dealer_cards = str(session.dealer_hand) if show_dealer else f"{session.dealer_hand.cards[0]} ?"
        dealer_value = session.dealer_hand.value if show_dealer else "?"
        
        embed = discord.Embed(
            title="🃏 EMERALD BLACKJACK",
            color=0x2f3136
        )
        
        embed.add_field(
            name="🎩 Dealer",
            value=f"**Cards:** {dealer_cards}\n**Value:** {dealer_value}",
            inline=False
        )
        
        embed.add_field(
            name="👤 Your Hand",
            value=f"**Cards:** {session.player_hand}\n**Value:** {session.player_hand.value}",
            inline=False
        )
        
        embed.add_field(
            name="💰 Bet",
            value=f"${session.bet_amount:,}",
            inline=True
        )
        
        return embed

class BlackjackSession(GameSession):
    """Blackjack game session"""
    
    def __init__(self, user_id: int, guild_id: int, bet_amount: int):
        super().__init__(user_id, guild_id, bet_amount)
        self.player_hand = BlackjackHand()
        self.dealer_hand = BlackjackHand()
        self.doubled_down = False