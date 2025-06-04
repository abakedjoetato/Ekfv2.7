"""
Create Rate Limit Cooldown Files - Stop excessive Discord API calls
This creates cooldown files to prevent the bot from making too many API requests
"""

import os
from datetime import datetime, timedelta

def create_cooldowns():
    """Create cooldown files to prevent excessive Discord API calls"""
    
    # Create command sync cooldown (6 hours)
    command_cooldown_time = datetime.utcnow() + timedelta(hours=6)
    with open('command_sync_cooldown.txt', 'w') as f:
        f.write(command_cooldown_time.isoformat())
    
    # Create global sync cooldown (1 hour)
    global_cooldown_time = datetime.utcnow() + timedelta(hours=1)
    with open('global_sync_cooldown.txt', 'w') as f:
        f.write(global_cooldown_time.isoformat())
    
    print("Created cooldown files:")
    print(f"Command sync cooldown until: {command_cooldown_time}")
    print(f"Global sync cooldown until: {global_cooldown_time}")
    
    # Create command hash to track changes
    with open('command_hash.txt', 'w') as f:
        f.write('rate_limit_protection_enabled')
    
    print("Created command hash file for change tracking")

if __name__ == "__main__":
    create_cooldowns()