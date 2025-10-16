#!/usr/bin/env python3
"""
Phase Manager

Comprehensive phase management for JSON plan files.
Supports both individual files and phases.json formats.
"""

import json
import os
import re
from typing import List, Dict, Any, Optional


class PhaseManager:
    """Comprehensive phase management class."""

    def __init__(self, plan_dir: str = ".ai/plan"):
        """
        Initialize with plan directory path

        Args:
            plan_dir: Path to directory containing plan JSON files
        """
        self.plan_dir = plan_dir

    # ==================== HELPER METHODS ====================

    def load_json(self, file_path: str) -> Dict[str, Any]:
        """Load JSON file safely"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            return {}

    def save_json(self, file_path: str, data: Dict[str, Any]) -> bool:
        """Save JSON file safely"""
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving {file_path}: {e}")
            return False

    def get_all_plan_files(self) -> List[str]:
        """Get all plan JSON files (recursive scan, excluding phases.json and index.json)"""
        if not os.path.exists(self.plan_dir):
            return []

        files = []

        def scan_directory(dir_path):
            try:
                for item in os.listdir(dir_path):
                    full_path = os.path.join(dir_path, item)

                    if os.path.isdir(full_path):
                        scan_directory(full_path)  # Recursive scan
                    elif item.endswith('.json') and item != 'index.json':
                        files.append(full_path)
            except (OSError, PermissionError):
                # Skip directories we can't access
                pass

        scan_directory(self.plan_dir)
        return sorted(files)

    def get_priority_value(self, priority) -> int:
        """Convert priority string to number for sorting"""
        if isinstance(priority, str):
            priority_map = {'high': 1, 'medium': 2, 'low': 3}
            return priority_map.get(priority.lower(), 999)
        return priority or 999

    def needs_breakdown(self, duration) -> bool:
        """Check if duration > 60 minutes (matches JavaScript needsBreakdown)"""
        if not duration:
            return False

        duration_str = str(duration)
        if '-' in duration_str:
            # Range format: "960-1440"
            min_val, max_val = duration_str.split('-')
            min_minutes = int(min_val.strip())
            max_minutes = int(max_val.strip())
            return min_minutes > 60 or max_minutes > 60
        else:
            # Single value: "960"
            minutes = int(duration_str)
            return minutes > 60

    def log_duration_check(self, phase_id: str, duration) -> bool:
        """Log duration check result (matches JavaScript logDurationCheck)"""
        needs_break = self.needs_breakdown(duration)
        result = "OK needs breakdown" if needs_break else "NO no breakdown"
        print(f"Phase {phase_id}: {duration} minutes -> {result}")
        return needs_break

    def is_leaf_phase(self, file_path: str, all_files: List[str]) -> bool:
        """Check if phase is leaf (no child files)"""
        file_name = os.path.basename(file_path).replace('.json', '')
        child_pattern = re.compile(f'^{file_name.replace(".", "\\.")}\\.\\d+\\.json$')

        return not any(child_pattern.search(os.path.basename(f)) for f in all_files)

    # ==================== STATUS METHODS ====================

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

    def update_parent_status_if_all_children_completed(self, child_phase_id: str) -> bool:
        """Auto-update parent status if all children completed"""
        parts = child_phase_id.split('.')
        if len(parts) <= 1:
            return True  # No parent for main phases

        parent_phase_id = '.'.join(parts[:-1])
        parent_file = os.path.join(self.plan_dir, f"{parent_phase_id}.json")

        if not os.path.exists(parent_file):
            return True

        parent_data = self.load_json(parent_file)
        if not parent_data or not parent_data.get('phases'):
            return True

        # Check if all children are completed
        all_children_completed = all(
            child.get('status') == 'completed'
            for child in parent_data['phases']
        )

        if all_children_completed and parent_data.get('status') != 'completed':
            old_status = parent_data.get('status', 'pending')
            parent_data['status'] = 'completed'

            if self.save_json(parent_file, parent_data):
                print(f"AUTO-UPDATE: {parent_phase_id}: {old_status} -> completed")
                return self.update_parent_status_if_all_children_completed(parent_phase_id)

        return True

    # ==================== FINDER METHODS ====================

    def get_workable_phases(self) -> List[Dict[str, Any]]:
        """Get workable phases that can be worked on"""
        if not os.path.exists(self.plan_dir):
            return []

        # Get all individual files first
        all_files = self.get_all_plan_files()
        tasks = []

        # Process individual files (like JS version)
        for file_path in all_files:
            phase_id = os.path.basename(file_path).replace('.json', '')
            data = self.load_json(file_path)

            if not data.get('title'):
                continue

            # If this phase has sub-phases, check each sub-phase
            phases = data.get('phases', [])
            if phases:
                for sub_phase in phases:
                    if not self.is_true_leaf_phase(sub_phase):
                        continue  # Skip non-leaf nodes

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

    
    def parse_phase_data(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse phase data from file (matches JavaScript parsePhaseData)"""
        try:
            data = self.load_json(file_path)
            if not data:
                return None

            phases = []
            if data.get('phases') and isinstance(data['phases'], list):
                for phase in data['phases']:
                    phases.append({
                        'id': phase.get('id', 'undefined'),
                        'title': phase.get('title', 'No title'),
                        'duration': phase.get('duration', '0'),
                        'status': phase.get('status', 'pending')
                    })

            return {
                'file_path': file_path,
                'file_name': os.path.basename(file_path),
                'phases': phases,
                'breakdown_complete': data.get('breakdown_complete', False)
            }
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return None

    def find_phases_needing_breakdown(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Find phases with duration > 60 minutes that need breakdown"""
        all_files = self.get_all_plan_files()
        leaf_phases = []
        processed_files = []

        for file_path in all_files:
            if not self.is_leaf_phase(file_path, all_files):
                continue

            phase_data = self.parse_phase_data(file_path)
            if not phase_data or not phase_data['phases']:
                continue

            processed_files.append(phase_data)

            # Check each phase in phases array (matches JavaScript logic)
            for phase in phase_data['phases']:
                if phase.get('duration') and self.needs_breakdown(phase.get('duration')):
                    leaf_phases.append({
                        'file': phase_data['file_name'],
                        'phase_id': phase.get('id', 'No ID'),
                        'title': phase['title'],
                        'duration': phase['duration'],
                        'status': phase.get('status', 'pending')
                    })

        # Filter to show only top results (matches JavaScript limit)
        return leaf_phases[:limit]

    # ==================== STATUS UPDATE METHODS ====================

    def update_status(self, phase_id: str, new_status: str) -> bool:
        """Update status of phase and cascade updates"""
        valid_statuses = ['pending', 'in-progress', 'completed']
        if new_status not in valid_statuses:
            print(f"Invalid status: {new_status}. Valid: {valid_statuses}")
            return False

        # Try individual file first
        individual_file = os.path.join(self.plan_dir, f"{phase_id}.json")
        if os.path.exists(individual_file):
            data = self.load_json(individual_file)
            old_status = data.get('status', 'pending')
            data['status'] = new_status

            # Update sub-phases if exist
            if data.get('phases'):
                for sub_phase in data['phases']:
                    sub_phase['status'] = new_status

            if self.save_json(individual_file, data):
                print(f"SUCCESS: {phase_id}: {old_status} -> {new_status}")

                # Update sub-phases
                if data.get('phases'):
                    for sub_phase in data['phases']:
                        self.update_status(sub_phase['id'], new_status)

                # Auto-update parent if completed
                if new_status == 'completed':
                    self.update_parent_status_if_all_children_completed(phase_id)

                return True

        # Try phases.json
        phases_file = os.path.join(self.plan_dir, 'phases.json')
        if os.path.exists(phases_file):
            data = self.load_json(phases_file)
            phases = data.get('phases', [])

            for phase in phases:
                if str(phase['id']) == str(phase_id):
                    old_status = phase.get('status', 'pending')
                    phase['status'] = new_status

                    if self.save_json(phases_file, data):
                        print(f"SUCCESS: {phase_id}: {old_status} -> {new_status}")
                        return True

        print(f"Phase not found: {phase_id}")
        return False

    def update_all_status(self, new_status: str) -> int:
        """Update status of all phases"""
        count = 0

        # Update phases.json
        phases_file = os.path.join(self.plan_dir, 'phases.json')
        if os.path.exists(phases_file):
            data = self.load_json(phases_file)
            if data.get('phases'):
                for phase in data['phases']:
                    phase['status'] = new_status
                if self.save_json(phases_file, data):
                    print(f"SUCCESS: phases.json updated")
                    count += 1

        # Update individual files
        all_files = self.get_all_plan_files()
        for file_path in all_files:
            phase_id = os.path.basename(file_path).replace('.json', '')
            if self.update_status(phase_id, new_status):
                count += 1

        return count

    # ==================== DISPLAY METHODS ====================

    def list_phases(self) -> None:
        """List all phases with their status"""
        print("\n=== All Phase Status ===\n")

        # Load main phases from phases.json
        phases_file = os.path.join(self.plan_dir, 'phases.json')
        if os.path.exists(phases_file):
            data = self.load_json(phases_file)
            if data.get('phases'):
                print("Main Phases:")
                for phase in data['phases']:
                    print(f"  Phase {phase['id']}: {phase['title']} [{phase.get('status', 'unknown')}]")
                print()

        # Load detailed phase files
        print("Detailed Phase Files:")
        all_files = self.get_all_plan_files()

        for file_path in all_files:
            phase_id = os.path.basename(file_path).replace('.json', '')
            data = self.load_json(file_path)

            if data:
                indent = '  └─ ' if '.' in phase_id else '  '
                status = data.get('status', 'unknown')
                title = data.get('title', 'Untitled')

                print(f"{indent}{phase_id}: {title} [{status}]")

                # Show sub-phases count if exists
                if data.get('phases'):
                    print(f"{indent}  └─ {len(data['phases'])} sub-phases")

        print()

    def format_tasks(self, tasks: List[Dict[str, Any]], limit: int = 5) -> str:
        """Format tasks as readable string"""
        limited_tasks = tasks[:limit]

        if not limited_tasks:
            return "No workable phases available."

        result = []
        for i, task in enumerate(limited_tasks, 1):
            result.append(f"{i}. [{task['id']}] {task['title']}")
            result.append(f"   Priority: {task['priority']} | Parent: {task.get('parent_id', 'None')}")
            if task.get('duration'):
                result.append(f"   Duration: {task['duration']}")
            if task.get('dependencies'):
                result.append(f"   Dependencies: {', '.join(task['dependencies'])}")
            result.append("")

        return "\n".join(result)

    def format_phases_needing_breakdown(self, phases: List[Dict[str, Any]]) -> str:
        """Format phases with duration >60min that need breakdown"""
        if not phases:
            return "SUCCESS: No phases with duration >60 minutes need breakdown!"

        result = [f"FOUND: {len(phases)} phases with duration >60 minutes need breakdown\n"]

        # Group by file
        grouped = {}
        for phase in phases:
            file_name = phase['file']
            if file_name not in grouped:
                grouped[file_name] = []
            grouped[file_name].append(phase)

        for file_name, phase_list in grouped.items():
            result.append(f"File: {file_name}")
            for phase in phase_list:
                result.append(f"   - Phase {phase['phase_id']}: {phase['title']}")
                result.append(f"     Duration: {phase['duration']} minutes")
                result.append(f"     Status: {phase['status']}")
                result.append("")

        return "\n".join(result)


