#!/usr/bin/env python3
"""
Main Claude CLI Tools

Multi-function CLI with subcommands for streaming and breakdown automation.
"""

import argparse
import sys
import os
from datetime import datetime

# Add class directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
class_dir = os.path.join(current_dir, 'class')
if class_dir not in sys.path:
    sys.path.insert(0, class_dir)

from claude_streamer import ClaudeStreamer


def default_finish_hook():
    """Default callback called when stream finishes"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Task completed")


def stream_main(args):
    """Handle stream subcommand"""
    # Create streamer with default settings and finish hook
    streamer = ClaudeStreamer(on_finish_callback=default_finish_hook)

    # Stream response
    exit_code = streamer.stream(args.prompt)
    return exit_code


def break_main(args):
    """Handle break subcommand"""
    # Import here to avoid circular imports
    import importlib.util
    import os

    # Load break.py module dynamically to avoid keyword conflict
    spec = importlib.util.spec_from_file_location("break_module", os.path.join(os.path.dirname(__file__), "break.py"))
    break_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(break_module)

    # Set sys.argv to pass arguments to break.py
    original_argv = sys.argv[:]
    sys.argv = ['break']
    if args.workers:
        sys.argv.extend(['--workers', str(args.workers)])
    if args.max_iterations:
        sys.argv.extend(['--max-iterations', str(args.max_iterations)])

    try:
        # Call the main function from break.py
        break_module.main()
        return 0
    except SystemExit as e:
        return e.code
    finally:
        # Restore original argv
        sys.argv = original_argv


def init_main(args):
    """Handle init subcommand"""
    # Import here to avoid circular imports
    import importlib.util
    import os

    # Load init.py module dynamically to avoid keyword conflict
    spec = importlib.util.spec_from_file_location("init_module", os.path.join(os.path.dirname(__file__), "init.py"))
    init_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(init_module)

    # Set sys.argv to pass arguments to init.py
    original_argv = sys.argv[:]
    sys.argv = ['init']
    if args.plan_path:
        sys.argv.append(args.plan_path)
    if args.target_folder:
        sys.argv.append(args.target_folder)

    try:
        # Initialize and run the system
        init_system = init_module.InitializationSystem()
        success = init_system.run_initialization(args.plan_path, args.target_folder)
        return 0 if success else 1
    except SystemExit as e:
        return e.code
    finally:
        # Restore original argv
        sys.argv = original_argv


def run_main(args):
    """Handle run subcommand"""
    # Import here to avoid circular imports
    import importlib.util
    import os

    # Load run.py module dynamically to avoid keyword conflict
    spec = importlib.util.spec_from_file_location("run_module", os.path.join(os.path.dirname(__file__), "run.py"))
    run_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(run_module)

    # Set sys.argv to pass arguments to run.py
    original_argv = sys.argv[:]
    sys.argv = ['run']
    if args.workers:
        sys.argv.extend(['--workers', str(args.workers)])

    try:
        # Initialize and run the system with dynamic workers
        workers = args.workers if args.workers is not None else 5
        task_system = run_module.TaskExecutionSystem(max_tasks=workers)
        success = task_system.run_task_execution(workers)
        return 0 if success else 1
    except SystemExit as e:
        return e.code
    finally:
        # Restore original argv
        sys.argv = original_argv


def gass_cli():
    """Main CLI entry point for gass command"""
    parser = argparse.ArgumentParser(
        description="Claude CLI Tools - Multi-function command line interface",
        epilog="Use 'gass <command> --help' for more information on a specific command."
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Stream subcommand
    stream_parser = subparsers.add_parser(
        'stream',
        help='Stream Claude Code responses in headless mode',
        description="Stream Claude Code responses in headless mode",
        epilog="Example: gass stream \"Explain this code\""
    )
    stream_parser.add_argument(
        'prompt',
        help='The prompt to send to Claude'
    )

    # Break subcommand
    break_parser = subparsers.add_parser(
        'break',
        help='Run breakdown loop for phase automation',
        description="Breakdown Loop - Automated Phase Breakdown System",
        epilog="Example: gass break --workers 2 --max-iterations 50"
    )
    break_parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='Number of parallel workers for processing phases (default: 1)'
    )
    break_parser.add_argument(
        '--max-iterations',
        type=int,
        default=50,
        help='Maximum iterations to prevent infinite loops (default: 50)'
    )

    # Init subcommand
    init_parser = subparsers.add_parser(
        'init',
        help='Initialize project with comprehensive planning',
        description="Project Initialization System - Comprehensive planning, database schema and structure generation",
        epilog="Example: gass init @sample_prd.rbac myproject"
    )
    init_parser.add_argument(
        'plan_path',
        help='Path to PRD/plan file (supports @ notation for file references)'
    )
    init_parser.add_argument(
        'target_folder',
        nargs='?',
        help='Target folder name for project (optional)'
    )

    # Run subcommand
    run_parser = subparsers.add_parser(
        'run',
        help='Execute tasks with parallel processing and validation',
        description="Task Execution System - Execute tasks with comprehensive planning, validation, and status management",
        epilog="Example: gass run --workers 3"
    )
    run_parser.add_argument(
        '--workers',
        type=int,
        default=5,
        help='Number of parallel workers for task execution (default: 5)'
    )

    # Parse arguments
    args = parser.parse_args()

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return 1

    # Route to appropriate handler
    try:
        if args.command == 'stream':
            return stream_main(args)
        elif args.command == 'break':
            return break_main(args)
        elif args.command == 'init':
            return init_main(args)
        elif args.command == 'run':
            return run_main(args)
        else:
            print(f"Unknown command: {args.command}")
            return 1
    except KeyboardInterrupt:
        print(f"\n[OK] Interrupted by user")
        return 130
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return 1


def main():
    """Original main function for backward compatibility"""
    parser = argparse.ArgumentParser(
        description="Stream Claude Code responses in headless mode",
        epilog="Example: %(prog)s \"Explain this code\""
    )

    parser.add_argument(
        "prompt",
        help="The prompt to send to Claude"
    )

    args = parser.parse_args()

    # Create streamer with default settings and finish hook
    streamer = ClaudeStreamer(on_finish_callback=default_finish_hook)

    # Stream response
    exit_code = streamer.stream(args.prompt)
    sys.exit(exit_code)


if __name__ == "__main__":
    # If called directly, use original main function
    main()