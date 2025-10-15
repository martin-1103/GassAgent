#!/usr/bin/env python3
"""
Phase Manager CLI

Command-line interface for the PhaseManager class.
Provides all CLI functionality that was previously in phase_manager.py.
"""

import sys
import os

# Add the class directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'class'))

from class.phase_manager import PhaseManager


def show_help():
    """Show help message"""
    print("""
Usage: python phase_manager_cli.py [command] [options]

Commands:
  leaf-tasks               Show available leaf tasks to work on
  find-phases              Find leaf phases with duration >60 minutes
  update-status            Update phase status
  list                     List all phases with status

Options:
  --phase <id>             Filter by specific phase ID
  --status <status>        New status (pending, in-progress, completed)
  --all                    Update all phases
  --limit <number>         Limit output (default: 5/20)
  --help, -h               Show this help

Examples:
  python phase_manager_cli.py leaf-tasks
  python phase_manager_cli.py leaf-tasks --phase 1
  python phase_manager_cli.py find-phases --limit 10
  python phase_manager_cli.py update-status --phase 1 --status completed
  python phase_manager_cli.py update-status --all --status pending
  python phase_manager_cli.py list
""")


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2 or '--help' in sys.argv or '-h' in sys.argv:
        show_help()
        return

    command = sys.argv[1]
    manager = PhaseManager()

    if command == 'leaf-tasks':
        if '--phase' in sys.argv:
            phase_idx = sys.argv.index('--phase')
            if phase_idx + 1 < len(sys.argv):
                phase_id = sys.argv[phase_idx + 1]
                tasks = manager.get_leaf_tasks_for_phase(phase_id)
                print(f"SEARCH: Leaf tasks for Phase {phase_id}:")
            else:
                print("Please provide phase ID: --phase <id>")
                return
        else:
            tasks = manager.get_all_leaf_tasks()
            print("SEARCH: All available leaf tasks:")

        limit = 5
        if '--limit' in sys.argv:
            limit_idx = sys.argv.index('--limit')
            if limit_idx + 1 < len(sys.argv):
                limit = int(sys.argv[limit_idx + 1])

        print(manager.format_tasks(tasks, limit))

    elif command == 'find-phases':
        limit = 20
        if '--limit' in sys.argv:
            limit_idx = sys.argv.index('--limit')
            if limit_idx + 1 < len(sys.argv):
                limit = int(sys.argv[limit_idx + 1])

        print("SEARCH: Finding leaf phases with duration >60 minutes...")
        phases = manager.find_leaf_phases(limit)
        print(manager.format_leaf_phases(phases))

    elif command == 'update-status':
        if '--status' not in sys.argv:
            print("Error: --status option required")
            return

        status_idx = sys.argv.index('--status')
        new_status = sys.argv[status_idx + 1]

        if '--all' in sys.argv:
            count = manager.update_all_status(new_status)
            print(f"SUCCESS: Updated {count} phases to {new_status}")
        elif '--phase' in sys.argv:
            phase_idx = sys.argv.index('--phase')
            if phase_idx + 1 < len(sys.argv):
                phase_id = sys.argv[phase_idx + 1]
                manager.update_status(phase_id, new_status)
            else:
                print("Please provide phase ID: --phase <id>")
        else:
            print("Please specify --all or --phase <id>")

    elif command == 'list':
        manager.list_phases()

    else:
        print(f"Unknown command: {command}")
        show_help()


if __name__ == "__main__":
    main()