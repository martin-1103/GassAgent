#!/usr/bin/env python3
"""
Breakdown System - Main Entry Point

Clean entry point for breakdown system using refactored components.
"""

import sys
import argparse
from pathlib import Path

# Import helper functions
from .break_helpers import (
    load_environment_variables,
    setup_class_imports,
    parse_arguments,
    validate_arguments,
    run_breakdown_workflow
)


def main():
    """Main CLI interface for breakdown system."""

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