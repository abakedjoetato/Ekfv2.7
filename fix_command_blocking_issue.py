"""
Fix Command Blocking Issue - Resolve coroutine execution problems in cached database manager
The diagnosis shows database queries work but coroutine handling is broken in the cache layer
"""

import os
import asyncio

def fix_command_blocking_issue():
    """Fix the command blocking issue by bypassing problematic cache layer"""
    print("🔧 FIXING COMMAND BLOCKING ISSUE")
    print("=" * 50)
    
    # The diagnosis revealed that while individual operations work,
    # the cached database manager has coroutine execution issues
    # Solution: Temporarily bypass cache for slash commands
    
    # Fix 1: Modify main.py to use direct database manager for commands
    main_py_path = "main.py"
    
    if os.path.exists(main_py_path):
        with open(main_py_path, 'r') as f:
            content = f.read()
        
        # Replace cached database manager with direct database manager for command execution
        original_content = content
        
        # Find the database manager assignment
        cache_assignment = """        # Wrap with caching layer
        bot.db_manager = create_cached_database_manager(base_db_manager)"""
        
        direct_assignment = """        # Use direct database manager to avoid cache blocking issues
        bot.db_manager = base_db_manager
        
        # Store cached version separately for parsers
        bot.cached_db_manager = create_cached_database_manager(base_db_manager)"""
        
        content = content.replace(cache_assignment, direct_assignment)
        
        if content != original_content:
            with open(main_py_path, 'w') as f:
                f.write(content)
            print("✅ Fixed main.py to use direct database manager for commands")
        else:
            print("ℹ️ main.py already using correct database configuration")
    
    # Fix 2: Update parsers to use cached database manager
    parser_files = [
        "bot/parsers/scalable_killfeed_parser.py",
        "bot/parsers/scalable_unified_parser.py"
    ]
    
    for parser_file in parser_files:
        if os.path.exists(parser_file):
            with open(parser_file, 'r') as f:
                content = f.read()
            
            original_content = content
            
            # Replace self.bot.db_manager with self.bot.cached_db_manager for parsers
            content = content.replace("self.bot.db_manager", "getattr(self.bot, 'cached_db_manager', self.bot.db_manager)")
            
            if content != original_content:
                with open(parser_file, 'w') as f:
                    f.write(content)
                print(f"✅ Updated {parser_file} to use cached database manager")
    
    # Fix 3: Add emergency fallback to cached database manager
    cache_integration_path = "bot/utils/cache_integration.py"
    
    if os.path.exists(cache_integration_path):
        with open(cache_integration_path, 'r') as f:
            content = f.read()
        
        # Add timeout protection to the __getattr__ method
        original_getattr = """    def __getattr__(self, name):
        \"\"\"Pass through any missing methods to the underlying database manager\"\"\"
        return getattr(self.db, name)"""
        
        fixed_getattr = """    def __getattr__(self, name):
        \"\"\"Pass through any missing methods to the underlying database manager with timeout protection\"\"\"
        attr = getattr(self.db, name)
        
        # If it's a callable method, wrap it with timeout protection
        if callable(attr):
            async def wrapped_method(*args, **kwargs):
                try:
                    if asyncio.iscoroutinefunction(attr):
                        return await asyncio.wait_for(attr(*args, **kwargs), timeout=10.0)
                    else:
                        return attr(*args, **kwargs)
                except asyncio.TimeoutError:
                    logger.error(f"Database operation {name} timed out")
                    raise
                except Exception as e:
                    logger.error(f"Database operation {name} failed: {e}")
                    raise
            
            # Return the wrapped method if it's async, otherwise return as-is
            if asyncio.iscoroutinefunction(attr):
                return wrapped_method
        
        return attr"""
        
        content = content.replace(original_getattr, fixed_getattr)
        
        with open(cache_integration_path, 'w') as f:
            f.write(content)
        print("✅ Added timeout protection to cached database manager")
    
    print("🎯 COMMAND BLOCKING FIXES APPLIED")
    print("   - Direct database access for slash commands")
    print("   - Cached database access for parsers") 
    print("   - Timeout protection for cache operations")
    
    return True

if __name__ == "__main__":
    fix_command_blocking_issue()