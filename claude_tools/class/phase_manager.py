#!/usr/bin/env python3
"""
Phase Manager

Comprehensive phase management for JSON plan files.
Supports both individual files and phases.json formats.
"""

import json
import os
import re
import shutil
from typing import List, Dict, Any, Optional
from ..claude_streamer import ClaudeStreamer


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

    def load_json(self, file_path: str, auto_repair: bool = True) -> Dict[str, Any]:
        """Load JSON file safely with optional auto-repair

        Args:
            file_path: Path to JSON file
            auto_repair: Enable auto-repair using Claude AI if JSON decode fails

        Returns:
            Parsed JSON data as dict, or empty dict if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            if auto_repair:
                print(f"[JSON ERROR] {file_path}: {e}")
                repaired_json = self.repair_json_file(file_path, str(e))
                if repaired_json:
                    try:
                        return json.loads(repaired_json)
                    except json.JSONDecodeError:
                        print(f"[REPAIR] Failed to parse repaired JSON, returning empty dict")
                        return {}
                else:
                    print(f"[REPAIR] Auto-repair failed for {file_path}")
                    return {}
            else:
                print(f"Error loading {file_path}: {e}")
                return {}
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

    def repair_json_file(self, file_path: str, error_message: str) -> Optional[str]:
        """Repair JSON file using Claude AI

        Args:
            file_path: Path to corrupted JSON file
            error_message: JSON decode error message

        Returns:
            Repaired JSON content as string, or None if repair failed
        """
        try:
            # Create backup
            backup_path = f"{file_path}.backup"
            shutil.copy2(file_path, backup_path)
            print(f"[REPAIR] Created backup: {backup_path}")

            # Read corrupted content
            with open(file_path, 'r', encoding='utf-8') as f:
                corrupted_content = f.read()

            # Generate repair prompt for Claude
            repair_prompt = f"""Please fix this JSON syntax error. The file contains phase management data that needs to be valid JSON.

Error: {error_message}

Corrupted JSON content:
```
{corrupted_content}
```

Please fix the JSON syntax error and return ONLY the corrected JSON. Make sure to:
1. Fix any missing quotes, commas, brackets, or braces
2. Ensure proper JSON structure
3. Preserve all the original data and structure
4. Return only valid JSON (no explanations, just the JSON)

