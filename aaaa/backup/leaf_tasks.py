#!/usr/bin/env python3
"""
Simple Leaf Task Finder

Find pending leaf tasks from JSON plan files.
"""

import json
import os
from typing import List, Dict, Any


class LeafTaskFinder:
    """Simple class to find leaf tasks from plan files."""

    def __init__(self, plan_dir: str = ".ai/plan"):
        """
        Initialize with plan directory path

        Args:
            plan_dir: Path to directory containing plan JSON files
        """
        self.plan_dir = plan_dir

    def load_json(self, file_path: str) -> Dict[str, Any]:
        """Load JSON file safely"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return {}

    def get_phase_status(self, phase_id: str) -> str:
        """Get status of a phase - supports both individual files and phases.json"""
        # First try individual file
        individual_file = os.path.join(self.plan_dir, f"{phase_id}.json")
        if os.path.exists(individual_file):
            data = self.load_json(individual_file)
            return data.get('status', 'pending')

        # Then try phases.json
        phases_file = os.path.join(self.plan_dir, 'phases.json')
        if os.path.exists(phases_file):
            data = self.load_json(phases_file)
            phases = data.get('phases', [])
            for phase in phases:
                if str(phase['id']) == str(phase_id):
                    return phase.get('status', 'pending')

        return 'unknown'

    def are_dependencies_completed(self, dependencies: List[str]) -> bool:
        """Check if all dependencies are completed"""
        if not dependencies:
            return True

        return all(self.get_phase_status(dep) == 'completed' for dep in dependencies)

    def is_true_leaf_phase(self, sub_phase: Dict[str, Any]) -> bool:
        """Check if sub-phase is a true leaf node"""
        sub_phase_file = os.path.join(self.plan_dir, f"{sub_phase['id']}.json")

        if os.path.exists(sub_phase_file):
            sub_phase_data = self.load_json(sub_phase_file)
            if sub_phase_data.get('phases'):
                return False  # Has sub-phases, not a leaf

        return True  # Is a leaf node

    def get_priority_value(self, priority) -> int:
        """Convert priority string to number for sorting"""
        if isinstance(priority, str):
            priority_map = {'high': 1, 'medium': 2, 'low': 3}
            return priority_map.get(priority.lower(), 999)
        return priority or 999

    def get_all_leaf_tasks(self) -> List[Dict[str, Any]]:
        """Get all leaf tasks that can be worked on - supports both individual files and phases.json"""
        if not os.path.exists(self.plan_dir):
            return []

        # Get all individual files first
        all_files = os.listdir(self.plan_dir)
        phase_files = [f for f in all_files if f.endswith('.json') and f != 'phases.json']
        tasks = []

        # Process individual files (like JS version)
        for file in phase_files:
            phase_id = file.replace('.json', '')
            file_path = os.path.join(self.plan_dir, file)
            data = self.load_json(file_path)

            if not data.get('title'):
                continue

            # If this phase has sub-phases, check each sub-phase
            phases = data.get('phases', [])
            if phases:
                for sub_phase in phases:
                    if not self.is_true_leaf_phase(sub_phase):
                        continue  # Skip non-leaf nodes

                    # Check if task can be worked on
                    deps_completed = self.are_dependencies_completed(sub_phase.get('dependencies', []))
                    is_pending = sub_phase.get('status') == 'pending'

                    if deps_completed and is_pending:
                        task = {
                            'id': sub_phase['id'],
                            'title': sub_phase['title'],
                            'description': sub_phase.get('description', ''),
                            'duration': sub_phase.get('duration'),
                            'priority': self.get_priority_value(sub_phase.get('priority')),
                            'parent_id': phase_id,
                            'parent_status': data.get('status'),
                            'status': sub_phase.get('status'),
                            'dependencies': sub_phase.get('dependencies', []),
                            'deliverables': sub_phase.get('deliverables', []),
                            'is_leaf': True
                        }
                        tasks.append(task)

        # Also check phases.json for direct phases (no sub-phases structure)
        phases_file = os.path.join(self.plan_dir, 'phases.json')
        if os.path.exists(phases_file):
            data = self.load_json(phases_file)
            phases = data.get('phases', [])

            for phase in phases:
                # Check if task can be worked on
                deps_completed = self.are_dependencies_completed(phase.get('dependencies', []))
                is_pending = phase.get('status') == 'pending'

                if deps_completed and is_pending:
                    task = {
                        'id': phase['id'],
                        'title': phase['title'],
                        'description': phase.get('description', ''),
                        'duration': phase.get('duration'),
                        'priority': self.get_priority_value(phase.get('priority')),
                        'parent_id': None,
                        'parent_status': None,
                        'status': phase.get('status'),
                        'dependencies': phase.get('dependencies', []),
                        'deliverables': phase.get('deliverables', []),
                        'is_leaf': True
                    }
                    tasks.append(task)

        # Sort by priority then by ID
        tasks.sort(key=lambda x: (x['priority'], x['id']))
        return tasks

    def get_leaf_tasks_for_phase(self, phase_id: str) -> List[Dict[str, Any]]:
        """Get leaf tasks for specific phase - supports both individual files and phases.json"""
        tasks = []

        # First try individual file
        individual_file = os.path.join(self.plan_dir, f"{phase_id}.json")
        if os.path.exists(individual_file):
            data = self.load_json(individual_file)

            if data.get('title'):
                phases = data.get('phases', [])
                if phases:
                    # Process sub-phases
                    for sub_phase in phases:
                        if not self.is_true_leaf_phase(sub_phase):
                            continue

                        deps_completed = self.are_dependencies_completed(sub_phase.get('dependencies', []))
                        is_pending = sub_phase.get('status') == 'pending'

                        if deps_completed and is_pending:
                            task = {
                                'id': sub_phase['id'],
                                'title': sub_phase['title'],
                                'description': sub_phase.get('description', ''),
                                'duration': sub_phase.get('duration'),
                                'priority': self.get_priority_value(sub_phase.get('priority')),
                                'parent_id': phase_id,
                                'parent_status': data.get('status'),
                                'status': sub_phase.get('status'),
                                'dependencies': sub_phase.get('dependencies', []),
                                'deliverables': sub_phase.get('deliverables', []),
                                'is_leaf': True
                            }
                            tasks.append(task)
            else:
                # This is a direct phase (no sub-phases)
                deps_completed = self.are_dependencies_completed(data.get('dependencies', []))
                is_pending = data.get('status') == 'pending'

                if deps_completed and is_pending:
                    task = {
                        'id': data['id'],
                        'title': data['title'],
                        'description': data.get('description', ''),
                        'duration': data.get('duration'),
                        'priority': self.get_priority_value(data.get('priority')),
                        'parent_id': None,
                        'parent_status': None,
                        'status': data.get('status'),
                        'dependencies': data.get('dependencies', []),
                        'deliverables': data.get('deliverables', []),
                        'is_leaf': True
                    }
                    tasks.append(task)

        # Then try phases.json
        phases_file = os.path.join(self.plan_dir, 'phases.json')
        if os.path.exists(phases_file):
            data = self.load_json(phases_file)
            phases = data.get('phases', [])

            for phase in phases:
                if str(phase['id']) == str(phase_id):
                    deps_completed = self.are_dependencies_completed(phase.get('dependencies', []))
                    is_pending = phase.get('status') == 'pending'

                    if deps_completed and is_pending:
                        task = {
                            'id': phase['id'],
                            'title': phase['title'],
                            'description': phase.get('description', ''),
                            'duration': phase.get('duration'),
                            'priority': self.get_priority_value(phase.get('priority')),
                            'parent_id': None,
                            'parent_status': None,
                            'status': phase.get('status'),
                            'dependencies': phase.get('dependencies', []),
                            'deliverables': phase.get('deliverables', []),
                            'is_leaf': True
                        }
                        tasks.append(task)

        # Sort by priority then by ID
        tasks.sort(key=lambda x: (x['priority'], x['id']))
        return tasks

    def format_tasks(self, tasks: List[Dict[str, Any]], limit: int = 5) -> str:
        """Format tasks as readable string"""
        limited_tasks = tasks[:limit]

        if not limited_tasks:
            return "No leaf tasks available."

        result = []
        for i, task in enumerate(limited_tasks, 1):
            result.append(f"{i}. [{task['id']}] {task['title']}")
            result.append(f"   Priority: {task['priority']} | Parent: {task['parent_id']}")
            if task['dependencies']:
                result.append(f"   Dependencies: {', '.join(task['dependencies'])}")
            result.append("")

        return "\n".join(result)


# Simple usage example
if __name__ == "__main__":
    import sys

    finder = LeafTaskFinder()

    if len(sys.argv) > 1 and sys.argv[1] == '--phase':
        if len(sys.argv) > 2:
            phase_id = sys.argv[2]
            tasks = finder.get_leaf_tasks_for_phase(phase_id)
            print(f"🔍 Leaf tasks for Phase {phase_id}:")
        else:
            print("Please provide phase ID: --phase <id>")
            sys.exit(1)
    else:
        tasks = finder.get_all_leaf_tasks()
        print("🔍 All available leaf tasks:")

    print(finder.format_tasks(tasks))