#!/usr/bin/env python3
"""
Init Helpers

Initialization-specific helper functions for init.py
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Import shared helpers
from .shared_helpers import load_environment_variables, setup_class_imports, handle_keyboard_interrupt, handle_fatal_error, validate_file_path

# Import class modules
import importlib
InitializationSystem = importlib.import_module('.class.initialization_system', package='claude_tools').InitializationSystem


def validate_arguments(args) -> bool:
    """
    Validate command line arguments for initialization system

    Args:
        args: Parsed command line arguments

    Returns:
        True if valid, False otherwise
    """
    # Validate plan file
    plan_file = validate_file_path(args.plan_path, handle_at_symbol=True)
    if not plan_file:
        return False

    # Validate target folder if provided
    if args.target_folder:
        target_path = Path(args.target_folder)
        if target_path.exists() and not target_path.is_dir():
            print(f"[ERROR] Target path exists but is not a directory: {target_path}")
            return False

        # Check for invalid characters in folder name
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        if any(char in args.target_folder for char in invalid_chars):
            print(f"[ERROR] Target folder contains invalid characters: {args.target_folder}")
            return False

    return True


def setup_directories() -> bool:
    """
    Setup required directories for initialization system

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create AI directories
        base_dir = Path(".ai")
        plan_dir = base_dir / "plan"
        schema_dir = base_dir / "schema"
        structure_dir = base_dir / "structure"

        for dir_path in [base_dir, plan_dir, schema_dir, structure_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

        # Create prompt temp directory
        package_dir = Path(__file__).parent
        prompt_tmp_dir = package_dir / "prompt_tmp"
        prompt_tmp_dir.mkdir(exist_ok=True)

        return True
    except Exception as e:
        print(f"[ERROR] Failed to setup directories: {e}")
        return False


def initialize_init_system() -> Optional[InitializationSystem]:
    """
    Initialize the initialization system

    Returns:
        InitializationSystem instance or None if failed
    """
    try:
        init_system = InitializationSystem()
        return init_system
    except Exception as e:
        print(f"[ERROR] Failed to initialize initialization system: {e}")
        return None


def print_startup_info(plan_file: Path, target_folder: Optional[str]):
    """
    Print startup information

    Args:
        plan_file: Path to plan file
        target_folder: Optional target folder name
    """
    print("=" * 60)
    print("PROJECT INITIALIZATION SYSTEM")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Plan file: {plan_file}")
    print(f"Target folder: {target_folder or 'New project'}")
    print(f"Working directory: {Path.cwd()}")
    print("=" * 60)


def print_completion_info(init_system: InitializationSystem, success: bool, output_dir: Path):
    """
    Print completion information

    Args:
        init_system: InitializationSystem instance
        success: Whether initialization was successful
        output_dir: Directory where files were generated
    """
    print("=" * 60)
    print("INITIALIZATION COMPLETED")
    print("=" * 60)
    print(f"Ended at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if init_system.statistics_tracker:
        init_system.statistics_tracker.print_summary()

    print(f"Generated files in: {output_dir}")
    print(f"Result: {'SUCCESS' if success else 'COMPLETED_WITH_ISSUES'}")
    print("=" * 60)


def handle_system_interrupt(init_system: InitializationSystem):
    """
    Handle system interruption (Ctrl+C)

    Args:
        init_system: InitializationSystem instance
    """
    stats_dict = {}
    if init_system.statistics_tracker:
        stats_dict = init_system.statistics_tracker.get_summary_dict()

    handle_keyboard_interrupt(stats_dict, "Initialization")


def handle_system_error(error: Exception, init_system: InitializationSystem):
    """
    Handle system error

    Args:
        error: Exception that occurred
        init_system: InitializationSystem instance
    """
    stats_dict = {}
    if init_system.statistics_tracker:
        stats_dict = init_system.statistics_tracker.get_summary_dict()

    handle_fatal_error(error, stats_dict, "Initialization")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Project Initialization System - Initialize projects from PRD files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m claude_tools.init @sample_prd.md                    # Initialize new project
  python -m claude_tools.init @sample_prd.md my_project        # Initialize with target folder
  python -m claude_tools.init prd.md                           # Initialize without @ notation
  python -m claude_tools.init ./requirements/prd.md existing     # Initialize existing project
        """
    )

    parser.add_argument(
        "plan_path",
        help="Path to PRD/plan file (supports @ notation for relative paths)"
    )

    parser.add_argument(
        "target_folder",
        nargs='?',
        help="Target folder name (optional - creates new project if not specified)"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="Initialization System 1.0.0"
    )

    return parser.parse_args()


def check_prerequisites() -> bool:
    """
    Check if all prerequisites are met for initialization system

    Returns:
        True if prerequisites are met, False otherwise
    """
    # Check for required agent templates
    prompt_template_dir = Path(__file__).parent / "prompt_template"
    if not prompt_template_dir.exists():
        print(f"[ERROR] Prompt template directory not found: {prompt_template_dir}")
        return False

    # Check for required agent templates
    required_templates = [
        "plan-analyzer.md",
        "database-schema-designer.md",
        "project-structure-generator.md"
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


def print_project_summary(plan_file: Path, target_folder: Optional[str]):
    """
    Print project summary before initialization

    Args:
        plan_file: Path to plan file
        target_folder: Optional target folder name
    """
    print(f"Project initialization summary:")
    print(f"  Source plan: {plan_file}")
    print(f"  Target folder: {target_folder or 'Auto-generated'}")
    print(f"  Output location: .ai/")
    print(f"  Phases: Plan analysis → Parallel generation")
    print(f"  Output files:")
    print(f"    - .ai/plan/ (Development phases)")
    print(f"    - .ai/schema/ (Database schema)")
    print(f"    - .ai/structure/ (Project structure)")
    print()


def run_initialization_workflow(plan_path: str, target_folder: Optional[str]) -> bool:
    """
    Run the complete initialization workflow

    Args:
        plan_path: Path to plan file
        target_folder: Optional target folder name

    Returns:
        True if successful, False otherwise
    """
    # Convert plan path to Path object
    plan_file = Path(plan_path)

    # Print startup info
    print_startup_info(plan_file, target_folder)
    print_project_summary(plan_file, target_folder)

    # Check prerequisites
    if not check_prerequisites():
        return False

    # Setup directories
    if not setup_directories():
        return False

    # Initialize initialization system
    init_system = initialize_init_system()
    if not init_system:
        return False

    try:
        # Run the initialization
        success = init_system.run_initialization(plan_path, target_folder)

        # Print completion info
        print_completion_info(init_system, success, Path(".ai"))

        return success

    except KeyboardInterrupt:
        handle_system_interrupt(init_system)
        return False
    except Exception as e:
        handle_system_error(e, init_system)
        return False


def main():
    """Main entry point for initialization system"""
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

    # Run initialization workflow
    try:
        success = run_initialization_workflow(args.plan_path, args.target_folder)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[OK] Interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n[ERROR] Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()