Return ONLY the fixed JSON:"""

            # Use ClaudeStreamer to repair
            streamer = ClaudeStreamer(
                permission_mode="acceptEdits",
                output_format="json",
                verbose=False
            )

            print(f"[REPAIR] Attempting to repair {file_path}...")
            repaired_json, exit_code = streamer.get_response(repair_prompt)

            if exit_code == 0 and repaired_json.strip():
                # Validate the repaired JSON
                try:
                    json.loads(repaired_json)

                    # Save repaired content
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(repaired_json)

                    print(f"[REPAIR] Successfully repaired {file_path}")
                    return repaired_json

                except json.JSONDecodeError as e:
                    print(f"[REPAIR] Claude response still invalid JSON: {e}")
                    print(f"[REPAIR] Claude response: {repaired_json[:200]}...")
                    return None
            else:
                print(f"[REPAIR] Claude repair failed with exit code: {exit_code}")
                return None

        except Exception as e:
            print(f"[REPAIR] Error during repair: {e}")
            # Restore from backup if available
            backup_path = f"{file_path}.backup"
            if os.path.exists(backup_path):
                try:
                    shutil.copy2(backup_path, file_path)
                    print(f"[REPAIR] Restored original file from backup")
                except:
                    pass
            return None

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

        # Check for child files based on file name pattern
        for f in all_files:
            other_file_name = os.path.basename(f).replace('.json', '')

            if file_name == "phases":
                # Child of phases.json are numeric files: 1.json, 2.json, etc.
                if other_file_name.isdigit() and int(other_file_name) > 0:
                    return False  # Found child file
            else:
                # Child of X.json are X.Y.json files
                if other_file_name.startswith(f"{file_name}."):
                    # Check if it's a direct child (X.Y) not grandchild (X.Y.Z)
                    parts = other_file_name.split(".")
                    if len(parts) == len(file_name.split(".")) + 1:
                        return False  # Found child file

        return True  # No child files found

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

        # Sort by priority only
        tasks.sort(key=lambda x: x['priority'])
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

        # Process ALL files (not just leaf files) to find sub-phases needing breakdown
        for file_path in all_files:
            phase_data = self.parse_phase_data(file_path)
            if not phase_data or not phase_data['phases']:
                continue

            processed_files.append(phase_data)

            # Check each phase in phases array for breakdown needs
            for phase in phase_data['phases']:
                if phase.get('duration') and self.needs_breakdown(phase.get('duration')):
                    # Check if this phase already has an individual breakdown file
                    phase_id = str(phase.get('id', 'No ID'))
                    individual_file = os.path.join(self.plan_dir, f"{phase_id}.json")

                    # Only add to list if it doesn't have its own breakdown file yet
                    if not os.path.exists(individual_file):
                        leaf_phases.append({
                            'file': phase_data['file_name'],
                            'phase_id': phase_id,
                            'title': phase['title'],
                            'duration': phase['duration'],
                            'status': phase.get('status', 'pending')
                        })

        # Also check phases.json for individual phases that don't have individual files
        phases_file = os.path.join(self.plan_dir, 'phases.json')
        if os.path.exists(phases_file):
            phases_data = self.load_json(phases_file)
            phases = phases_data.get('phases', [])

            for phase in phases:
                phase_id = str(phase['id'])
                individual_file = os.path.join(self.plan_dir, f"{phase_id}.json")

                # Check if this phase is a leaf (no individual file exists)
                if not os.path.exists(individual_file):
                    if phase.get('duration') and self.needs_breakdown(phase.get('duration')):
                        leaf_phases.append({
                            'file': 'phases.json',
                            'phase_id': phase_id,
                            'title': phase['title'],
                            'duration': phase['duration'],
                            'status': phase.get('status', 'pending')
                        })

        # Remove duplicates and sort by duration (largest first)
        unique_phases = []
        seen_ids = set()
        for phase in leaf_phases:
            phase_key = f"{phase['file']}:{phase['phase_id']}"
            if phase_key not in seen_ids:
                seen_ids.add(phase_key)
                unique_phases.append(phase)

        # Sort by duration (largest first) for priority processing
        unique_phases.sort(key=lambda x: int(x['duration']), reverse=True)

        # Filter to show only top results (matches JavaScript limit)
        return unique_phases[:limit]

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

    # ==================== CONTEXT INHERITANCE SYSTEM ====================

    def build_strategic_context(self, phase_id: str) -> Dict[str, Any]:
        """
        Build complete strategic context from project root to target phase.
        Provides hierarchical context for guided breakdown decisions.

        Args:
            phase_id: Target phase ID (e.g., "1", "1.1", "1.1.1")

        Returns:
            Complete strategic context including project DNA, parent chain, and constraints
        """
        context = {
            "strategic_dna": self._get_project_strategic_dna(),
            "parent_chain": self._build_parent_chain(phase_id),
            "sibling_coordination": self._get_sibling_coordination(phase_id),
            "boundary_constraints": self._get_boundary_constraints(phase_id),
            "current_phase": self._get_current_phase_info(phase_id)
        }

        return context

    def _get_project_strategic_dna(self) -> Dict[str, Any]:
        """Extract project-level strategic DNA from phases.json"""
        phases_file = os.path.join(self.plan_dir, 'phases.json')
        if not os.path.exists(phases_file):
            return self._default_strategic_dna()

        data = self.load_json(phases_file)
        project = data.get('project', {})

        return {
            "project_vision": project.get('title', 'Unknown Project'),
            "project_goal": project.get('description', ''),
            "project_type": project.get('type', 'unknown'),
            "complexity": project.get('complexity', 'medium'),
            "total_phases": project.get('totalPhases', 0),
            "estimated_duration": project.get('estimatedDuration', 0),
            "architectural_principles": self._extract_architectural_principles(project),
            "critical_success_factors": self._extract_success_factors(project)
        }

    def _default_strategic_dna(self) -> Dict[str, Any]:
        """Default strategic DNA when no phases.json exists"""
        return {
            "project_vision": "Unknown Project",
            "project_goal": "No project description available",
            "project_type": "unknown",
            "complexity": "medium",
            "total_phases": 0,
            "estimated_duration": 0,
            "architectural_principles": ["Quality", "Maintainability", "Performance"],
            "critical_success_factors": ["Functionality", "Quality", "Performance"]
        }

    def _extract_architectural_principles(self, project: Dict[str, Any]) -> List[str]:
        """Extract architectural principles from project data"""
        principles = []

        # Extract from project type
        project_type = project.get('type', '').lower()
        if 'web' in project_type:
            principles.extend(["Web Standards", "Responsive Design"])
        if 'app' in project_type:
            principles.extend(["User Experience", "Performance"])
        if 'api' in project_type:
            principles.extend(["REST Principles", "Documentation"])
        if 'enterprise' in project.get('complexity', '').lower():
            principles.extend(["Scalability", "Security", "Maintainability"])

        # Extract from description
        description = project.get('description', '').lower()
        if 'microservices' in description:
            principles.append("Microservices Architecture")
        if 'react' in description:
            principles.append("React Component Architecture")
        if 'node' in description:
            principles.append("Node.js Backend Architecture")

        return principles or ["Clean Architecture", "SOLID Principles"]

    def _extract_success_factors(self, project: Dict[str, Any]) -> List[str]:
        """Extract critical success factors from project data"""
        factors = []

        description = project.get('description', '').lower()
        if 'performance' in description or 'scalability' in description:
            factors.append("Performance & Scalability")
        if 'user' in description or 'ui' in description:
            factors.append("User Experience")
        if 'api' in description:
            factors.append("API Reliability")
        if 'testing' in description:
            factors.append("Test Coverage")
        if 'security' in description:
            factors.append("Security")

        return factors or ["Functionality", "Quality", "Performance"]

    def _build_parent_chain(self, phase_id: str) -> List[Dict[str, Any]]:
        """Build chain of parent phases from root to immediate parent"""
        parent_chain = []
        # Convert to string to handle both int and string inputs
        phase_id_str = str(phase_id)
        parts = phase_id_str.split('.')

        # Start with project root (phases.json)
        project_root = self._get_project_root_info()
        if project_root:
            parent_chain.append({
                "level": 0,
                "id": "project",
                "title": project_root['title'],
                "goal": project_root['goal'],
                "type": "project_root"
            })

        # Add each parent in the chain
        for i in range(len(parts) - 1):
            parent_id = '.'.join(parts[:i+1])
            parent_info = self._get_phase_info(parent_id)
            if parent_info:
                parent_chain.append({
                    "level": i + 1,
                    "id": parent_id,
                    "title": parent_info['title'],
                    "goal": parent_info['description'],
                    "deliverables": parent_info.get('deliverables', []),
                    "type": "parent_phase"
                })

        return parent_chain

    def _get_project_root_info(self) -> Optional[Dict[str, Any]]:
        """Get project root information from phases.json"""
        phases_file = os.path.join(self.plan_dir, 'phases.json')
        if not os.path.exists(phases_file):
            return None

        data = self.load_json(phases_file)
        project = data.get('project', {})

        return {
            "title": project.get('title', 'Project'),
            "goal": project.get('description', ''),
            "total_phases": project.get('totalPhases', 0),
            "estimated_duration": project.get('estimatedDuration', 0)
        }

    def _get_phase_info(self, phase_id: str) -> Optional[Dict[str, Any]]:
        """Get phase information from individual file or phases.json"""
        # Try individual file first
        phase_file = os.path.join(self.plan_dir, f"{phase_id}.json")
        if os.path.exists(phase_file):
            data = self.load_json(phase_file)
            return {
                "title": data.get('title', ''),
                "description": data.get('description', ''),
                "deliverables": data.get('deliverables', [])
            }

        # Try phases.json
        phases_file = os.path.join(self.plan_dir, 'phases.json')
        if os.path.exists(phases_file):
            data = self.load_json(phases_file)
            phases = data.get('phases', [])
            for phase in phases:
                if str(phase['id']) == phase_id:
                    return {
                        "title": phase.get('title', ''),
                        "description": phase.get('description', ''),
                        "deliverables": phase.get('deliverables', [])
                    }

        return None

    def _get_sibling_coordination(self, phase_id: str) -> Dict[str, Any]:
        """Get coordination requirements with sibling phases"""
        # Convert to string to handle both int and string inputs
        phase_id_str = str(phase_id)
        parts = phase_id_str.split('.')

        if len(parts) == 1:
            # Root level - no siblings for coordination
            return {
                "has_siblings": False,
                "coordination_points": []
            }

        parent_id = '.'.join(parts[:-1])
        siblings = self._get_sibling_phases(phase_id, parent_id)

        coordination_points = []
        for sibling in siblings:
            coordination_points.append({
                "sibling_id": sibling['id'],
                "sibling_title": sibling['title'],
                "coordination_type": self._determine_coordination_type(phase_id, sibling),
                "dependency_notes": self._get_dependency_notes(phase_id, sibling)
            })

        return {
            "has_siblings": len(siblings) > 0,
            "coordination_points": coordination_points
        }

    def _get_sibling_phases(self, phase_id: str, parent_id: str) -> List[Dict[str, Any]]:
        """Get all sibling phases of the given phase"""
        parent_file = os.path.join(self.plan_dir, f"{parent_id}.json")
        siblings = []

        if os.path.exists(parent_file):
            parent_data = self.load_json(parent_file)
            phases = parent_data.get('phases', [])
            for phase in phases:
                if phase['id'] != phase_id:
                    siblings.append({
                        "id": phase['id'],
                        "title": phase.get('title', ''),
                        "description": phase.get('description', ''),
                        "deliverables": phase.get('deliverables', [])
                    })

        return siblings

    def _determine_coordination_type(self, phase_id: str, sibling: Dict[str, Any]) -> str:
        """Determine coordination type with sibling phase"""
        # Simple logic - can be enhanced based on project specifics
        sibling_id = sibling['id']

        if '.' in phase_id and '.' in sibling_id:
            # Both are sub-phases - likely parallel work
            return "parallel_execution"
        elif sibling_id.endswith('.1') or phase_id.endswith('.1'):
            # One is foundation for the other
            return "sequential_dependency"
        else:
            return "independent_coordination"

    def _get_dependency_notes(self, phase_id: str, sibling: Dict[str, Any]) -> str:
        """Get specific dependency coordination notes"""
        # Use file path notation to give AI direct access to phase content
        return f"Coordinate deliverables to ensure integration compatibility between @.ai/plan/{phase_id}.json and @.ai/plan/{sibling['id']}.json"

    def _get_boundary_constraints(self, phase_id: str) -> Dict[str, Any]:
        """Get boundary constraints for the phase breakdown"""
        parent_info = self._get_parent_info(phase_id)

        constraints = {
            "must_include": [],
            "must_not_include": [],
            "architectural_constraints": [],
            "scope_limits": []
        }

        if parent_info:
            # Extract constraints from parent description and deliverables
            description = parent_info.get('description', '').lower()
            deliverables = parent_info.get('deliverables', [])

            # MUST include based on parent goals
            if 'architecture' in description:
                constraints["must_include"].append("Architectural consistency")
            if 'api' in description:
                constraints["must_include"].append("API design principles")
            if 'security' in description:
                constraints["must_include"].append("Security considerations")

            # MUST NOT include based on scope
            if 'foundation' in description:
                constraints["must_not_include"].append("Advanced features beyond foundation")
            if 'basic' in description:
                constraints["must_not_include"].append("Complex implementations")

            # Architectural constraints
            constraints["architectural_constraints"] = self._extract_architectural_principles({"description": parent_info.get('description', '')})

            # Scope limits based on deliverables
            for deliverable in deliverables:
                constraints["scope_limits"].append(f"Focus on: {deliverable}")

        return constraints

    def _get_parent_info(self, phase_id: str) -> Optional[Dict[str, Any]]:
        """Get immediate parent information"""
        # Convert to string to handle both int and string inputs
        phase_id_str = str(phase_id)
        parts = phase_id_str.split('.')
        if len(parts) <= 1:
            return None

        parent_id = '.'.join(parts[:-1])
        return self._get_phase_info(parent_id)

    def _get_current_phase_info(self, phase_id: str) -> Dict[str, Any]:
        """Get current phase information"""
        current_info = self._get_phase_info(phase_id)

        if not current_info:
            return {
                "id": phase_id,
                "title": "Unknown Phase",
                "description": "No description available",
                "deliverables": []
            }

        current_info["id"] = phase_id
        return current_info

    def validate_breakdown_alignment(self, breakdown_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate breakdown result against strategic context with expert coverage analysis
        Returns validation results with specific feedback
        """
        validation = {
            "is_valid": True,
            "strategic_alignment": {"passed": True, "issues": []},
            "boundary_compliance": {"passed": True, "issues": []},
            "coordination_check": {"passed": True, "issues": []},
            "architecture_consistency": {"passed": True, "issues": []},
            "expert_coverage": {"passed": True, "issues": []},
            "overall_score": 0,
            "recommendations": []
        }

        # Check strategic alignment
        validation["strategic_alignment"] = self._check_strategic_alignment(breakdown_result, context)

        # Check boundary compliance
        validation["boundary_compliance"] = self._check_boundary_compliance(breakdown_result, context)

        # Check coordination requirements
        validation["coordination_check"] = self._check_coordination_requirements(breakdown_result, context)

        # Check architectural consistency
        validation["architecture_consistency"] = self._check_architectural_consistency(breakdown_result, context)

        # NEW: Check expert perspective coverage
        validation["expert_coverage"] = self._check_expert_coverage(breakdown_result, context)

        # Calculate overall score (now includes expert coverage)
        all_passed = all([
            validation["strategic_alignment"]["passed"],
            validation["boundary_compliance"]["passed"],
            validation["coordination_check"]["passed"],
            validation["architecture_consistency"]["passed"],
            validation["expert_coverage"]["passed"]
        ])

        validation["is_valid"] = all_passed
        validation["overall_score"] = self._calculate_quality_score(validation)
        validation["recommendations"] = self._generate_recommendations(validation)

        return validation

    def _check_strategic_alignment(self, breakdown: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if breakdown aligns with strategic goals"""
        result = {"passed": True, "issues": []}

        phases = breakdown.get('phases', [])
        parent_goal = context.get('parent_chain', [{}])[-1].get('goal', '').lower()

        for phase in phases:
            phase_desc = phase.get('description', '').lower()
            phase_title = phase.get('title', '').lower()

            # Check if phase supports parent goals
            if not any(word in phase_desc or word in phase_title for word in parent_goal.split() if len(word) > 3):
                result["issues"].append(f"Phase {phase.get('id')} may not align with parent goal: {parent_goal[:50]}...")

        result["passed"] = len(result["issues"]) == 0
        return result

    def _check_boundary_compliance(self, breakdown: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if breakdown respects boundary constraints"""
        result = {"passed": True, "issues": []}

        constraints = context.get('boundary_constraints', {})
        must_not = constraints.get('must_not_include', [])
        phases = breakdown.get('phases', [])

        for phase in phases:
            phase_text = f"{phase.get('title', '')} {phase.get('description', '')}".lower()

            for constraint in must_not:
                if any(word in phase_text for word in constraint.lower().split() if len(word) > 3):
                    result["issues"].append(f"Phase {phase.get('id')} may violate constraint: {constraint}")

        result["passed"] = len(result["issues"]) == 0
        return result

    def _check_coordination_requirements(self, breakdown: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if breakdown addresses coordination requirements"""
        result = {"passed": True, "issues": []}

        coordination = context.get('sibling_coordination', {})
        if coordination.get('has_siblings'):
            coordination_points = coordination.get('coordination_points', [])

            # Check if breakdown considers coordination
            phases = breakdown.get('phases', [])
            has_coordination_focus = any(
                'coordinate' in phase.get('description', '').lower() or
                'integrate' in phase.get('description', '').lower() or
                'align' in phase.get('description', '').lower()
                for phase in phases
            )

            if not has_coordination_focus and coordination_points:
                result["issues"].append("Breakdown should include coordination/integration phases for sibling alignment")

        result["passed"] = len(result["issues"]) == 0
        return result

    def _check_architectural_consistency(self, breakdown: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if breakdown maintains architectural consistency"""
        result = {"passed": True, "issues": []}

        principles = context.get('strategic_dna', {}).get('architectural_principles', [])
        phases = breakdown.get('phases', [])

        if not principles:
            return result

        # Simple check - can be enhanced
        for phase in phases:
            phase_text = f"{phase.get('title', '')} {phase.get('description', '')}".lower()

            if 'security' in principles and 'security' not in phase_text:
                result["issues"].append(f"Phase {phase.get('id')} should consider security aspects")

            if 'performance' in principles and 'performance' not in phase_text:
                result["issues"].append(f"Phase {phase.get('id')} should consider performance aspects")

        result["passed"] = len(result["issues"]) <= len(principles) // 2  # Allow some flexibility
        return result

    def _calculate_quality_score(self, validation: Dict[str, Any]) -> int:
        """Calculate overall quality score (0-100)"""
        checks = [
            validation["strategic_alignment"]["passed"],
            validation["boundary_compliance"]["passed"],
            validation["coordination_check"]["passed"],
            validation["architecture_consistency"]["passed"]
        ]

        passed_checks = sum(checks)
        base_score = (passed_checks / len(checks)) * 80  # Base score from passed checks

        # Deduct points for issues
        total_issues = sum(
            len(validation[key]["issues"])
            for key in ["strategic_alignment", "boundary_compliance", "coordination_check", "architecture_consistency"]
        )

        issue_penalty = min(total_issues * 5, 20)  # Max 20 point penalty
        return max(0, int(base_score - issue_penalty))

    def _check_expert_coverage(self, breakdown: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Check if breakdown considers multiple expert perspectives"""
        result = {"passed": True, "issues": []}

        phases = breakdown.get('phases', [])
        if not phases:
            result["issues"].append("No sub-phases found for expert analysis")
            result["passed"] = False
            return result

        # Get project characteristics for expert prioritization
        dna = context.get('strategic_dna', {})
        project_type = dna.get('project_type', '').lower()
        complexity = dna.get('complexity', '').lower()
        principles = dna.get('architectural_principles', [])

        # Check for core expert coverage
        all_phase_text = " ".join([
            f"{phase.get('title', '')} {phase.get('description', '')} {' '.join(phase.get('deliverables', []))}"
            for phase in phases
        ]).lower()

        # Performance Expert Check
        performance_keywords = ['performance', 'scalability', 'optimization', 'efficient', 'speed', 'resource', 'memory', 'cpu']
        if not any(keyword in all_phase_text for keyword in performance_keywords):
            result["issues"].append("Performance Expert perspective missing - no performance/scalability considerations found")

        # Security Expert Check
        security_keywords = ['security', 'auth', 'encrypt', 'protect', 'vulnerability', 'safe', 'secure']
        if not any(keyword in all_phase_text for keyword in security_keywords):
            result["issues"].append("Security Expert perspective missing - no security considerations found")

        # Architecture Expert Check
        architecture_keywords = ['architecture', 'structure', 'design', 'pattern', 'maintain', 'organize', 'modular']
        if not any(keyword in all_phase_text for keyword in architecture_keywords):
            result["issues"].append("Architecture Expert perspective missing - no architectural considerations found")

        # Domain-specific Expert Checks
        if 'web' in project_type or 'app' in project_type:
            frontend_keywords = ['ui', 'ux', 'interface', 'frontend', 'component', 'responsive']
            backend_keywords = ['api', 'backend', 'server', 'service', 'logic', 'data']

            has_frontend = any(keyword in all_phase_text for keyword in frontend_keywords)
            has_backend = any(keyword in all_phase_text for keyword in backend_keywords)

            if not (has_frontend or has_backend):
                result["issues"].append("Domain Expert perspective missing - no frontend/backend considerations found")

        if 'api' in project_type:
            api_keywords = ['api', 'rest', 'endpoint', 'contract', 'integration', 'service']
            if not any(keyword in all_phase_text for keyword in api_keywords):
                result["issues"].append("API Expert perspective missing - no API design considerations found")

        if 'enterprise' in complexity:
            testing_keywords = ['test', 'coverage', 'quality', 'validation', 'verification']
            database_keywords = ['database', 'schema', 'query', 'data', 'storage']

            has_testing = any(keyword in all_phase_text for keyword in testing_keywords)
            has_database = any(keyword in all_phase_text for keyword in database_keywords)

            if not has_testing:
                result["issues"].append("Testing Expert perspective missing - enterprise projects require comprehensive testing strategy")
            if not has_database:
                result["issues"].append("Database Expert perspective missing - enterprise projects typically require database considerations")

        # Check for expert conflict resolution indicators
        conflict_resolution_keywords = ['trade-off', 'balance', 'compromise', 'prioritize', 'optimize']
        if not any(keyword in all_phase_text for keyword in conflict_resolution_keywords):
            result["issues"].append("Expert conflict resolution not evident - no indication of trade-off decisions or prioritization")

        # Check for risk mitigation (expert-driven)
        risk_keywords = ['risk', 'mitigation', 'backup', 'fallback', 'contingency', 'error handling']
        if not any(keyword in all_phase_text for keyword in risk_keywords):
            result["issues"].append("Risk mitigation missing - experts typically identify and address potential risks")

        # Allow some flexibility - don't fail if only minor issues
        critical_issues = [
            issue for issue in result["issues"]
            if "Performance Expert" in issue or "Security Expert" in issue or "Architecture Expert" in issue
        ]

        result["passed"] = len(critical_issues) == 0

        return result

    def _generate_recommendations(self, validation: Dict[str, Any]) -> List[str]:
        """Generate specific recommendations for improvement"""
        recommendations = []

        for check_name, check_result in validation.items():
            if check_name.endswith('_check') or check_name.endswith('_alignment') or check_name.endswith('_compliance') or check_name.endswith('_consistency') or check_name.endswith('_coverage'):
                if not check_result["passed"]:
                    recommendations.extend(check_result["issues"])

        if not recommendations:
            recommendations.append("Breakdown appears well-aligned with strategic context and expert perspectives")

        return recommendations

