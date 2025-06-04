"""
Resource Management System
Centralizes Discord.File creation and asset management
"""

import logging
from pathlib import Path
from typing import Dict, Optional
import discord

logger = logging.getLogger(__name__)

class ResourceManager:
    """Centralized resource and asset management"""
    
    def __init__(self):
        self.asset_cache: Dict[str, bytes] = {}
        self.asset_path = Path("./assets")
        self.preload_assets()
        
    def preload_assets(self):
        """Preload commonly used assets into memory"""
        try:
            common_assets = [
                "main.png", "Killfeed.png", "Connections.png", 
                "Mission.png", "Airdrop.png", "HeliCrash.png",
                "Trader.png", "Leaderboard.png", "WeaponStats.png"
            ]
            
            for asset_name in common_assets:
                asset_path = self.asset_path / asset_name
                if asset_path.exists():
                    with open(asset_path, 'rb') as f:
                        self.asset_cache[asset_name] = f.read()
                    logger.debug(f"Preloaded asset: {asset_name}")
                    
        except Exception as e:
            logger.error(f"Asset preloading failed: {e}")
            
    def get_discord_file(self, filename: str) -> Optional[discord.File]:
        """Get Discord.File from cache or filesystem"""
        try:
            if filename in self.asset_cache:
                # Create from cached bytes
                import io
                file_obj = io.BytesIO(self.asset_cache[filename])
                return discord.File(file_obj, filename=filename)
            else:
                # Fallback to filesystem
                asset_path = self.asset_path / filename
                if asset_path.exists():
                    return discord.File(str(asset_path), filename=filename)
                    
            logger.warning(f"Asset not found: {filename}")
            return None
            
        except Exception as e:
            logger.error(f"Error creating Discord file for {filename}: {e}")
            return None
            
    def cleanup_resources(self):
        """Clean up cached resources"""
        self.asset_cache.clear()
        logger.info("Resource cache cleared")