"""
Emerald's Killfeed - Embed Factory
Advanced embed creation with themed messaging and elite visual design
"""

import discord
from datetime import datetime, timezone
from pathlib import Path
import logging
import random
import re
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

def should_use_inline(field_value: str, max_inline_chars: int = 20) -> bool:
    """Determine if field should be inline based on content length to prevent wrapping"""
    # Remove Discord formatting for accurate length calculation
    clean_text = re.sub(r'[*`_~<>:]', '', str(field_value))
    return len(clean_text) <= max_inline_chars

class EmbedFactory:
    """Elite embed factory with 10/10 visual quality and advanced analytics"""
    
    @staticmethod
    def get_thumbnail_for_type(embed_type: str) -> Tuple[str, str]:
        """Get correct thumbnail file and filename for embed type"""
        
        thumbnail_mappings = {
            'killfeed': 'Killfeed.png',
            'suicide': 'Killfeed.png', 
            'falling': 'Killfeed.png',
            'connection': 'Connections.png',
            'mission': 'Mission.png',
            'airdrop': 'Airdrop.png',
            'helicrash': 'Helicrash.png',
            'trader': 'Trader.png',
            'vehicle': 'Killfeed.png',
            'leaderboard': 'Leaderboard.png',
            'stats': 'WeaponStats.png',
            'bounty': 'Bounty.png',
            'faction': 'Faction.png',
            'gambling': 'Gamble.png',
            'economy': 'main.png',
            'work': 'main.png',
            'balance': 'main.png',
            'premium': 'main.png',
            'profile': 'main.png', 
            'admin': 'main.png',
            'error': 'main.png',
            'success': 'main.png',
            'info': 'main.png'
        }
        
        thumbnail = thumbnail_mappings.get(embed_type.lower(), 'main.png')
        return f"./assets/{thumbnail}", thumbnail


    # Asset paths validation
    ASSETS_PATH = Path('./assets')

    # Enhanced color scheme with gradients and elite styling
    COLORS = {
        'killfeed': 0xFFD700,    # Gold for elite kills
        'suicide': 0xDC143C,     # Crimson red for suicides
        'falling': 0x9370DB,     # Medium slate blue for falling
        'connection': 0x32CD32,  # Lime green for connections
        'mission': 0x4169E1,     # Royal blue for missions
        'airdrop': 0xFF8C00,     # Dark orange for airdrops
        'helicrash': 0xFF4500,   # Orange red for helicrashes
        'trader': 0x9932CC,      # Dark orchid for traders
        'vehicle': 0x696969,     # Dim gray for vehicles
        'success': 0x00FF32,     # Bright green for success
        'error': 0xFF1493,       # Deep pink for errors
        'warning': 0xFFD700,     # Gold for warnings
        'info': 0x00BFFF,        # Deep sky blue for info
        'bounty': 0xFF6347,      # Tomato for bounties
        'economy': 0x7CFC00,     # Lawn green for economy
        'elite': 0xFFD700,       # Gold for elite status
        'legendary': 0xFF00FF     # Magenta for legendary
    }

    # Enhanced themed message pools with military flair - no emojis
    CONNECTION_TITLES = [
        "🔷 **REINFORCEMENTS ARRIVE**",
        "🔷 **OPERATIVE DEPLOYED**", 
        "🔷 **COMBATANT ONLINE**",
        "🔷 **WARRIOR ACTIVE**",
        "🔷 **ASSET MOBILIZED**"
    ]

    CONNECTION_DESCRIPTIONS = [
        "New player has joined the server",
        "Elite operative enters the battlefield",
        "Combat asset successfully deployed",
        "Legendary warrior joins the fight",
        "Tactical reinforcement activated"
    ]

    DISCONNECTION_TITLES = [
        "🔻 **EXTRACTION CONFIRMED**",
        "🔻 **OPERATIVE WITHDRAWN**",
        "🔻 **COMBAT COMPLETE**", 
        "🔻 **MISSION CONCLUDED**",
        "🔻 **ASSET OFFLINE**"
    ]

    DISCONNECTION_DESCRIPTIONS = [
        "Player has left the server",
        "Operative extraction successful",
        "Combat mission concluded",
        "Tactical withdrawal completed",
        "Asset deactivated from sector"
    ]

    MISSION_READY_TITLES = [
        "**CLASSIFIED OPERATION DECLASSIFIED**",
        "**HIGH-VALUE TARGET ACQUIRED**", 
        "**ELIMINATION CONTRACT ACTIVE**",
        "**DEATH WARRANT AUTHORIZATION**",
        "**BLADE PROTOCOL ENGAGED**",
        "**ELITE MISSION PARAMETERS**",
        "**LEGENDARY OBJECTIVE AVAILABLE**",
        "**DIAMOND TIER OPERATION**",
        "**COMMANDER'S SPECIAL ASSIGNMENT**",
        "**CHAMPIONSHIP ELIMINATION ROUND**"
    ]

    MISSION_READY_DESCRIPTIONS = [
        "**CRITICAL PRIORITY** • Elite operatives required for high-stakes engagement",
        "**MAXIMUM THREAT LEVEL** • Only the deadliest warriors need apply", 
        "**EXPLOSIVE OPPORTUNITY** • Massive rewards await skilled tacticians",
        "**PRECISION STRIKE REQUIRED** • Legendary marksmen to the front lines",
        "**LIGHTNING OPERATION** • Swift execution demanded for success",
        "**INFERNO PROTOCOL** • Enter the flames and emerge victorious",
        "**DEATH'S EMBRACE** • Where angels fear to tread, legends are born",
        "**STELLAR MISSION** • Reach for the stars through fields of fire",
        "**DIAMOND STANDARD** • Only perfection survives this crucible",
        "**CHAMPIONSHIP TIER** • Prove your worth among immortals"
    ]

    # Enhanced killfeed titles with analytics integration - no emojis
    KILL_TITLES = [
        "**COMBAT SUPERIORITY ACHIEVED**",
        "**TARGET NEUTRALIZATION COMPLETE**",
        "**PRECISION ELIMINATION CONFIRMED**",
        "**TACTICAL DOMINANCE DISPLAYED**",
        "**LIGHTNING STRIKE EXECUTED**",
        "**MASTERCLASS ELIMINATION**",
        "**LEGENDARY TAKEDOWN**",
        "**CHAMPIONSHIP KILL**",
        "**BLADE DANCE FINALE**",
        "**ROYAL EXECUTION**"
    ]

    # Gritty survivalist kill messages
    KILL_MESSAGES = [
        "Another heartbeat silenced beneath the ash sky",
        "No burial, no name — just silence where a soul once stood",
        "Left no echo. Just scattered gear and cooling blood",
        "Cut from the world like thread from a fraying coat",
        "Hunger, cold, bullets — it could've been any of them. It was enough",
        "Marked, hunted, forgotten. In that order",
        "Their fire went out before they even knew they were burning",
        "A last breath swallowed by wind and war",
        "The price of survival paid in someone else's blood",
        "The map didn't change. The player did"
    ]

    SUICIDE_TITLES = [
        "**CRITICAL SYSTEM FAILURE**",
        "**TACTICAL ERROR FATAL**",
        "**OPERATION SELF-DESTRUCT**",
        "**MISSION COMPROMISED**",
        "**EMERGENCY PROTOCOL ACTIVATED**",
        "**SYSTEM OVERLOAD CRITICAL**",
        "**MELTDOWN SEQUENCE COMPLETE**",
        "**OPERATOR DOWN - INTERNAL**",
        "**CHAOS THEORY IN ACTION**",
        "**TRAGIC PERFORMANCE**"
    ]

    # Deadpan dark humor suicide messages
    SUICIDE_MESSAGES = [
        "Hit relocate like it was the snooze button. Got deleted",
        "Tactical redeployment... into the abyss",
        "Rage respawned and logic respawned with it",
        "Wanted a reset. Got a reboot straight to the void",
        "Pressed something. Paid everything",
        "Who needs enemies when you've got bad decisions?",
        "Alt+F4'd themselves into Valhalla",
        "Strategic death — poorly executed",
        "Fast travel without a destination",
        "Confirmed: the dead menu is not a safe zone"
    ]

    # Enhanced falling death titles - no emojis
    FALLING_TITLES = [
        "**GRAVITY ENFORCEMENT PROTOCOL**",
        "**ALTITUDE ADJUSTMENT FATAL**",
        "**TERMINAL VELOCITY ACHIEVED**",
        "**GROUND IMPACT CONFIRMED**",
        "**ELEVATION ERROR CORRECTED**",
        "**PHYSICS LESSON CONCLUDED**",
        "**DESCENT PROTOCOL FAILED**",
        "**VERTICAL MISCALCULATION**",
        "**FLIGHT PLAN TERMINATED**",
        "**LANDING COORDINATES INCORRECT**"
    ]

    # Sardonic falling messages
    FALLING_MESSAGES = [
        "Thought they could make it. The ground disagreed",
        "Airborne ambition. Terminal results",
        "Tried flying. Landed poorly",
        "Gravity called. They answered — headfirst",
        "Believed in themselves. Gravity didn't",
        "From rooftops to regret in under two seconds",
        "The sky opened. The floor closed",
        "Survival instincts took a coffee break",
        "Feet first into a bad decision",
        "Their plan had one fatal step too many"
    ]

    # Enhanced airdrop titles - no emojis
    AIRDROP_TITLES = [
        "**TACTICAL SUPPLY DEPLOYMENT**",
        "**HIGH-VALUE CARGO INBOUND**",
        "**GIFT FROM THE GODS**",
        "**TREASURE CHEST DESCENDING**",
        "**LEGENDARY LOOT PACKAGE**",
        "**CHAMPIONSHIP REWARDS**",
        "**LIGHTNING DELIVERY**",
        "**INFERNO SUPPLIES**",
        "**ROYAL CARE PACKAGE**",
        "**PRECISION DROP ZONE**"
    ]

    # Enhanced helicrash titles - no emojis
    HELICRASH_TITLES = [
        "**BIRD OF STEEL GROUNDED**",
        "**AVIATION CATASTROPHE**",
        "**MECHANICAL PHOENIX DOWN**",
        "**SKY CHARIOT TERMINATED**",
        "**IRON ANGEL FALLEN**",
        "**STELLAR CRASH LANDING**",
        "**PRECIOUS METAL SCATTERED**",
        "**CHAMPIONSHIP WRECKAGE**",
        "**TARGET PRACTICE COMPLETE**",
        "**ROYAL AIRCRAFT DOWN**"
    ]

    # Enhanced trader titles - no emojis
    TRADER_TITLES = [
        "**BLACK MARKET MAGNATE**",
        "**SHADOW MERCHANT PRINCE**",
        "**DIAMOND DEALER ACTIVE**",
        "**CHAMPIONSHIP TRADER**",
        "**LIGHTNING MERCHANT**",
        "**INFERNO BUSINESSMAN**",
        "**STELLAR SALESMAN**",
        "**ROYAL ARMS DEALER**",
        "**PRECISION SUPPLIER**",
        "**DEATH'S QUARTERMASTER**"
    ]

    # Mission mappings for readable names
    MISSION_MAPPINGS = {
        'GA_Airport_mis_01_SFPSACMission': 'Airport Mission #1',
        'GA_Airport_mis_02_SFPSACMission': 'Airport Mission #2',
        'GA_Airport_mis_03_SFPSACMission': 'Airport Mission #3',
        'GA_Airport_mis_04_SFPSACMission': 'Airport Mission #4',
        'GA_Military_02_Mis1': 'Military Base Mission #2',
        'GA_Military_03_Mis_01': 'Military Base Mission #3',
        'GA_Military_04_Mis1': 'Military Base Mission #4',
        'GA_Beregovoy_Mis1': 'Beregovoy Settlement Mission',
        'GA_Settle_05_ChernyLog_Mis1': 'Cherny Log Settlement Mission',
        'GA_Ind_01_m1': 'Industrial Zone Mission #1',
        'GA_Ind_02_Mis_1': 'Industrial Zone Mission #2',
        'GA_KhimMash_Mis_01': 'Chemical Plant Mission #1',
        'GA_KhimMash_Mis_02': 'Chemical Plant Mission #2',
        'GA_Bunker_01_Mis1': 'Underground Bunker Mission',
        'GA_Sawmill_01_Mis1': 'Sawmill Mission #1',
        'GA_Settle_09_Mis_1': 'Settlement Mission #9',
        'GA_Military_04_Mis_2': 'Military Base Mission #4B',
        'GA_PromZone_6_Mis_1': 'Industrial Zone Mission #6',
        'GA_PromZone_Mis_01': 'Industrial Zone Mission A',
        'GA_PromZone_Mis_02': 'Industrial Zone Mission B',
        'GA_Kamensk_Ind_3_Mis_1': 'Kamensk Industrial Mission',
        'GA_Kamensk_Mis_1': 'Kamensk City Mission #1',
        'GA_Kamensk_Mis_2': 'Kamensk City Mission #2',
        'GA_Kamensk_Mis_3': 'Kamensk City Mission #3',
        'GA_Krasnoe_Mis_1': 'Krasnoe City Mission',
        'GA_Vostok_Mis_1': 'Vostok City Mission',
        'GA_Lighthouse_02_Mis1': 'Lighthouse Mission #2',
        'GA_Elevator_Mis_1': 'Elevator Complex Mission #1',
        'GA_Elevator_Mis_2': 'Elevator Complex Mission #2',
        'GA_Sawmill_02_1_Mis1': 'Sawmill Mission #2A',
        'GA_Sawmill_03_Mis_01': 'Sawmill Mission #3',
        'GA_Bochki_Mis_1': 'Barrel Storage Mission',
        'GA_Dubovoe_0_Mis_1': 'Dubovoe Resource Mission',
    }

    @staticmethod
    def normalize_mission_name(mission_id: str) -> str:
        """Convert mission ID to readable name"""
        return EmbedFactory.MISSION_MAPPINGS.get(mission_id, mission_id.replace('_', ' ').title())

    @staticmethod
    def get_mission_level(mission_id: str) -> int:
        """Determine mission difficulty level"""
        if any(x in mission_id.lower() for x in ['airport', 'military', 'bunker']):
            return 4  # High difficulty
        elif any(x in mission_id.lower() for x in ['industrial', 'chemical', 'kamensk']):
            return 3  # Medium-high difficulty
        elif any(x in mission_id.lower() for x in ['settlement', 'sawmill']):
            return 2  # Medium difficulty
        else:
            return 1  # Low difficulty

    @staticmethod
    def get_threat_level_display(level: int) -> str:
        """Get enhanced threat level display"""
        threat_displays = {
            1: "**LOW THREAT** - Rookie Operations",
            2: "**MEDIUM THREAT** - Veteran Required", 
            3: "**HIGH THREAT** - Elite Operatives Only",
            4: "**CRITICAL THREAT** - Legendary Masters"
        }
        return threat_displays.get(level, "**UNKNOWN THREAT** - Proceed with Caution")

    @staticmethod
    async def build(embed_type: str, embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build embed with proper file attachment"""
        try:
            if embed_type == 'connection':
                return await EmbedFactory.build_connection_embed(embed_data)
            elif embed_type == 'disconnection':
                return await EmbedFactory.build_disconnection_embed(embed_data)
            elif embed_type == 'mission':
                return await EmbedFactory.build_mission_embed(embed_data)
            elif embed_type == 'airdrop':
                return await EmbedFactory.build_airdrop_embed(embed_data)
            elif embed_type == 'helicrash':
                return await EmbedFactory.build_helicrash_embed(embed_data)
            elif embed_type == 'trader':
                return await EmbedFactory.build_trader_embed(embed_data)
            elif embed_type == 'killfeed':
                return await EmbedFactory.build_killfeed_embed(embed_data)
            elif embed_type == 'leaderboard':
                return await EmbedFactory.build_leaderboard_embed(embed_data)
            elif embed_type == 'stats':
                return await EmbedFactory.build_stats_embed(embed_data)
            elif embed_type == 'bounty_set':
                return await EmbedFactory.build_bounty_set_embed(embed_data)
            elif embed_type == 'bounty_list':
                return await EmbedFactory.build_bounty_list_embed(embed_data)
            elif embed_type == 'faction_created':
                return await EmbedFactory.build_faction_created_embed(embed_data)
            elif embed_type == 'economy_balance':
                return await EmbedFactory.build_economy_balance_embed(embed_data)
            elif embed_type == 'economy_work':
                return await EmbedFactory.build_economy_work_embed(embed_data)
            else:
                return await EmbedFactory.build_generic_embed(embed_data)
        except Exception as e:
            logger.error(f"Error building {embed_type} embed: {e}")
            return await EmbedFactory.build_error_embed(f"Failed to build {embed_type} embed")

    @staticmethod
    async def build_connection_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build minimalistic connection embed - 2 FIELDS ONLY"""
        try:
            title = embed_data.get('title', random.choice(EmbedFactory.CONNECTION_TITLES))
            description = embed_data.get('description', random.choice(EmbedFactory.CONNECTION_DESCRIPTIONS))

            embed = discord.Embed(
                title=title,
                description=description,
                color=EmbedFactory.COLORS['connection'],
                timestamp=datetime.now(timezone.utc)
            )

            player_name = embed_data.get('player_name', 'Unknown Player')
            platform = embed_data.get('platform', 'Unknown')
            server_name = embed_data.get('server_name', 'Unknown Server')

            embed.add_field(name="**OPERATIVE**", value=f"**{player_name}**\n**{platform}** • **{server_name}**", inline=True)
            embed.add_field(name="**STATUS**", value="**ACTIVE** • Ready for Combat", inline=True)

            embed.set_footer(text="Powered by Emerald")

            connections_file = discord.File("./assets/Connections.png", filename="Connections.png")
            embed.set_thumbnail(url="attachment://Connections.png")

            return embed, connections_file

        except Exception as e:
            logger.error(f"Error building connection embed: {e}")
            return await EmbedFactory.build_error_embed("Connection embed error")

    @staticmethod
    async def build_disconnection_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build minimalistic disconnection embed - 2 FIELDS ONLY"""
        try:
            title = embed_data.get('title', random.choice(EmbedFactory.DISCONNECTION_TITLES))
            description = embed_data.get('description', random.choice(EmbedFactory.DISCONNECTION_DESCRIPTIONS))

            embed = discord.Embed(
                title=title,
                description=description,
                color=0xDC143C,  # Crimson red for disconnections
                timestamp=datetime.now(timezone.utc)
            )

            player_name = embed_data.get('player_name', 'Unknown Player')
            platform = embed_data.get('platform', 'Unknown')
            server_name = embed_data.get('server_name', 'Unknown Server')

            embed.add_field(name="**OPERATIVE**", value=f"**{player_name}**\n**{platform}** • **{server_name}**", inline=True)
            embed.add_field(name="**STATUS**", value="**OFFLINE** • Mission Complete", inline=True)

            embed.set_footer(text="Powered by Emerald")

            connections_file = discord.File("./assets/Connections.png", filename="Connections.png")
            embed.set_thumbnail(url="attachment://Connections.png")

            return embed, connections_file

        except Exception as e:
            logger.error(f"Error building disconnection embed: {e}")
            return await EmbedFactory.build_error_embed("Disconnection embed error")

    @staticmethod
    async def build_mission_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build elite mission embed - MINIMALISTIC 3 FIELDS"""
        try:
            mission_id = embed_data.get('mission_id', '')
            state = embed_data.get('state', 'UNKNOWN')
            level = embed_data.get('level', 1)

            if state == 'READY':
                title = random.choice(EmbedFactory.MISSION_READY_TITLES)
                description = random.choice(EmbedFactory.MISSION_READY_DESCRIPTIONS)
                color = EmbedFactory.COLORS['mission']
                status_display = "**READY** • Awaiting Deployment"
            else:
                title = "**MISSION STATUS UPDATE**"
                description = "**TACTICAL SITUATION EVOLVING** • Stand by for further orders"
                color = EmbedFactory.COLORS['info']
                status_display = f"**{state}** • Updating"

            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=datetime.now(timezone.utc)
            )

            mission_name = EmbedFactory.normalize_mission_name(mission_id)
            threat_display = EmbedFactory.get_threat_level_display(level)

            embed.add_field(name="**TARGET DESIGNATION**", value=f"**{mission_name}**\n{threat_display}", inline=False)
            embed.add_field(name="**STATUS**", value=status_display, inline=True)

            if state == 'READY':
                embed.add_field(name="**DEPLOYMENT ORDERS**", value="Deploy immediately • High-value rewards await brave operatives", inline=False)

            embed.set_footer(text="Powered by Emerald")

            mission_file = discord.File("./assets/Mission.png", filename="Mission.png")
            embed.set_thumbnail(url="attachment://Mission.png")

            return embed, mission_file

        except Exception as e:
            logger.error(f"Error building mission embed: {e}")
            return await EmbedFactory.build_error_embed("Mission embed error")

    @staticmethod
    async def build_airdrop_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build elite airdrop embed - MINIMALISTIC 3 FIELDS"""
        try:
            title = random.choice(EmbedFactory.AIRDROP_TITLES)
            description = "**High-value military assets incoming**"

            embed = discord.Embed(
                title=title,
                description=description,
                color=EmbedFactory.COLORS['airdrop'],
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="**LEGENDARY TIER**", value="Premium equipment and tactical resources", inline=False)
            embed.add_field(name="**INBOUND** • Limited Time", value="High competition expected from hostile operatives", inline=False)

            embed.set_footer(text="Powered by Emerald")

            airdrop_file = discord.File("./assets/Airdrop.png", filename="Airdrop.png")
            embed.set_thumbnail(url="attachment://Airdrop.png")

            return embed, airdrop_file

        except Exception as e:
            logger.error(f"Error building airdrop embed: {e}")
            return await EmbedFactory.build_error_embed("Airdrop embed error")

    @staticmethod
    async def build_helicrash_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build elite helicrash embed - MINIMALISTIC 3 FIELDS"""
        try:
            title = random.choice(EmbedFactory.HELICRASH_TITLES)
            description = "**Salvage opportunity in hostile territory**"

            embed = discord.Embed(
                title=title,
                description=description,
                color=EmbedFactory.COLORS['helicrash'],
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="**MILITARY GRADE**", value="High-value military equipment available", inline=False)
            embed.add_field(name="**SITE LOCATED** • Dangerous", value="Hot zone active with confirmed hostile presence", inline=False)

            embed.set_footer(text="Powered by Emerald")

            helicrash_file = discord.File("./assets/Helicrash.png", filename="Helicrash.png")
            embed.set_thumbnail(url="attachment://Helicrash.png")

            return embed, helicrash_file

        except Exception as e:
            logger.error(f"Error building helicrash embed: {e}")
            return await EmbedFactory.build_error_embed("Helicrash embed error")

    @staticmethod
    async def build_trader_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build elite trader embed - MINIMALISTIC 3 FIELDS"""
        try:
            title = random.choice(EmbedFactory.TRADER_TITLES)
            description = "**Rare commodities available for trade**"

            embed = discord.Embed(
                title=title,
                description=description,
                color=EmbedFactory.COLORS['trader'],
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="**ROYAL GRADE**", value="Premium equipment and rare commodities", inline=False)
            embed.add_field(name="**ACTIVE** • Open for Business", value="Verified trader with exclusive deals on high-tier equipment", inline=False)

            embed.set_footer(text="Powered by Emerald")

            trader_file = discord.File("./assets/Trader.png", filename="Trader.png")
            embed.set_thumbnail(url="attachment://Trader.png")

            return embed, trader_file

        except Exception as e:
            logger.error(f"Error building trader embed: {e}")
            return await EmbedFactory.build_error_embed("Trader embed error")

    @staticmethod
    async def build_advanced_stats_profile(embed_data: Dict[str, Any]) -> Tuple[discord.Embed, Optional[discord.File]]:
        """Build revolutionary 20/10 advanced military intelligence profile"""
        try:
            player_name = embed_data.get('player_name', 'Unknown Operative')
            server_name = embed_data.get('server_name', 'Unknown Theater')

            # Combat Performance Metrics
            kills = embed_data.get('kills', 0)
            deaths = embed_data.get('deaths', 0)
            kdr = float(embed_data.get('kdr', 0.0))
            suicides = embed_data.get('suicides', 0)

            # Advanced Combat Intelligence
            best_streak = embed_data.get('best_streak', 0)
            current_streak = embed_data.get('current_streak', 0)
            personal_best_distance = embed_data.get('personal_best_distance', 0.0)
            total_distance = embed_data.get('total_distance', 0.0)
            favorite_weapon = embed_data.get('favorite_weapon', 'Unknown')

            # Tactical Analysis
            most_eliminated = embed_data.get('most_eliminated_player', 'None')
            most_eliminated_count = embed_data.get('most_eliminated_count', 0)
            nemesis = embed_data.get('eliminated_by_most_player', 'None')
            nemesis_count = embed_data.get('eliminated_by_most_count', 0)
            rivalry_score = embed_data.get('rivalry_score', 0)

            # Operational Statistics
            servers_played = embed_data.get('servers_played', 0)
            weapon_stats = embed_data.get('weapon_stats', {})
            active_days = embed_data.get('active_days', 42)

            # Calculate advanced metrics
            total_engagements = kills + deaths
            survival_rate = (kills / max(total_engagements, 1)) * 100 if total_engagements > 0 else 0
            efficiency_rating = min(100, (kdr * 20) + (best_streak * 2))
            avg_engagement_distance = total_distance / max(kills, 1) if kills > 0 and total_distance > 0 else 0

            # Performance Classification System
            if kdr >= 3.0 and kills >= 100:
                classification = "ELITE OPERATOR"
                class_color = 0xFF0000  # Red
            elif kdr >= 2.0 and kills >= 50:
                classification = "VETERAN COMBATANT"
                class_color = 0xFF8C00  # Dark Orange
            elif kdr >= 1.5 and kills >= 25:
                classification = "EXPERIENCED SOLDIER"
                class_color = 0xFFD700  # Gold
            elif kdr >= 1.0:
                classification = "TACTICAL OPERATIVE"
                class_color = 0x32CD32  # Lime Green
            else:
                classification = "FIELD RECRUIT"
                class_color = 0x808080  # Gray

            # Create revolutionary embed structure
            embed = discord.Embed(
                title=f"MILITARY INTELLIGENCE PROFILE",
                description=f"**OPERATIVE:** `{player_name}`\n**THEATER:** `{server_name}`\n**CLASSIFICATION:** {classification}",
                color=class_color,
                timestamp=datetime.now(timezone.utc)
            )

            # PRIMARY COMBAT METRICS (Field 1)
            primary_metrics = (
                f"**Eliminations:** `{kills:,}`\n"
                f"**KIA Events:** `{deaths:,}`\n"
                f"**K/D Ratio:** `{kdr:.2f}`\n"
                f"**Survival Rate:** `{survival_rate:.1f}%`"
            )
            embed.add_field(
                name="PRIMARY COMBAT METRICS",
                value=primary_metrics,
                inline=should_use_inline(primary_metrics)
            )

            # TACTICAL PERFORMANCE (Field 2)
            tactical_performance = (
                f"**Current Streak:** `{current_streak}`\n"
                f"**Best Streak:** `{best_streak}`\n"
                f"**Efficiency Rating:** `{efficiency_rating:.0f}/100`\n"
                f"**Self-Eliminations:** `{suicides}`"
            )
            embed.add_field(
                name="TACTICAL PERFORMANCE",
                value=tactical_performance,
                inline=should_use_inline(tactical_performance)
            )

            # ENGAGEMENT ANALYSIS (Field 3)
            engagement_analysis = (
                f"**Total Engagements:** `{total_engagements:,}`\n"
                f"**Longest Shot:** `{personal_best_distance:.0f}m`\n"
                f"**Avg Distance:** `{avg_engagement_distance:.0f}m`\n"
                f"**Primary Weapon:** `{favorite_weapon or 'Unknown'}`"
            )
            embed.add_field(
                name="ENGAGEMENT ANALYSIS",
                value=engagement_analysis,
                inline=should_use_inline(engagement_analysis)
            )

            # RIVALRY INTELLIGENCE (Field 4)
            if most_eliminated and most_eliminated != 'None':
                rivalry_status = f"**Primary Target:** `{most_eliminated}` ({most_eliminated_count} eliminations)"
            else:
                rivalry_status = "**Primary Target:** `No significant targets`"

            if nemesis and nemesis != 'None':
                threat_assessment = f"**Known Threat:** `{nemesis}` ({nemesis_count} eliminations)"
            else:
                threat_assessment = "**Known Threat:** `No significant threats`"

            rivalry_intel = (
                f"{rivalry_status}\n"
                f"{threat_assessment}\n"
                f"**Rivalry Score:** `{rivalry_score:+d}`\n"
                f"**Threat Level:** `{'HIGH' if rivalry_score < -5 else 'MODERATE' if rivalry_score < 0 else 'LOW'}`"
            )
            embed.add_field(
                name="🔍 RIVALRY INTELLIGENCE",
                value=rivalry_intel,
                inline=should_use_inline(rivalry_intel)
            )

            # OPERATIONAL STATUS (Field 5)
            operational_status = (
                f"**Theaters Active:** `{servers_played}`\n"
                f"**Days in Field:** `{active_days}`\n"
                f"**Total Distance:** `{total_distance:,.0f}m`\n"
                f"**Weapon Systems:** `{len(weapon_stats)}`"
            )
            embed.add_field(
                name="🌍 OPERATIONAL STATUS",
                value=operational_status,
                inline=should_use_inline(operational_status)
            )

            # WEAPON PROFICIENCY (Field 6)
            if weapon_stats:
                top_weapons = sorted(weapon_stats.items(), key=lambda x: x[1], reverse=True)[:3]
                weapon_proficiency = "\n".join([
                    f"**{weapon}:** `{count}` eliminations" 
                    for weapon, count in top_weapons
                ])
            else:
                weapon_proficiency = "**No weapon data available**"

            embed.add_field(
                name="WEAPON PROFICIENCY",
                value=weapon_proficiency,
                inline=should_use_inline(weapon_proficiency)
            )

            # Footer with military timestamp
            embed.set_footer(
                text=f"Intelligence Report Generated • Powered by Discord.gg/EmeraldServers",
                icon_url="attachment://Killfeed.png"
            )

            # Attach main.png thumbnail
            main_file = discord.File("./assets/main.png", filename="main.png")
            embed.set_thumbnail(url="attachment://main.png")

            return embed, main_file

        except Exception as e:
            logger.error(f"Failed to build advanced stats profile: {e}")
            # Fallback to basic embed
            try:
                basic_embed = discord.Embed(
                    title="**OPERATIVE STATS**",
                    description=f"**{embed_data.get('player_name', 'Unknown')}**",
                    color=0x00BFFF,
                    timestamp=datetime.now(timezone.utc)
                )
                killfeed_file = discord.File("./assets/Killfeed.png", filename="Killfeed.png")
                basic_embed.set_thumbnail(url="attachment://Killfeed.png")
                return basic_embed, killfeed_file
            except Exception as fallback_error:
                logger.error(f"Fallback embed creation failed: {fallback_error}")
                # Ultimate fallback
                simple_embed = discord.Embed(title="Stats Error", color=0xFF0000)
                return simple_embed, None

    @staticmethod
    async def build_killfeed_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build elite killfeed embed with proper title pools and field structure matching screenshots"""
        try:
            # Get bot instance for database access
            from main import EmeraldKillfeedBot
            bot = EmeraldKillfeedBot._instance if hasattr(EmeraldKillfeedBot, '_instance') else None
            
            # Extract data
            killer = embed_data.get('killer', 'Unknown')
            victim = embed_data.get('victim', 'Unknown')
            weapon = embed_data.get('weapon', 'Unknown')
            distance = embed_data.get('distance', 0)
            is_suicide = embed_data.get('is_suicide', False)
            
            # Determine embed type and get appropriate pools
            if is_suicide:
                if weapon.lower() in ['falling', 'fall', 'gravity']:
                    # Falling death
                    title = random.choice(EmbedFactory.FALLING_TITLES)
                    message = random.choice(EmbedFactory.FALLING_MESSAGES)
                    color = EmbedFactory.COLORS['falling']
                    
                    embed = discord.Embed(
                        title=title,
                        color=color,
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    # Get player KDR
                    player_kdr = await EmbedFactory._get_player_kdr(bot, embed_data.get('guild_id'), killer) if bot else None
                    player_display = f"{killer} • {player_kdr} KDR" if player_kdr else killer
                    
                    embed.add_field(name="**OPERATIVE**", value=player_display, inline=False)
                    embed.add_field(name="**KIA - FALLING**", value="Falling • Physics Lesson", inline=False)
                    embed.add_field(name="**INCIDENT REPORT**", value=message, inline=False)
                    
                else:
                    # Regular suicide
                    title = random.choice(EmbedFactory.SUICIDE_TITLES)
                    message = random.choice(EmbedFactory.SUICIDE_MESSAGES)
                    color = EmbedFactory.COLORS['suicide']
                    
                    embed = discord.Embed(
                        title=title,
                        color=color,
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    # Get player KDR
                    player_kdr = await EmbedFactory._get_player_kdr(bot, embed_data.get('guild_id'), killer) if bot else None
                    player_display = f"{killer} • {player_kdr} KDR" if player_kdr else killer
                    
                    embed.add_field(name="**OPERATIVE**", value=player_display, inline=False)
                    embed.add_field(name="**KIA - INTERNAL**", value="Menu Suicide • Non-Combat Loss", inline=False)
                    embed.add_field(name="**INCIDENT REPORT**", value=message, inline=False)
                    
            else:
                # Regular kill
                title = random.choice(EmbedFactory.KILL_TITLES)
                message = random.choice(EmbedFactory.KILL_MESSAGES)
                color = EmbedFactory.COLORS['killfeed']
                
                embed = discord.Embed(
                    title=title,
                    color=color,
                    timestamp=datetime.now(timezone.utc)
                )
                
                # Get player KDRs
                killer_kdr = await EmbedFactory._get_player_kdr(bot, embed_data.get('guild_id'), killer) if bot else None
                victim_kdr = await EmbedFactory._get_player_kdr(bot, embed_data.get('guild_id'), victim) if bot else None
                
                killer_display = f"{killer} • {killer_kdr} KDR" if killer_kdr else killer
                victim_display = f"{victim} • {victim_kdr} KDR" if victim_kdr else victim
                
                embed.add_field(name="**ELIMINATOR**", value=killer_display, inline=False)
                embed.add_field(name="**ELIMINATED**", value=victim_display, inline=False)
                embed.add_field(name="**WEAPON SYSTEM**", value=f"{weapon} • {distance}m", inline=False)
                embed.add_field(name="**COMBAT REPORT**", value=message, inline=False)

            embed.set_footer(text="Powered by Emerald")
            
            # Get asset file
            asset_file = discord.File("./assets/Killfeed.png", filename="Killfeed.png")
            embed.set_thumbnail(url="attachment://Killfeed.png")

            return embed, asset_file

        except Exception as e:
            logger.error(f"Error building killfeed embed: {e}")
            return await EmbedFactory.build_error_embed("Killfeed embed error")

    @staticmethod
    async def _get_player_kdr(bot, guild_id: int, player_name: str) -> Optional[str]:
        """Get player KDR from database"""
        try:
            if not bot or not hasattr(bot, 'db_manager') or not bot.db_manager:
                return None
                
            player_data = await bot.db_manager.pvp_data.find_one({
                "guild_id": guild_id,
                "player_name": player_name
            })
            
            if player_data:
                kills = player_data.get('kills', 0)
                deaths = player_data.get('deaths', 0)
                kdr = round(kills / deaths, 2) if deaths > 0 else float(kills)
                return f"{kdr:.2f}"
            
            return "0.00"
            
        except Exception as e:
            logger.error(f"Failed to get player KDR for {player_name}: {e}")
            return None

    @staticmethod
    async def build_leaderboard_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build enhanced leaderboard embed - MINIMALISTIC 3 FIELDS"""
        try:
            title = embed_data.get('title', "**ELITE COMBAT RANKINGS**")
            description = embed_data.get('description', '**Champions ranked by battlefield supremacy**')

            embed = discord.Embed(
                title=title,
                description=description,
                color=EmbedFactory.COLORS['elite'],
                timestamp=datetime.now(timezone.utc)
            )

            rankings = embed_data.get('rankings', '')
            if rankings:
                # Use inline=False for long content to prevent text wrapping
                embed.add_field(name="**TOP WARRIORS**", value=rankings, inline=False)

            server_name = embed_data.get('server_name', 'All Servers')
            embed.add_field(name="**THEATER OF OPERATIONS**", value=f"**{server_name}**", inline=should_use_inline(f"**{server_name}**"))


            thumbnail_url = embed_data.get('thumbnail_url', 'attachment://Leaderboard.png')
            if 'WeaponStats.png' in thumbnail_url:
                asset_file = discord.File("./assets/WeaponStats.png", filename="WeaponStats.png")
            elif 'Faction.png' in thumbnail_url:
                asset_file = discord.File("./assets/Faction.png", filename="Faction.png")
            else:
                asset_file = discord.File("./assets/Leaderboard.png", filename="Leaderboard.png")

            embed.set_thumbnail(url=thumbnail_url)
            embed.set_footer(text="Powered by Emerald")

            return embed, asset_file

        except Exception as e:
            logger.error(f"Error building leaderboard embed: {e}")
            return await EmbedFactory.build_error_embed("Leaderboard embed error")

    @staticmethod
    async def build_stats_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build enhanced stats embed - MINIMALISTIC 3 FIELDS"""
        try:
            player_name = embed_data.get('player_name', 'Unknown Player')
            server_name = embed_data.get('server_name', 'Unknown Server')

            title = "**OPERATIVE DOSSIER**"
            description = f"**Complete battlefield analysis**"

            embed = discord.Embed(
                title=title,
                description=description,
                color=EmbedFactory.COLORS['info'],
                timestamp=datetime.now(timezone.utc)
            )

            kills = max(0, embed_data.get('kills', 0))
            deaths = max(0, embed_data.get('deaths', 0))
            kdr_value = embed_data.get('kdr', '0.00')

            try:
                if isinstance(kdr_value, (int, float)):
                    kdr = f"{float(kdr_value):.2f}"
                else:
                    kdr = str(kdr_value)
            except:
                kdr = "0.00"

            embed.add_field(name="**OPERATIVE**", value=f"**{player_name}**\n**{kills:,}** Eliminations • **{deaths:,}** Casualties • **{kdr}** KDR", inline=False)

            # Get best weapon and longest shot
            favorite_weapon = embed_data.get('favorite_weapon', 'AK-74')
            personal_best_distance = float(embed_data.get('personal_best_distance', 847.0))

            if personal_best_distance >= 1000:
                distance_str = f"{personal_best_distance/1000:.1f}km"
            else:
                distance_str = f"{personal_best_distance:.0f}m"

            embed.add_field(name="**PREFERRED LOADOUT**", value=f"**{favorite_weapon}** • **{distance_str}** Longest Shot", inline=should_use_inline(f"**{favorite_weapon}** • **{distance_str}** Longest Shot"))

            active_days = embed_data.get('active_days', 42)
            embed.add_field(name="**SERVICE RECORD**", value=f"**Theater:** {server_name} • **{active_days}** Active Days", inline=False)

            embed.set_footer(text="Powered by Emerald")

            main_file = discord.File("./assets/WeaponStats.png", filename="WeaponStats.png")
            embed.set_thumbnail(url="attachment://WeaponStats.png")

            return embed, main_file

        except Exception as e:
            logger.error(f"Error building stats embed: {e}")
            return await EmbedFactory.build_error_embed("Stats embed error")

    @staticmethod
    async def build_bounty_set_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build enhanced bounty set embed - MINIMALISTIC 3 FIELDS"""
        try:
            title = "**ELIMINATION CONTRACT ISSUED**"
            description = f"**High-value target designated**"

            embed = discord.Embed(
                title=title,
                description=description,
                color=EmbedFactory.COLORS['bounty'],
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="**TARGET**", value=f"**{embed_data['target_character']}**", inline=True)
            embed.add_field(name="**REWARD**", value=f"**${embed_data['bounty_amount']:,}**", inline=True)
            embed.add_field(name="**EXPIRES** • <t:{embed_data['expires_timestamp']}:R>", value="Eliminate target to claim bounty immediately", inline=False)

            embed.set_footer(text="Powered by Emerald")

            bounty_file = discord.File("./assets/Bounty.png", filename="Bounty.png")
            embed.set_thumbnail(url="attachment://Bounty.png")

            return embed, bounty_file

        except Exception as e:
            logger.error(f"Error building bounty set embed: {e}")
            return await EmbedFactory.build_error_embed("Bounty set embed error")

    @staticmethod
    async def build_bounty_list_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build enhanced bounty list embed - MINIMALISTIC 3 FIELDS"""
        try:
            embed = discord.Embed(
                title="**ACTIVE ELIMINATION CONTRACTS**",
                description=f"**{embed_data['total_bounties']}** high-value targets identified",
                color=EmbedFactory.COLORS['bounty'],
                timestamp=datetime.now(timezone.utc)
            )

            bounty_list = []
            for i, bounty in enumerate(embed_data['bounty_list'][:5], 1):  # Show max 5
                target = bounty['target_character']
                amount = bounty['amount']
                auto_indicator = " Auto" if bounty and bounty.get('auto_generated', False) else ""
                bounty_list.append(f"**{i}. {target}** - **${amount:,}**{auto_indicator}")

            embed.add_field(name="**TOP CONTRACTS**", value="\n".join(bounty_list), inline=False)
            embed.add_field(name="**PRIORITY STATUS**", value="Showing highest value targets available", inline=False)

            embed.set_footer(text="Powered by Emerald")

            bounty_file = discord.File("./assets/Bounty.png", filename="Bounty.png")
            embed.set_thumbnail(url="attachment://Bounty.png")

            return embed, bounty_file

        except Exception as e:
            logger.error(f"Error building bounty list embed: {e}")
            return await EmbedFactory.build_error_embed("Bounty list embed error")

    @staticmethod
    async def build_faction_created_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build enhanced faction created embed - MINIMALISTIC 3 FIELDS"""
        try:
            embed = discord.Embed(
                title="**FACTION ESTABLISHED**",
                description="**New military organization formed**",
                color=EmbedFactory.COLORS['success'],
                timestamp=datetime.now(timezone.utc)
            )

            faction_tag = f"**[{embed_data['faction_tag']}]**" if embed_data and embed_data.get('faction_tag') else ""
            embed.add_field(name="**ORGANIZATION**", value=f"**{embed_data['faction_name']}**\n**{embed_data['leader']}** • {faction_tag}", inline=False)

            embed.add_field(name="**ROSTER**", value=f"**{embed_data['member_count']}/{embed_data['max_members']}** Members • Active", inline=True)
            embed.add_field(name="**RECRUITMENT**", value="Use /faction invite to recruit skilled operatives", inline=False)

            embed.set_footer(text="Powered by Emerald")

            faction_file = discord.File("./assets/Faction.png", filename="Faction.png")
            embed.set_thumbnail(url="attachment://Faction.png")

            return embed, faction_file

        except Exception as e:
            logger.error(f"Error building faction created embed: {e}")
            return await EmbedFactory.build_error_embed("Faction creation embed error")

    @staticmethod
    async def build_economy_balance_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build enhanced economy balance embed - MINIMALISTIC 3 FIELDS"""
        try:
            embed = discord.Embed(
                title="**FINANCIAL STATUS REPORT**",
                description="**Economic portfolio overview**",
                color=EmbedFactory.COLORS['economy'],
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="**OPERATIVE**", value=f"**{embed_data['user_name']}**", inline=False)
            embed.add_field(name="**CURRENT BALANCE**", value=f"**${embed_data['balance']:,}**", inline=True)

            net_worth = embed_data['total_earned'] - embed_data['total_spent']
            embed.add_field(name="**FINANCIAL ANALYSIS**", value=f"**${embed_data['total_earned']:,}** Total Earned • **${embed_data['total_spent']:,}** Total Spent\n**${net_worth:,}** Net Worth • **Excellent** Credit Rating", inline=False)

            embed.set_footer(text="Powered by Emerald")

            main_file = discord.File("./assets/main.png", filename="main.png")
            embed.set_thumbnail(url="attachment://main.png")

            return embed, main_file

        except Exception as e:
            logger.error(f"Error building economy balance embed: {e}")
            return await EmbedFactory.build_error_embed("Economy balance embed error")

    @staticmethod
    async def build_economy_work_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build enhanced economy work embed - MINIMALISTIC 3 FIELDS"""
        try:
            embed = discord.Embed(
                title="**MISSION COMPLETED**",
                description=f"**{embed_data['scenario']}**",
                color=EmbedFactory.COLORS['success'],
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="**COMPENSATION**", value=f"**+${embed_data['earnings']:,}**", inline=True)
            embed.add_field(name="**NEXT ASSIGNMENT**", value="**Available in 1 hour**", inline=True)
            embed.add_field(name="**PERFORMANCE**", value="**Excellent** • Above Standard • Contract Work", inline=False)

            embed.set_footer(text="Powered by Emerald")

            main_file = discord.File("./assets/main.png", filename="main.png")
            embed.set_thumbnail(url="attachment://main.png")

            return embed, main_file

        except Exception as e:
            logger.error(f"Error building economy work embed: {e}")
            return await EmbedFactory.build_error_embed("Economy work embed error")

    @staticmethod
    async def build_generic_embed(embed_data: dict) -> tuple[discord.Embed, discord.File]:
        """Build enhanced generic embed with context-aware thumbnails"""
        try:
            embed = discord.Embed(
                title=embed_data.get('title', '**EMERALD SERVERS**'),
                description=embed_data.get('description', '**Elite Gaming Network Notification**'),
                color=EmbedFactory.COLORS['info'],
                timestamp=datetime.now(timezone.utc)
            )

            embed.set_footer(text="Powered by Emerald")

            # Determine appropriate thumbnail based on context
            embed_type = embed_data.get('embed_type', 'info')
            thumbnail_path, thumbnail_filename = EmbedFactory.get_thumbnail_for_type(embed_type)
            
            asset_file = discord.File(thumbnail_path, filename=thumbnail_filename)
            embed.set_thumbnail(url=f"attachment://{thumbnail_filename}")

            return embed, asset_file

        except Exception as e:
            logger.error(f"Error building generic embed: {e}")
            return await EmbedFactory.build_error_embed("Generic embed error")

    @staticmethod
    async def build_error_embed(error_message: str) -> tuple[discord.Embed, discord.File]:
        """Build enhanced error embed - MINIMALISTIC"""
        try:
            embed = discord.Embed(
                title="**SYSTEM ERROR**",
                description=f"**Critical malfunction detected:** *{error_message}*",
                color=EmbedFactory.COLORS['error'],
                timestamp=datetime.now(timezone.utc)
            )

            embed.add_field(name="**STATUS**", value="**OPERATION FAILED** • Error", inline=True)
            embed.add_field(name="**ACTION REQUIRED**", value="**DIAGNOSTIC NEEDED** • Investigation", inline=True)
            embed.add_field(name="**PRIORITY**", value="**High** • Immediate Attention", inline=True)

            embed.set_footer(text="Powered by Emerald")

            main_file = discord.File("./assets/main.png", filename="main.png")
            embed.set_thumbnail(url="attachment://main.png")

            return embed, main_file

        except Exception as e:
            logger.error(f"Critical error building error embed: {e}")
            embed = discord.Embed(
                title="**CRITICAL ERROR**",
                description="**Multiple system failures detected**",
                color=0xFF0000,
                timestamp=datetime.now(timezone.utc)
            )
            try:
                fallback_file = discord.File("./assets/main.png", filename="main.png")
                return embed, fallback_file
            except Exception as file_error:
                logger.error(f"Failed to load fallback file: {file_error}")
                fallback_file = discord.File("./assets/main.png", filename="main.png")
                return embed, fallback_file

    # Legacy compatibility methods (unchanged)
    @staticmethod
    def create_mission_embed(title: str, description: str, mission_id: str, level: int, state: str, respawn_time: Optional[int] = None) -> discord.Embed:
        """Create mission embed (legacy compatibility)"""
        try:
            if state == 'READY':
                color = EmbedFactory.COLORS['mission']
            elif state == 'IN_PROGRESS':
                color = 0xFFAA00
            elif state == 'COMPLETED':
                color = EmbedFactory.COLORS['success']
            else:
                color = EmbedFactory.COLORS['info']

            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=datetime.now(timezone.utc)
            )

            mission_name = EmbedFactory.normalize_mission_name(mission_id)
            embed.add_field(name="Mission", value=mission_name, inline=False)

            threat_levels = ["Low", "Medium", "High", "Critical"]
            threat_level = threat_levels[min(level-1, 3)] if level > 0 else "Unknown"
            embed.add_field(name="Threat Level", value=f"Class {level} - {threat_level}", inline=True)
            embed.add_field(name="Status", value=state.replace('_', ' ').title(), inline=True)

            if respawn_time:
                embed.add_field(name="Respawn", value=f"{respawn_time}s", inline=True)

            embed.set_footer(text="Powered by Emerald")
            embed.set_thumbnail(url="attachment://Mission.png")

            return embed

        except Exception as e:
            logger.error(f"Error creating mission embed: {e}")
            return discord.Embed(title="Error", description="Failed to create mission embed", color=0xFF0000)

    @staticmethod
    def create_airdrop_embed(state: str, location: str, timestamp: datetime) -> discord.Embed:
        """Create airdrop embed (legacy compatibility)"""
        try:
            embed = discord.Embed(
                title="🪂 Airdrop Incoming",
                description="High-value supply drop detected inbound",
                color=EmbedFactory.COLORS['airdrop'],
                timestamp=timestamp
            )

            embed.add_field(name="Drop Zone", value=location, inline=True)
            embed.add_field(name="Status", value=state.title(), inline=True)
            embed.add_field(name="Contents", value="High-Value Loot", inline=True)

            embed.set_footer(text="Powered by Emerald")
            embed.set_thumbnail(url="attachment://Airdrop.png")

            return embed

        except Exception as e:
            logger.error(f"Error creating airdrop embed: {e}")
            return discord.Embed(title="Error", description="Failed to create airdrop embed", color=0xFF0000)

    @staticmethod
    def create_helicrash_embed(location: str, timestamp: datetime) -> discord.Embed:
        """Create helicrash embed (legacy compatibility)"""
        try:
            embed = discord.Embed(
                title="🚁 Helicopter Crash",
                description="Military helicopter has crashed - salvage opportunity detected",
                color=EmbedFactory.COLORS['helicrash'],
                timestamp=timestamp
            )

            embed.add_field(name="Crash Site", value=location, inline=True)
            embed.add_field(name="Status", value="Active", inline=True)
            embed.add_field(name="Loot Type", value="Military Equipment", inline=True)

            embed.set_footer(text="Powered by Emerald")
            embed.set_thumbnail(url="attachment://Helicrash.png")

            return embed

        except Exception as e:
            logger.error(f"Error creating helicrash embed: {e}")
            return discord.Embed(title="Error", description="Failed to create helicrash embed", color=0xFF0000)

    @staticmethod
    def create_trader_embed(location: str, timestamp: datetime) -> discord.Embed:
        """Create trader embed (legacy compatibility)"""
        try:
            embed = discord.Embed(
                title="Trader Arrival",
                description="Traveling merchant has arrived with rare goods",
                color=EmbedFactory.COLORS['trader'],
                timestamp=timestamp
            )

            embed.add_field(name="Location", value=location, inline=True)
            embed.add_field(name="Status", value="Open for Business", inline=True)
            embed.add_field(name="Inventory", value="Rare Items Available", inline=True)

            embed.set_footer(text="Powered by Emerald")
            embed.set_thumbnail(url="attachment://Trader.png")

            return embed

        except Exception as e:
            logger.error(f"Error creating trader embed: {e}")
            return discord.Embed(title="Error", description="Failed to create trader embed", color=0xFF0000)

    @staticmethod
    def create_player_connect_embed(event_data: Dict[str, Any]) -> discord.Embed:
        """Create player connection embed for unified parser"""
        try:
            embed = discord.Embed(
                title="🟢 Player Connected",
                description=f"**{event_data.get('player_name', 'Unknown')}** joined the server",
                color=0x00FF00,
                timestamp=datetime.now(timezone.utc)
            )
            
            eos_id = event_data.get('eos_id', 'Unknown')
            server_name = event_data.get('server_name', 'Unknown Server')
            
            embed.add_field(name="EOS ID", value=f"`{eos_id[:16]}...`", inline=True)
            embed.add_field(name="Server", value=server_name, inline=True)
            embed.set_footer(text="Powered by Emerald")
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating player connect embed: {e}")
            return discord.Embed(title="Error", description="Failed to create connection embed", color=0xFF0000)

    @staticmethod
    def create_player_disconnect_embed(event_data: Dict[str, Any]) -> discord.Embed:
        """Create player disconnection embed for unified parser"""
        try:
            embed = discord.Embed(
                title="🔴 Player Disconnected",
                description=f"**{event_data.get('player_name', 'Unknown')}** left the server",
                color=0xFF0000,
                timestamp=datetime.now(timezone.utc)
            )
            
            eos_id = event_data.get('eos_id', 'Unknown')
            server_name = event_data.get('server_name', 'Unknown Server')
            
            embed.add_field(name="EOS ID", value=f"`{eos_id[:16]}...`", inline=True)
            embed.add_field(name="Server", value=server_name, inline=True)
            embed.set_footer(text="Powered by Emerald")
            
            return embed
            
        except Exception as e:
            logger.error(f"Error creating player disconnect embed: {e}")
            return discord.Embed(title="Error", description="Failed to create disconnection embed", color=0xFF0000)

    @staticmethod
    def create_event_embed(event_data: Dict[str, Any]) -> discord.Embed:
        """Create game event embed for unified parser"""
        try:
            event_type = event_data.get('event')
            
            if event_type == 'mission_start':
                embed = discord.Embed(
                    title="🎯 Mission Started",
                    description=f"Mission **{event_data.get('mission_name', 'Unknown')}** is now active",
                    color=0x00FF00,
                    timestamp=datetime.now(timezone.utc)
                )
            elif event_type == 'mission_end':
                embed = discord.Embed(
                    title="🎯 Mission Ended", 
                    description=f"Mission **{event_data.get('mission_name', 'Unknown')}** has ended",
                    color=0xFF0000,
                    timestamp=datetime.now(timezone.utc)
                )
            elif event_type == 'airdrop':
                embed = discord.Embed(
                    title="📦 Airdrop Event",
                    description="Supply drop incoming with valuable loot",
                    color=0x00BFFF,
                    timestamp=datetime.now(timezone.utc)
                )
            elif event_type == 'trader':
                embed = discord.Embed(
                    title="🛒 Trader Event",
                    description="Traveling merchant has arrived",
                    color=0xFF6B35,
                    timestamp=datetime.now(timezone.utc)
                )
            else:
                embed = discord.Embed(
                    title="🎮 Server Event",
                    description=f"Event: {event_type}",
                    color=0x7289DA,
                    timestamp=datetime.now(timezone.utc)
                )
            
            embed.set_footer(text="Powered by Emerald")
            return embed
            
        except Exception as e:
            logger.error(f"Error creating event embed: {e}")
            return discord.Embed(title="Error", description="Failed to create event embed", color=0xFF0000)