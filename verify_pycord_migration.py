
#!/usr/bin/env python3
"""
Comprehensive py-cord 2.6.1 Migration Verification Script
Ensures entire codebase uses py-cord syntax and blocks discord.py
"""

import os
import ast
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Tuple

def check_discord_imports(file_path: str) -> Dict[str, List[str]]:
    """Check for discord.py vs py-cord imports in a file"""
    issues = {
        'discord_py_imports': [],
        'correct_imports': [],
        'command_decorators': [],
        'bot_class_usage': []
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse AST to check imports
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == 'discord':
                        issues['correct_imports'].append(f"import discord")
                    elif alias.name.startswith('discord.'):
                        if 'ext.commands' in alias.name:
                            issues['correct_imports'].append(f"from discord.ext import commands")
                        else:
                            issues['discord_py_imports'].append(f"import {alias.name}")
            
            elif isinstance(node, ast.ImportFrom):
                if node.module == 'discord':
                    issues['correct_imports'].append(f"from discord import ...")
                elif node.module and node.module.startswith('discord.'):
                    if 'ext.commands' in node.module:
                        issues['correct_imports'].append(f"from {node.module} import ...")
                    else:
                        issues['discord_py_imports'].append(f"from {node.module} import ...")
        
        # Check for command decorator patterns
        if '@commands.slash_command' in content:
            issues['command_decorators'].append('Found @commands.slash_command (discord.py style)')
        if '@discord.slash_command' in content:
            issues['command_decorators'].append('Found @discord.slash_command (py-cord style)')
        
        # Check bot class usage
        if 'commands.Bot' in content:
            issues['bot_class_usage'].append('Found commands.Bot (discord.py style)')
        if 'discord.Bot' in content:
            issues['bot_class_usage'].append('Found discord.Bot (py-cord style)')
            
    except Exception as e:
        print(f"Error analyzing {file_path}: {e}")
    
    return issues

def scan_codebase() -> Dict[str, Dict]:
    """Scan entire codebase for py-cord compatibility"""
    results = {}
    
    # Scan all Python files
    for root, dirs, files in os.walk('.'):
        # Skip hidden directories and __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                results[file_path] = check_discord_imports(file_path)
    
    return results

def check_dependencies() -> Dict[str, bool]:
    """Check if discord.py is blocked and py-cord is installed"""
    checks = {
        'py_cord_installed': False,
        'discord_py_blocked': True,
        'correct_version': False
    }
    
    try:
        # Check installed packages
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                              capture_output=True, text=True)
        
        packages = result.stdout.lower()
        
        if 'py-cord' in packages:
            checks['py_cord_installed'] = True
            # Check version
            if '2.6.1' in packages:
                checks['correct_version'] = True
        
        if 'discord.py' in packages:
            checks['discord_py_blocked'] = False
            
    except Exception as e:
        print(f"Error checking dependencies: {e}")
    
    return checks

def verify_command_syntax() -> List[str]:
    """Verify all command decorators use py-cord 2.6.1 syntax"""
    issues = []
    
    cog_files = list(Path('bot/cogs').glob('*.py'))
    
    for cog_file in cog_files:
        try:
            with open(cog_file, 'r') as f:
                content = f.read()
            
            # Check for discord.py style decorators
            if '@commands.slash_command' in content:
                issues.append(f"{cog_file}: Uses @commands.slash_command (should be @discord.slash_command)")
            
            if '@commands.user_command' in content:
                issues.append(f"{cog_file}: Uses @commands.user_command (should be @discord.user_command)")
            
            if '@commands.message_command' in content:
                issues.append(f"{cog_file}: Uses @commands.message_command (should be @discord.message_command)")
                
        except Exception as e:
            issues.append(f"Error reading {cog_file}: {e}")
    
    return issues

def main():
    """Run comprehensive verification"""
    print("🔍 Comprehensive py-cord 2.6.1 Migration Verification")
    print("=" * 60)
    
    # Check dependencies
    print("\n📦 Dependency Check:")
    deps = check_dependencies()
    for check, status in deps.items():
        print(f"   {'✅' if status else '❌'} {check}")
    
    # Scan codebase
    print("\n🔍 Codebase Analysis:")
    results = scan_codebase()
    
    total_files = len(results)
    files_with_issues = 0
    all_issues = []
    
    for file_path, issues in results.items():
        file_issues = []
        
        # Check for discord.py imports
        if issues['discord_py_imports']:
            file_issues.extend([f"Discord.py import: {imp}" for imp in issues['discord_py_imports']])
        
        # Check command decorators
        discord_py_decorators = [dec for dec in issues['command_decorators'] if 'discord.py style' in dec]
        if discord_py_decorators:
            file_issues.extend(discord_py_decorators)
        
        # Check bot class usage
        discord_py_bot = [bot for bot in issues['bot_class_usage'] if 'discord.py style' in bot]
        if discord_py_bot:
            file_issues.extend(discord_py_bot)
        
        if file_issues:
            files_with_issues += 1
            all_issues.append((file_path, file_issues))
    
    print(f"   📊 Analyzed {total_files} Python files")
    print(f"   {'✅' if files_with_issues == 0 else '❌'} {files_with_issues} files with issues")
    
    # Show issues
    if all_issues:
        print("\n❌ Issues Found:")
        for file_path, file_issues in all_issues:
            print(f"\n   📄 {file_path}:")
            for issue in file_issues:
                print(f"      - {issue}")
    
    # Command syntax verification
    print("\n⚙️ Command Syntax Check:")
    command_issues = verify_command_syntax()
    if command_issues:
        print("   ❌ Command syntax issues found:")
        for issue in command_issues:
            print(f"      - {issue}")
    else:
        print("   ✅ All command decorators use py-cord syntax")
    
    # Overall status
    print("\n" + "=" * 60)
    if (deps['py_cord_installed'] and deps['discord_py_blocked'] and 
        deps['correct_version'] and not all_issues and not command_issues):
        print("✅ MIGRATION COMPLETE: Codebase fully compatible with py-cord 2.6.1")
    else:
        print("❌ MIGRATION INCOMPLETE: Issues need to be resolved")
        
        if not deps['py_cord_installed']:
            print("   → Install py-cord 2.6.1")
        if not deps['discord_py_blocked']:
            print("   → Remove discord.py")
        if not deps['correct_version']:
            print("   → Ensure py-cord version 2.6.1")
        if all_issues:
            print("   → Fix import and syntax issues")
        if command_issues:
            print("   → Fix command decorator syntax")

if __name__ == "__main__":
    main()
