#!/usr/bin/env python3
"""
Break Helpers

Breakdown-specific helper functions for break.py
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Import shared helpers
from .shared_helpers import load_environment_variables, setup_class_imports, handle_keyboard_interrupt, handle_fatal_error

# Import class modules
import importlib
BreakdownSystem = importlib.import_module('.class.breakdown_system', package='claude_tools').BreakdownSystem


def validate_arguments(args) -> bool:
    """
    Validate command line arguments for breakdown system

    Args:
        args: Parsed command line arguments

    Returns:
        True if valid, False otherwise
    """
    if args.workers <= 0:
        print("[ERROR] Number of workers must be greater than 0")
        return False

    if args.workers > 10:
        print("[WARNING] High number of workers may cause performance issues for breakdown operations")

    if args.max_iterations <= 0:
        print("[ERROR] Max iterations must be greater than 0")
        return False

    if args.max_iterations > 100:
        print("[WARNING] High number of iterations may indicate infinite loop issues")

    return True


def setup_directories() -> bool:
    """
    Setup required directories for breakdown system

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create plan directories
        plan_dir = Path(".ai/plan")
        if not plan_dir.exists():
            plan_dir.mkdir(parents=True, exist_ok=True)

        # Create prompt temp directory
        package_dir = Path(__file__).parent
        prompt_tmp_dir = package_dir / "prompt_tmp"
        prompt_tmp_dir.mkdir(exist_ok=True)

        return True
    except Exception as e:
        print(f"[ERROR] Failed to setup directories: {e}")
        return False


def initialize_breakdown_system(max_workers: int) -> Optional[BreakdownSystem]:
    """
    Initialize the breakdown system

    Args:
        max_workers: Number of maximum workers

    Returns:
        BreakdownSystem instance or None if failed
    """
    try:
        breakdown_system = BreakdownSystem(max_workers=max_workers)
        return breakdown_system
    except Exception as e:
        print(f"[ERROR] Failed to initialize breakdown system: {e}")
        return None


def print_startup_info(max_workers: int, max_iterations: int):
    """
    Print startup information

    Args:
        max_workers: Number of workers being used
        max_iterations: Maximum number of iterations
    """
    print("=" * 60)
    print("BREAKDOWN SYSTEM")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Maximum workers: {max_workers}")
    print(f"Maximum iterations: {max_iterations}")
    print(f"Working directory: {Path.cwd()}")
    print("=" * 60)


def print_completion_info(breakdown_system: BreakdownSystem, success: bool):
    """
    Print completion information

    Args:
        breakdown_system: BreakdownSystem instance
        success: Whether execution was successful
    """
    print("=" * 60)
    print("BREAKDOWN COMPLETED")
    print("=" * 60)
    print(f"Ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if breakdown_system.statistics_tracker:
        breakdown_system.statistics_tracker.print_summary()

    print(f"Result: {'SUCCESS' if success else 'COMPLETED_WITH_ISSUES'}")
    print("=" * 60)


def handle_system_interrupt(breakdown_system: BreakdownSystem):
    """
    Handle system interruption (Ctrl+C)

    Args:
        breakdown_system: BreakdownSystem instance
    """
    stats_dict = {}
    if breakdown_system.statistics_tracker:
        stats_dict = breakdown_system.statistics_tracker.get_summary_dict()

    handle_keyboard_interrupt(stats_dict, "Breakdown")


def handle_system_error(error: Exception, breakdown_system: BreakdownSystem):
    """
    Handle system error

    Args:
        error: Exception that occurred
        breakdown_system: BreakdownSystem instance
    """
    stats_dict = {}
    if breakdown_system.statistics_tracker:
        stats_dict = breakdown_system.statistics_tracker.get_summary_dict()

    handle_fatal_error(error, stats_dict, "Breakdown")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Breakdown System - Automated phase breakdown with strategic context",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m claude_tools.break                              # Run with default settings
  python -m claude_tools.break --workers 3                 # Run with 3 workers
  python -m claude_tools.break --max-iterations 10         # Run with 10 iterations max
  python -m claude_tools.break --workers 2 --max-iterations 5  # Custom workers and iterations
        """
    )

    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=1,
        help="Number of parallel workers for processing phases (default: 1, max: 10)"
    )

    parser.add_argument(
        "--max-iterations", "-i",
        type=int,
        default=50,
        help="Maximum iterations to prevent infinite loops (default: 50, max: 100)"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Breakdown System 1.0.0"
    )

    return parser.parse_args()


def check_prerequisites() -> bool:
    """
    Check if all prerequisites are met for breakdown system

    Returns:
        True if prerequisites are met, False otherwise
    """
    # Check if .ai directory exists
    ai_dir = Path(".ai")
    if not ai_dir.exists():
        print("[ERROR] .ai directory not found")
        print("Please run initialization first: python -m claude_tools.init <plan_file>")
        return False

    # Check if .ai/plan directory exists
    plan_dir = Path(".ai/plan")
    if not plan_dir.exists():
        print("[ERROR] .ai/plan directory not found")
        print("Please run initialization first: python -m claude_tools.init <plan_file>")
        return False

    # Check if there are any plan files
    plan_files = list(plan_dir.glob("*.json"))
    if not plan_files:
        print("[WARNING] No plan files found in .ai/plan/")
        print("The breakdown system will exit immediately.")

    # Check if prompt templates exist
    prompt_template_dir = Path(__file__).parent / "prompt_template"
    if not prompt_template_dir.exists():
        print(f"[ERROR] Prompt template directory not found: {prompt_template_dir}")
        return False

    # Check for required agent templates
    required_templates = [
        "plan-breakdown-analyzer.md"
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


def print_phase_summary(phases_needing_breakdown):
    """
    Print summary of phases needing breakdown

    Args:
        phases_needing_breakdown: List of phases needing breakdown
    """
    if not phases_needing_breakdown:
        print("[OK] No phases need breakdown - all within 60min limit")
        return

    print(f"Found {len(phases_needing_breakdown)} phases needing breakdown:")

    # Group by file for display
    grouped_by_file = {}
    for phase in phases_needing_breakdown:
        file_name = phase['file']
        if file_name not in grouped_by_file:
            grouped_by_file[file_name] = []
        grouped_by_file[file_name].append(phase)

    # Display found phases
    for file_name, phases in grouped_by_file.items():
        print(f"\nFile: {file_name}")
        for phase in phases:
            print(f"   - Phase {phase['phase_id']}: {phase['title']} ({phase['duration']}min)")


def run_breakdown_workflow(max_workers: int, max_iterations: int) -> bool:
    """
    Run the complete breakdown workflow

    Args:
        max_workers: Number of workers to use
        max_iterations: Maximum number of iterations

    Returns:
        True if successful, False otherwise
    """
    # Print startup info
    print_startup_info(max_workers, max_iterations)

    # Check prerequisites
    if not check_prerequisites():
        return False

    # Setup directories
    if not setup_directories():
        return False

    # Initialize breakdown system
    breakdown_system = initialize_breakdown_system(max_workers)
    if not breakdown_system:
        return False

    try:
        # Run the breakdown loop
        success = breakdown_system.run_loop(max_iterations)

        # Print completion info
        print_completion_info(breakdown_system, success)

        return success

    except KeyboardInterrupt:
        handle_system_interrupt(breakdown_system)
        return False
    except Exception as e:
        handle_system_error(e, breakdown_system)
        return False


def main():
    """Main entry point for breakdown system"""
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

    # Run breakdown workflow
    try:
        success = run_breakdown_workflow(args.workers, args.max_iterations)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[OK] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n[ERROR] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()