#!/usr/bin/env python3
"""
Run Helpers

Task-specific helper functions for run.py
"""

import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Import shared helpers
from .shared_helpers import load_environment_variables, setup_class_imports, handle_keyboard_interrupt, handle_fatal_error

# Import class modules
import importlib
TaskExecutionSystem = importlib.import_module('.class.task_execution_system', package='claude_tools').TaskExecutionSystem


def validate_arguments(args) -> bool:
    """
    Validate command line arguments for task execution

    Args:
        args: Parsed command line arguments

    Returns:
        True if valid, False otherwise
    """
    if args.workers <= 0:
        print("[ERROR] Number of workers must be greater than 0")
        return False

    if args.workers > 20:
        print("[WARNING] High number of workers may cause performance issues")

    return True


def setup_directories() -> bool:
    """
    Setup required directories for task execution

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create brain directories
        brain_dir = Path(".ai/brain")
        tasks_dir = brain_dir / "tasks"
        validation_dir = brain_dir / "validation"
        status_dir = brain_dir / "status"

        for dir_path in [brain_dir, tasks_dir, validation_dir, status_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        return True
    except Exception as e:
        print(f"[ERROR] Failed to setup directories: {e}")
        return False


def initialize_task_system(max_workers: int) -> Optional[TaskExecutionSystem]:
    """
    Initialize the task execution system

    Args:
        max_workers: Number of maximum workers

    Returns:
        TaskExecutionSystem instance or None if failed
    """
    try:
        task_system = TaskExecutionSystem(max_tasks=max_workers)
        return task_system
    except Exception as e:
        print(f"[ERROR] Failed to initialize task execution system: {e}")
        return None


def print_startup_info(max_workers: int):
    """
    Print startup information

    Args:
        max_workers: Number of workers being used
    """
    print("=" * 60)
    print("TASK EXECUTION SYSTEM")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Maximum workers: {max_workers}")
    print(f"Working directory: {Path.cwd()}")
    print("=" * 60)


def print_completion_info(task_system: TaskExecutionSystem, success: bool):
    """
    Print completion information

    Args:
        task_system: TaskExecutionSystem instance
        success: Whether execution was successful
    """
    print("=" * 60)
    print("EXECUTION COMPLETED")
    print("=" * 60)
    print(f"Ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if task_system.statistics_tracker:
        task_system.statistics_tracker.print_summary()

    print(f"Result: {'SUCCESS' if success else 'FAILED'}")
    print("=" * 60)


def handle_system_interrupt(task_system: TaskExecutionSystem):
    """
    Handle system interruption (Ctrl+C)

    Args:
        task_system: TaskExecutionSystem instance
    """
    stats_dict = {}
    if task_system.statistics_tracker:
        stats_dict = task_system.statistics_tracker.get_summary_dict()

    handle_keyboard_interrupt(stats_dict, "Task execution")


def handle_system_error(error: Exception, task_system: TaskExecutionSystem):
    """
    Handle system error

    Args:
        error: Exception that occurred
        task_system: TaskExecutionSystem instance
    """
    stats_dict = {}
    if task_system.statistics_tracker:
        stats_dict = task_system.statistics_tracker.get_summary_dict()

    handle_fatal_error(error, stats_dict, "Task execution")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Task Execution System - Execute tasks with parallel processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m claude_tools.run                    # Run with default 5 workers
  python -m claude_tools.run --workers 3        # Run with 3 workers
  python -m claude_tools.run --workers 10       # Run with 10 workers
        """
    )

    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=5,
        help="Number of parallel workers (default: 5, max: 20)"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Task Execution System 1.0.0"
    )

    return parser.parse_args()


def check_prerequisites() -> bool:
    """
    Check if all prerequisites are met for task execution

    Returns:
        True if prerequisites are met, False otherwise
    """
    # Check if .ai directory exists
    ai_dir = Path(".ai")
    if not ai_dir.exists():
        print("[WARNING] .ai directory not found, will create it")
        try:
            ai_dir.mkdir(exist_ok=True)
        except Exception as e:
            print(f"[ERROR] Cannot create .ai directory: {e}")
            return False

    # Check if .ai/plan directory exists
    plan_dir = Path(".ai/plan")
    if not plan_dir.exists():
        print("[WARNING] .ai/plan directory not found, no tasks to execute")
        # This is not necessarily an error, just warning

    # Check if prompt templates exist
    prompt_template_dir = Path(__file__).parent / "prompt_template"
    if not prompt_template_dir.exists():
        print(f"[ERROR] Prompt template directory not found: {prompt_template_dir}")
        return False

    # Check for required agent templates
    required_templates = [
        "task-analyzer-executor.md",
        "task-validator.md",
        "task-status-updater.md"
    ]

    missing_templates = []
    for template in required_templates:
        template_file = prompt_template_dir / template
        if not template_file.exists():
            missing_templates.append(template)

    if missing_templates:
        print(f"[ERROR] Missing required agent templates:")
        for template in missing_templates:
            print(f"  - {template}")
        return False

    return True


def run_task_execution_workflow(max_workers: int) -> bool:
    """
    Run the complete task execution workflow

    Args:
        max_workers: Number of workers to use

    Returns:
        True if successful, False otherwise
    """
    # Print startup info
    print_startup_info(max_workers)

    # Check prerequisites
    if not check_prerequisites():
        return False

    # Setup directories
    if not setup_directories():
        return False

    # Initialize task system
    task_system = initialize_task_system(max_workers)
    if not task_system:
        return False

    try:
        # Run the task execution
        success = task_system.run_task_execution(max_workers)

        # Print completion info
        print_completion_info(task_system, success)

        return success

    except KeyboardInterrupt:
        handle_system_interrupt(task_system)
        return False
    except Exception as e:
        handle_system_error(e, task_system)
        return False


def main():
    """Main entry point for task execution"""
    # Load environment variables
    load_environment_variables()

    # Setup class imports
    classes = setup_class_imports()
    if not classes:
        sys.exit(1)

    # Parse arguments
    args = parse_arguments()

    # Validate arguments
    if not validate_arguments(args):
        sys.exit(1)

    # Run task execution workflow
    try:
        success = run_task_execution_workflow(args.workers)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[OK] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n[ERROR] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()