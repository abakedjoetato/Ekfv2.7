#!/usr/bin/env python3

"""
Verify Killfeed Fix
Check if the 9-column CSV format fix is working by examining recent processing results
"""

import asyncio
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def verify_killfeed_fix():
    """Verify the killfeed fix by checking recent logs and processing"""
    try:
        logger.info("=== Verifying Killfeed 9-Column CSV Fix ===")
        
        # Check recent killfeed processing logs
        with open('bot.log', 'r') as f:
            logs = f.read()
        
        # Look for recent killfeed processing
        recent_killfeed_logs = []
        for line in logs.split('\n'):
            if 'killfeed' in line.lower() and any(keyword in line for keyword in 
                ['processing complete', 'events', 'csv', 'Processing.*lines from']):
                recent_killfeed_logs.append(line)
        
        logger.info(f"Found {len(recent_killfeed_logs)} recent killfeed-related log entries")
        
        # Show the most recent killfeed processing results
        if recent_killfeed_logs:
            logger.info("=== Recent Killfeed Processing ===")
            for log in recent_killfeed_logs[-10:]:  # Last 10 entries
                logger.info(log)
        
        # Check for any successful event detection
        success_indicators = [
            'Found killfeed event',
            'events found',
            'killfeed events'
        ]
        
        successful_processing = False
        for line in logs.split('\n'):
            if any(indicator in line for indicator in success_indicators):
                successful_processing = True
                logger.info(f"SUCCESS INDICATOR: {line}")
        
        if successful_processing:
            logger.info("✅ SUCCESS: Killfeed events are being detected!")
        else:
            logger.warning("❌ ISSUE: Still no killfeed events detected - may need further investigation")
            
            # Check for debug information about CSV parsing
            debug_lines = []
            for line in logs.split('\n'):
                if any(keyword in line for keyword in ['Failed to parse line', 'has.*columns', 'Line.*:']):
                    debug_lines.append(line)
            
            if debug_lines:
                logger.info("=== CSV Parsing Debug Info ===")
                for line in debug_lines[-5:]:  # Last 5 debug entries
                    logger.info(line)
        
        # Check scheduler status
        scheduler_lines = []
        for line in logs.split('\n'):
            if 'ScalableKillfeedParser' in line and ('scheduled' in line or 'Running' in line):
                scheduler_lines.append(line)
        
        if scheduler_lines:
            logger.info("=== Killfeed Parser Schedule Status ===")
            for line in scheduler_lines[-3:]:  # Last 3 scheduler entries
                logger.info(line)
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(verify_killfeed_fix())