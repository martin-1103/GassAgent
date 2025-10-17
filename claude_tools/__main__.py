#!/usr/bin/env python3
"""
Main entry point for claude_tools module

This allows running the module with: python -m claude_tools
"""

import os
import sys
from pathlib import Path

# Load environment variables from .env file
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    try:
        # Try to load with python-dotenv if available
        from dotenv import load_dotenv
        load_dotenv(env_file)
    except ImportError:
        # Fallback: manually parse .env file
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# Import sub-modules
from . import init

# Import break module dynamically to avoid keyword conflict
import importlib.util
import os as _os

def _import_break_module():
    break_file = _os.path.join(_os.path.dirname(__file__), "break.py")
    spec = importlib.util.spec_from_file_location("break_module", break_file)
    break_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(break_module)
    return break_module

break_module = _import_break_module()

def main():
    """Main entry point for claude_tools module."""
    if len(sys.argv) < 2:
        print("Usage: python -m claude_tools <command> [args...]")
        print("Commands:")
        print("  init <plan_file> [target_folder]  - Initialize project")
        print("  break [options]                   - Run breakdown loop")
        print("  help                              - Show this help")
        return 1

    command = sys.argv[1]

    if command == "init":
        # Remove 'claude_tools' from sys.argv and pass to init.main()
        sys.argv = ["claude_tools"] + sys.argv[2:]
        return init.main()
    elif command == "break":
        # Remove 'claude_tools' from sys.argv and pass to break_module.main()
        sys.argv = ["break.py"] + sys.argv[2:]
        return break_module.main()
    elif command == "help":
        # Show help message directly instead of calling main() again
        print("Usage: python -m claude_tools <command> [args...]")
        print("Commands:")
        print("  init <plan_file> [target_folder]  - Initialize project")
        print("  break [options]                   - Run breakdown loop")
        print("  help                              - Show this help")
        return 0
    else:
        print(f"Unknown command: {command}")
        print("Use 'python -m claude_tools help' for usage information")
        return 1

if __name__ == "__main__":
    sys.exit(main())