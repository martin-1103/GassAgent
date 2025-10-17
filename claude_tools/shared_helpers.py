#!/usr/bin/env python3
"""
Shared Helper Functions

Common utility functions used across run.py, break.py, and init.py
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def load_environment_variables():
    """
    Load environment variables from .env file

    This function handles loading environment variables from .env file
    with fallback to manual parsing if python-dotenv is not available.
    """
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


def setup_class_imports():
    """
    Setup sys.path to include class directory and import classes

    Returns:
        Dictionary with imported classes or None if failed
    """
    try:
        import importlib

        # Import modules using importlib to avoid syntax issues
        claude_streamer = importlib.import_module('.claude_streamer', package='claude_tools')
        worker_monitor = importlib.import_module('.worker_monitor', package='claude_tools')
        phase_manager = importlib.import_module('.class.phase_manager', package='claude_tools')

        return {
            'ClaudeStreamer': claude_streamer.ClaudeStreamer,
            'WorkerMonitor': worker_monitor.WorkerMonitor,
            'WorkerState': worker_monitor.WorkerState,
            'PhaseManager': phase_manager.PhaseManager
        }
    except ImportError as e:
        print(f"Error importing classes: {e}")
        print("Make sure required modules are available")
        return None


def get_package_directory():
    """
    Get the package directory for absolute paths

    Returns:
        Path object for package directory
    """
    return Path(__file__).parent


def create_directories(directories):
    """
    Create multiple directories with parents if they don't exist

    Args:
        directories: List of Path objects or strings for directories to create
    """
    for dir_path in directories:
        if isinstance(dir_path, str):
            dir_path = Path(dir_path)
        if hasattr(dir_path, 'mkdir'):
            dir_path.mkdir(parents=True, exist_ok=True)
        else:
            Path(dir_path).mkdir(parents=True, exist_ok=True)


def validate_file_path(file_path: str, handle_at_symbol: bool = True) -> Optional[Path]:
    """
    Validate and return Path object for file

    Args:
        file_path: Path to file (supports @ notation if enabled)
        handle_at_symbol: Whether to handle @ symbol prefix

    Returns:
        Path object if valid, None otherwise
    """
    if handle_at_symbol and file_path.startswith('@'):
        file_path = file_path[1:]

    path_obj = Path(file_path)
    if not path_obj.exists():
        print(f"[ERROR] File not found: {path_obj}")
        return None

    if not path_obj.is_file():
        print(f"[ERROR] Path is not a file: {path_obj}")
        return None

    return path_obj


def format_duration_summary(duration_str: str) -> str:
    """
    Format duration string for display

    Args:
        duration_str: Duration string (e.g., "960", "960-1440")

    Returns:
        Formatted duration string
    """
    if '-' in duration_str:
        # Range format
        return f"{duration_str} minutes (range)"
    else:
        # Single value
        minutes = int(duration_str)
        hours = minutes // 60
        mins = minutes % 60
        if hours > 0:
            return f"{minutes} minutes ({hours}h {mins}m)"
        else:
            return f"{minutes} minutes"


def handle_keyboard_interrupt(stats_dict: Dict[str, int], operation_name: str):
    """
    Handle keyboard interruption gracefully

    Args:
        stats_dict: Dictionary with statistics (success, failed, etc.)
        operation_name: Name of the operation being interrupted
    """
    print(f"\n\n[OK] {operation_name} interrupted by user")
    print(f"Stats: {stats_dict.get('success', 0)} success, {stats_dict.get('failed', 0)} failed")


def handle_fatal_error(error: Exception, stats_dict: Dict[str, int], operation_name: str):
    """
    Handle fatal errors gracefully

    Args:
        error: Exception that occurred
        stats_dict: Dictionary with statistics
        operation_name: Name of the operation that failed
    """
    print(f"\n\n[ERROR] Fatal error in {operation_name}: {error}")
    print(f"Stats: {stats_dict.get('success', 0)} success, {stats_dict.get('failed', 0)} failed")


def create_stream_callback(worker_monitor, worker_id: int):
    """
    Create a stream callback function for worker monitoring

    Args:
        worker_monitor: WorkerMonitor instance
        worker_id: ID of the worker

    Returns:
        Callback function for streaming
    """
    def stream_callback(text: str):
        # Clean up the text and update worker status
        clean_text = text.strip().replace('\n', ' ').replace('\r', '')
        if clean_text and len(clean_text) > 0:
            # Truncate if too long
            if len(clean_text) > 40:
                clean_text = clean_text[:37] + "..."
            worker_monitor.update_worker(worker_id, clean_text, worker_monitor.WorkerState.ACTIVE)

    return stream_callback


def setup_delayed_idle(worker_monitor, worker_id: int, delay_seconds: int = 2):
    """
    Setup delayed idle state for worker after error

    Args:
        worker_monitor: WorkerMonitor instance
        worker_id: ID of the worker
        delay_seconds: Number of seconds to wait before setting to idle
    """
    import threading
    import time

    def delayed_idle():
        time.sleep(delay_seconds)
        worker_monitor.set_worker_idle(worker_id)

    threading.Thread(target=delayed_idle, daemon=True).start()


def cleanup_temp_file(file_path: str):
    """
    Clean up temporary file safely

    Args:
        file_path: Path to file to remove
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        pass  # Silently ignore cleanup errors


def validate_json_content(content: str) -> tuple[bool, str]:
    """
    Validate if content is valid JSON

    Args:
        content: String content to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        import json
        json.loads(content)
        return True, ""
    except json.JSONDecodeError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"