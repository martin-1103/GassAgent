"""
Claude CLI Tools

Multi-function command line interface for Claude Code automation.
"""

import os
from pathlib import Path

# Load environment variables from .env file
env_file = Path(__file__).parent / ".env"
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

__version__ = "0.1.0"
__author__ = "User"