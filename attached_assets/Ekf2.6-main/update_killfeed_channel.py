"""
Update Killfeed Channel Configuration
Set the correct existing Discord channel for killfeed delivery
"""
import asyncio
import os
import motor.motor_asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def update_channel_config():
    """Update the killfeed channel to use an existing Discord channel"""
    try:
        # Connect to database
        mongo_uri = os.getenv('MONGO_URI')
        client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        db = client.EmeraldDB
        
        guild_id = 1219706687980568769
        
        # Use the main killfeed channel: 🔫┊killfeed (ID: 1219745194346287226)
        new_killfeed_channel = 1219745194346287226
        
        logger.info(f"Updating killfeed channel to {new_killfeed_channel}")
        
        # Update the server-specific channel for Emerald EU
        result = await db.guilds.update_one(
            {"guild_id": guild_id},
            {
                "$set": {
                    "server_channels.Emerald EU.killfeed": new_killfeed_channel,
                    "server_channels.default.killfeed": new_killfeed_channel,
                    "channels.killfeed": new_killfeed_channel  # Legacy fallback
                }
            },
            upsert=True
        )
        
        if result.modified_count > 0 or result.upserted_id:
            logger.info(f"✅ Successfully updated killfeed channel configuration")
            logger.info(f"   Server-specific: server_channels.Emerald EU.killfeed = {new_killfeed_channel}")
            logger.info(f"   Default fallback: server_channels.default.killfeed = {new_killfeed_channel}")
            logger.info(f"   Legacy fallback: channels.killfeed = {new_killfeed_channel}")
        else:
            logger.warning("No changes made to database")
            
        # Verify the update
        guild_config = await db.guilds.find_one({"guild_id": guild_id})
        if guild_config:
            server_channels = guild_config.get('server_channels', {})
            emerald_killfeed = server_channels.get('Emerald EU', {}).get('killfeed')
            default_killfeed = server_channels.get('default', {}).get('killfeed')
            legacy_killfeed = guild_config.get('channels', {}).get('killfeed')
            
            logger.info(f"\n=== Verification ===")
            logger.info(f"Emerald EU killfeed: {emerald_killfeed}")
            logger.info(f"Default killfeed: {default_killfeed}")
            logger.info(f"Legacy killfeed: {legacy_killfeed}")
        
        client.close()
        
    except Exception as e:
        logger.error(f"Failed to update channel config: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(update_channel_config())