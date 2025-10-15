#!/usr/bin/env python3
"""
Test suite for PhaseManager class

Comprehensive test coverage for all PhaseManager functionality including:
- JSON loading/saving
- Phase status management
- Leaf task identification
- Dependency checking
- Status updates and cascading
- CLI command functionality
"""

import unittest
import json
import os
import tempfile
import shutil
from unittest.mock import patch, mock_open
import sys

# Add the parent directory to the path to import the class
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import using importlib to avoid the class keyword issue
import importlib.util
spec = importlib.util.spec_from_file_location("phase_manager", os.path.join(os.path.dirname(__file__), "..", "class", "phase_manager.py"))
phase_manager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase_manager_module)
PhaseManager = phase_manager_module.PhaseManager


class TestPhaseManager(unittest.TestCase):
    """Test cases for PhaseManager class"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.plan_dir = os.path.join(self.test_dir, '.ai', 'plan')
        os.makedirs(self.plan_dir, exist_ok=True)
        self.manager = PhaseManager(self.plan_dir)

    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    def create_test_file(self, filename, content):
        """Helper to create test JSON files"""
        file_path = os.path.join(self.plan_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2)
        return file_path

    # ==================== INITIALIZATION TESTS ====================

    def test_init_default_plan_dir(self):
        """Test PhaseManager initialization with default directory"""
        manager = PhaseManager()
        self.assertEqual(manager.plan_dir, ".ai/plan")

    def test_init_custom_plan_dir(self):
        """Test PhaseManager initialization with custom directory"""
        custom_dir = "/custom/plan/path"
        manager = PhaseManager(custom_dir)
        self.assertEqual(manager.plan_dir, custom_dir)

    # ==================== JSON HELPER TESTS ====================

    def test_load_json_valid_file(self):
        """Test loading valid JSON file"""
        test_data = {"id": "1", "title": "Test Phase", "status": "pending"}
        file_path = self.create_test_file("test.json", test_data)

        result = self.manager.load_json(file_path)
        self.assertEqual(result, test_data)

    def test_load_json_invalid_file(self):
        """Test loading invalid JSON file"""
        file_path = os.path.join(self.plan_dir, "invalid.json")
        with open(file_path, 'w') as f:
            f.write("invalid json content")

        result = self.manager.load_json(file_path)
        self.assertEqual(result, {})

    def test_load_json_nonexistent_file(self):
        """Test loading non-existent file"""
        result = self.manager.load_json("/non/existent/file.json")
        self.assertEqual(result, {})

    def test_save_json_success(self):
        """Test successful JSON file saving"""
        test_data = {"id": "1", "title": "Test Phase", "status": "pending"}
        file_path = os.path.join(self.plan_dir, "save_test.json")

        result = self.manager.save_json(file_path, test_data)
        self.assertTrue(result)

        # Verify file was created with correct content
        with open(file_path, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        self.assertEqual(saved_data, test_data)

    def test_save_json_failure(self):
        """Test JSON file saving failure"""
        test_data = {"id": "1", "title": "Test Phase"}
        # Try to save to invalid path (non-existent parent directory)
        invalid_path = os.path.join(self.test_dir, "nonexistent", "test.json")

        result = self.manager.save_json(invalid_path, test_data)
        self.assertFalse(result)

    # ==================== FILE MANAGEMENT TESTS ====================

    def test_get_all_plan_files_empty_directory(self):
        """Test getting plan files from empty directory"""
        files = self.manager.get_all_plan_files()
        self.assertEqual(files, [])

    def test_get_all_plan_files_with_files(self):
        """Test getting plan files from directory with files"""
        # Create test files
        self.create_test_file("1.json", {"id": "1"})
        self.create_test_file("2.json", {"id": "2"})
        self.create_test_file("phases.json", {"phases": []})
        self.create_test_file("readme.txt", "text file")

        files = self.manager.get_all_plan_files()
        self.assertEqual(len(files), 2)
        self.assertTrue(any("1.json" in f for f in files))
        self.assertTrue(any("2.json" in f for f in files))
        self.assertFalse(any("phases.json" in f for f in files))
        self.assertFalse(any("readme.txt" in f for f in files))

    # ==================== PRIORITY TESTS ====================

    def test_get_priority_value_string(self):
        """Test priority value conversion from strings"""
        self.assertEqual(self.manager.get_priority_value("high"), 1)
        self.assertEqual(self.manager.get_priority_value("medium"), 2)
        self.assertEqual(self.manager.get_priority_value("low"), 3)
        self.assertEqual(self.manager.get_priority_value("unknown"), 999)

    def test_get_priority_value_case_insensitive(self):
        """Test priority value conversion is case insensitive"""
        self.assertEqual(self.manager.get_priority_value("HIGH"), 1)
        self.assertEqual(self.manager.get_priority_value("Medium"), 2)
        self.assertEqual(self.manager.get_priority_value("LOW"), 3)

    def test_get_priority_value_numeric(self):
        """Test priority value conversion from numbers"""
        self.assertEqual(self.manager.get_priority_value(1), 1)
        self.assertEqual(self.manager.get_priority_value(5), 5)
        self.assertEqual(self.manager.get_priority_value(None), 999)

    # ==================== DURATION TESTS ====================

    def test_needs_breakdown_single_value(self):
        """Test duration breakdown check for single values"""
        self.assertFalse(self.manager.needs_breakdown("30"))
        self.assertFalse(self.manager.needs_breakdown("60"))
        self.assertTrue(self.manager.needs_breakdown("61"))
        self.assertTrue(self.manager.needs_breakdown("120"))

    def test_needs_breakdown_range(self):
        """Test duration breakdown check for ranges"""
        self.assertFalse(self.manager.needs_breakdown("30-60"))
        self.assertTrue(self.manager.needs_breakdown("50-90"))  # max > 60
        self.assertTrue(self.manager.needs_breakdown("70-100"))
        self.assertFalse(self.manager.needs_breakdown(None))

    def test_needs_breakdown_numeric(self):
        """Test duration breakdown check for numeric values"""
        self.assertFalse(self.manager.needs_breakdown(30))
        self.assertTrue(self.manager.needs_breakdown(90))

    # ==================== LEAF PHASE TESTS ====================

    def test_is_leaf_phase_no_children(self):
        """Test leaf phase detection for phases without children"""
        file_path = self.create_test_file("1.json", {"id": "1"})
        all_files = [file_path]

        result = self.manager.is_leaf_phase(file_path, all_files)
        self.assertTrue(result)

    def test_is_leaf_phase_with_children(self):
        """Test leaf phase detection for phases with children"""
        parent_file = self.create_test_file("1.json", {"id": "1"})
        child_file = self.create_test_file("1.1.json", {"id": "1.1"})
        all_files = [parent_file, child_file]

        result = self.manager.is_leaf_phase(parent_file, all_files)
        self.assertFalse(result)

    def test_is_leaf_phase_child_is_leaf(self):
        """Test leaf phase detection for child phases"""
        parent_file = self.create_test_file("1.json", {"id": "1"})
        child_file = self.create_test_file("1.1.json", {"id": "1.1"})
        all_files = [parent_file, child_file]

        result = self.manager.is_leaf_phase(child_file, all_files)
        self.assertTrue(result)

    # ==================== STATUS TESTS ====================

    def test_get_phase_status_individual_file(self):
        """Test getting phase status from individual file"""
        self.create_test_file("1.json", {"id": "1", "status": "completed"})

        status = self.manager.get_phase_status("1")
        self.assertEqual(status, "completed")

    def test_get_phase_status_individual_file_default(self):
        """Test getting phase status with default value"""
        self.create_test_file("1.json", {"id": "1"})

        status = self.manager.get_phase_status("1")
        self.assertEqual(status, "pending")

    def test_get_phase_status_phases_json(self):
        """Test getting phase status from phases.json"""
        phases_data = {
            "phases": [
                {"id": "1", "title": "Phase 1", "status": "in-progress"},
                {"id": "2", "title": "Phase 2", "status": "completed"}
            ]
        }
        self.create_test_file("phases.json", phases_data)

        status = self.manager.get_phase_status("1")
        self.assertEqual(status, "in-progress")

    def test_get_phase_status_unknown(self):
        """Test getting status for unknown phase"""
        status = self.manager.get_phase_status("999")
        self.assertEqual(status, "unknown")

    def test_are_dependencies_completed_empty(self):
        """Test dependency check with empty dependencies"""
        result = self.manager.are_dependencies_completed([])
        self.assertTrue(result)

    def test_are_dependencies_completed_none(self):
        """Test dependency check with None dependencies"""
        result = self.manager.are_dependencies_completed(None)
        self.assertTrue(result)

    def test_are_dependencies_completed_all_completed(self):
        """Test dependency check with all completed dependencies"""
        self.create_test_file("1.json", {"id": "1", "status": "completed"})
        self.create_test_file("2.json", {"id": "2", "status": "completed"})

        result = self.manager.are_dependencies_completed(["1", "2"])
        self.assertTrue(result)

    def test_are_dependencies_completed_some_pending(self):
        """Test dependency check with some pending dependencies"""
        self.create_test_file("1.json", {"id": "1", "status": "completed"})
        self.create_test_file("2.json", {"id": "2", "status": "pending"})

        result = self.manager.are_dependencies_completed(["1", "2"])
        self.assertFalse(result)

    def test_are_dependencies_completed_unknown(self):
        """Test dependency check with unknown dependencies"""
        result = self.manager.are_dependencies_completed(["999"])
        self.assertFalse(result)

    # ==================== TRUE LEAF PHASE TESTS ====================

    def test_is_true_leaf_phase_no_file(self):
        """Test true leaf phase detection when file doesn't exist"""
        sub_phase = {"id": "1.1", "title": "Sub Phase 1.1"}

        result = self.manager.is_true_leaf_phase(sub_phase)
        self.assertTrue(result)

    def test_is_true_leaf_phase_with_file_no_subphases(self):
        """Test true leaf phase detection with file that has no sub-phases"""
        self.create_test_file("1.1.json", {"id": "1.1", "title": "Sub Phase 1.1"})
        sub_phase = {"id": "1.1", "title": "Sub Phase 1.1"}

        result = self.manager.is_true_leaf_phase(sub_phase)
        self.assertTrue(result)

    def test_is_true_leaf_phase_with_file_has_subphases(self):
        """Test true leaf phase detection with file that has sub-phases"""
        self.create_test_file("1.1.json", {
            "id": "1.1",
            "title": "Sub Phase 1.1",
            "phases": [{"id": "1.1.1", "title": "Sub Sub Phase"}]
        })
        sub_phase = {"id": "1.1", "title": "Sub Phase 1.1"}

        result = self.manager.is_true_leaf_phase(sub_phase)
        self.assertFalse(result)

    # ==================== LEAF TASKS TESTS ====================

    def test_get_all_leaf_tasks_empty(self):
        """Test getting all leaf tasks from empty directory"""
        tasks = self.manager.get_all_leaf_tasks()
        self.assertEqual(tasks, [])

    def test_get_all_leaf_tasks_with_phases_json(self):
        """Test getting leaf tasks from phases.json"""
        phases_data = {
            "phases": [
                {
                    "id": "1",
                    "title": "Phase 1",
                    "status": "pending",
                    "priority": "high",
                    "description": "Test phase 1",
                    "duration": "30",
                    "dependencies": [],
                    "deliverables": ["deliverable1"]
                },
                {
                    "id": "2",
                    "title": "Phase 2",
                    "status": "completed",
                    "priority": "medium"
                }
            ]
        }
        self.create_test_file("phases.json", phases_data)

        tasks = self.manager.get_all_leaf_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['id'], "1")
        self.assertEqual(tasks[0]['title'], "Phase 1")
        self.assertEqual(tasks[0]['priority'], 1)  # high = 1

    def test_get_all_leaf_tasks_with_individual_files(self):
        """Test getting leaf tasks from individual files"""
        # Create a phase with sub-phases
        phase_data = {
            "id": "1",
            "title": "Phase 1",
            "status": "pending",
            "phases": [
                {
                    "id": "1.1",
                    "title": "Sub Phase 1.1",
                    "status": "pending",
                    "priority": "high",
                    "description": "Test sub phase",
                    "duration": "45",
                    "dependencies": [],
                    "deliverables": ["sub-deliverable"]
                },
                {
                    "id": "1.2",
                    "title": "Sub Phase 1.2",
                    "status": "completed",
                    "priority": "low"
                }
            ]
        }
        self.create_test_file("1.json", phase_data)

        tasks = self.manager.get_all_leaf_tasks()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['id'], "1.1")
        self.assertEqual(tasks[0]['parent_id'], "1")

    def test_get_all_leaf_tasks_with_dependencies(self):
        """Test getting leaf tasks with dependency filtering"""
        phases_data = {
            "phases": [
                {
                    "id": "1",
                    "title": "Phase 1",
                    "status": "pending",
                    "dependencies": []
                },
                {
                    "id": "2",
                    "title": "Phase 2",
                    "status": "pending",
                    "dependencies": ["1"]  # Depends on phase 1
                }
            ]
        }
        self.create_test_file("phases.json", phases_data)

        # Create phase 1 as completed
        self.create_test_file("1.json", {"id": "1", "status": "completed"})

        tasks = self.manager.get_all_leaf_tasks()
        self.assertEqual(len(tasks), 2)  # Both should be available now

    def test_get_all_leaf_tasks_sorting(self):
        """Test that leaf tasks are sorted by priority then ID"""
        phases_data = {
            "phases": [
                {
                    "id": "2",
                    "title": "Phase 2",
                    "status": "pending",
                    "priority": "high"
                },
                {
                    "id": "1",
                    "title": "Phase 1",
                    "status": "pending",
                    "priority": "low"
                },
                {
                    "id": "3",
                    "title": "Phase 3",
                    "status": "pending",
                    "priority": "high"
                }
            ]
        }
        self.create_test_file("phases.json", phases_data)

        tasks = self.manager.get_all_leaf_tasks()
        self.assertEqual(len(tasks), 3)
        # Should be sorted by priority (high=1, low=3) then by ID
        self.assertEqual(tasks[0]['id'], "2")  # high priority, lower ID
        self.assertEqual(tasks[1]['id'], "3")  # high priority, higher ID
        self.assertEqual(tasks[2]['id'], "1")  # low priority

    def test_get_leaf_tasks_for_phase_specific(self):
        """Test getting leaf tasks for specific phase"""
        # Create two different phases
        phase1_data = {
            "id": "1",
            "title": "Phase 1",
            "status": "pending",
            "phases": [
                {
                    "id": "1.1",
                    "title": "Sub Phase 1.1",
                    "status": "pending",
                    "priority": "high"
                }
            ]
        }
        phase2_data = {
            "id": "2",
            "title": "Phase 2",
            "status": "pending",
            "phases": [
                {
                    "id": "2.1",
                    "title": "Sub Phase 2.1",
                    "status": "pending",
                    "priority": "medium"
                }
            ]
        }
        self.create_test_file("1.json", phase1_data)
        self.create_test_file("2.json", phase2_data)

        # Get tasks for phase 1 only
        tasks = self.manager.get_leaf_tasks_for_phase("1")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['id'], "1.1")
        self.assertEqual(tasks[0]['parent_id'], "1")

    def test_get_leaf_tasks_for_phase_from_phases_json(self):
        """Test getting leaf tasks for specific phase from phases.json"""
        phases_data = {
            "phases": [
                {
                    "id": "1",
                    "title": "Phase 1",
                    "status": "pending",
                    "priority": "high"
                },
                {
                    "id": "2",
                    "title": "Phase 2",
                    "status": "completed",
                    "priority": "medium"
                }
            ]
        }
        self.create_test_file("phases.json", phases_data)

        tasks = self.manager.get_leaf_tasks_for_phase("1")
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['id'], "1")

    # ==================== STATUS UPDATE TESTS ====================

    def test_update_status_individual_file(self):
        """Test updating status in individual file"""
        self.create_test_file("1.json", {"id": "1", "status": "pending"})

        result = self.manager.update_status("1", "completed")
        self.assertTrue(result)

        # Verify the update
        updated_data = self.manager.load_json(os.path.join(self.plan_dir, "1.json"))
        self.assertEqual(updated_data['status'], "completed")

    def test_update_status_with_subphases(self):
        """Test updating status with sub-phases cascading"""
        phase_data = {
            "id": "1",
            "status": "pending",
            "phases": [
                {"id": "1.1", "status": "pending"},
                {"id": "1.2", "status": "pending"}
            ]
        }
        self.create_test_file("1.json", phase_data)

        result = self.manager.update_status("1", "completed")
        self.assertTrue(result)

        # Verify all statuses were updated
        updated_data = self.manager.load_json(os.path.join(self.plan_dir, "1.json"))
        self.assertEqual(updated_data['status'], "completed")
        self.assertEqual(updated_data['phases'][0]['status'], "completed")
        self.assertEqual(updated_data['phases'][1]['status'], "completed")

    def test_update_status_phases_json(self):
        """Test updating status in phases.json"""
        phases_data = {
            "phases": [
                {"id": "1", "title": "Phase 1", "status": "pending"},
                {"id": "2", "title": "Phase 2", "status": "pending"}
            ]
        }
        self.create_test_file("phases.json", phases_data)

        result = self.manager.update_status("1", "in-progress")
        self.assertTrue(result)

        # Verify the update
        updated_data = self.manager.load_json(os.path.join(self.plan_dir, "phases.json"))
        self.assertEqual(updated_data['phases'][0]['status'], "in-progress")
        self.assertEqual(updated_data['phases'][1]['status'], "pending")  # unchanged

    def test_update_status_invalid_status(self):
        """Test updating with invalid status"""
        self.create_test_file("1.json", {"id": "1", "status": "pending"})

        result = self.manager.update_status("1", "invalid")
        self.assertFalse(result)

    def test_update_status_nonexistent_phase(self):
        """Test updating non-existent phase"""
        result = self.manager.update_status("999", "completed")
        self.assertFalse(result)

    # ==================== AUTO-UPDATE PARENT TESTS ====================

    def test_update_parent_status_if_all_children_completed_no_parent(self):
        """Test auto-update when phase has no parent"""
        result = self.manager.update_parent_status_if_all_children_completed("1")
        self.assertTrue(result)

    def test_update_parent_status_if_all_children_completed_parent_nonexistent(self):
        """Test auto-update when parent file doesn't exist"""
        result = self.manager.update_parent_status_if_all_children_completed("1.1")
        self.assertTrue(result)

    def test_update_parent_status_if_all_children_completed_some_children_pending(self):
        """Test auto-update when not all children are completed"""
        parent_data = {
            "id": "1",
            "status": "pending",
            "phases": [
                {"id": "1.1", "status": "completed"},
                {"id": "1.2", "status": "pending"}
            ]
        }
        self.create_test_file("1.json", parent_data)

        result = self.manager.update_parent_status_if_all_children_completed("1.1")
        self.assertTrue(result)

        # Parent should still be pending
        updated_data = self.manager.load_json(os.path.join(self.plan_dir, "1.json"))
        self.assertEqual(updated_data['status'], "pending")

    def test_update_parent_status_if_all_children_completed_all_children_completed(self):
        """Test auto-update when all children are completed"""
        parent_data = {
            "id": "1",
            "status": "pending",
            "phases": [
                {"id": "1.1", "status": "completed"},
                {"id": "1.2", "status": "completed"}
            ]
        }
        self.create_test_file("1.json", parent_data)

        result = self.manager.update_parent_status_if_all_children_completed("1.1")
        self.assertTrue(result)

        # Parent should be auto-updated to completed
        updated_data = self.manager.load_json(os.path.join(self.plan_dir, "1.json"))
        self.assertEqual(updated_data['status'], "completed")

    # ==================== FIND LEAF PHASES TESTS ====================

    def test_find_leaf_phases_empty(self):
        """Test finding leaf phases in empty directory"""
        phases = self.manager.find_leaf_phases()
        self.assertEqual(phases, [])

    def test_find_leaf_phases_with_duration_over_60(self):
        """Test finding leaf phases with duration over 60 minutes"""
        phase_data = {
            "id": "1",
            "title": "Phase 1",
            "phases": [
                {
                    "id": "1.1",
                    "title": "Long Phase",
                    "duration": "120",  # > 60 minutes
                    "status": "pending"
                },
                {
                    "id": "1.2",
                    "title": "Short Phase",
                    "duration": "30",  # <= 60 minutes
                    "status": "pending"
                }
            ]
        }
        self.create_test_file("1.json", phase_data)

        phases = self.manager.find_leaf_phases()
        self.assertEqual(len(phases), 1)
        self.assertEqual(phases[0]['phase_id'], "1.1")
        self.assertEqual(phases[0]['duration'], "120")

    def test_find_leaf_phases_with_range_duration(self):
        """Test finding leaf phases with range duration"""
        phase_data = {
            "id": "1",
            "title": "Phase 1",
            "phases": [
                {
                    "id": "1.1",
                    "title": "Range Phase",
                    "duration": "50-90",  # max > 60
                    "status": "pending"
                }
            ]
        }
        self.create_test_file("1.json", phase_data)

        phases = self.manager.find_leaf_phases()
        self.assertEqual(len(phases), 1)
        self.assertEqual(phases[0]['phase_id'], "1.1")

    def test_find_leaf_phases_limit(self):
        """Test finding leaf phases with limit"""
        # Create multiple phases
        for i in range(1, 6):
            phase_data = {
                "id": str(i),
                "title": f"Phase {i}",
                "phases": [
                    {
                        "id": f"{i}.1",
                        "title": f"Long Phase {i}",
                        "duration": "120",
                        "status": "pending"
                    }
                ]
            }
            self.create_test_file(f"{i}.json", phase_data)

        phases = self.manager.find_leaf_phases(limit=3)
        self.assertEqual(len(phases), 3)

    # ==================== DISPLAY FORMAT TESTS ====================

    def test_format_tasks_empty(self):
        """Test formatting empty task list"""
        result = self.manager.format_tasks([])
        self.assertEqual(result, "No leaf tasks available.")

    def test_format_tasks_with_tasks(self):
        """Test formatting task list"""
        tasks = [
            {
                "id": "1.1",
                "title": "Test Task 1",
                "priority": 1,
                "parent_id": "1",
                "duration": "45",
                "dependencies": ["1"],
                "description": "Test description"
            },
            {
                "id": "2.1",
                "title": "Test Task 2",
                "priority": 2,
                "parent_id": "2",
                "duration": None,
                "dependencies": [],
                "description": "Another test"
            }
        ]

        result = self.manager.format_tasks(tasks, limit=10)

        self.assertIn("1. [1.1] Test Task 1", result)
        self.assertIn("Priority: 1 | Parent: 1", result)
        self.assertIn("Duration: 45", result)
        self.assertIn("Dependencies: 1", result)
        self.assertIn("2. [2.1] Test Task 2", result)
        self.assertIn("Priority: 2 | Parent: 2", result)

    def test_format_tasks_with_limit(self):
        """Test formatting tasks with limit"""
        tasks = [
            {"id": "1", "title": "Task 1", "priority": 1},
            {"id": "2", "title": "Task 2", "priority": 2},
            {"id": "3", "title": "Task 3", "priority": 3}
        ]

        result = self.manager.format_tasks(tasks, limit=2)

        self.assertIn("1. [1] Task 1", result)
        self.assertIn("2. [2] Task 2", result)
        self.assertNotIn("3. [3] Task 3", result)

    def test_format_leaf_phases_empty(self):
        """Test formatting empty leaf phases list"""
        result = self.manager.format_leaf_phases([])
        self.assertEqual(result, "SUCCESS: No leaf phases with duration >60 minutes!")

    def test_format_leaf_phases_with_phases(self):
        """Test formatting leaf phases list"""
        phases = [
            {
                "file": "1.json",
                "phase_id": "1.1",
                "title": "Long Phase 1",
                "duration": "120",
                "status": "pending"
            },
            {
                "file": "1.json",
                "phase_id": "1.2",
                "title": "Long Phase 2",
                "duration": "90",
                "status": "completed"
            },
            {
                "file": "2.json",
                "phase_id": "2.1",
                "title": "Long Phase 3",
                "duration": "180",
                "status": "in-progress"
            }
        ]

        result = self.manager.format_leaf_phases(phases)

        self.assertIn("FOUND: 3 leaf phases with duration >60 minutes", result)
        self.assertIn("File: 1.json", result)
        self.assertIn("- Phase 1.1: Long Phase 1", result)
        self.assertIn("Duration: 120 minutes", result)
        self.assertIn("Status: pending", result)
        self.assertIn("File: 2.json", result)

    # ==================== LIST PHASES TESTS ====================

    @patch('builtins.print')
    def test_list_phases_empty_directory(self, mock_print):
        """Test listing phases in empty directory"""
        self.manager.list_phases()

        # Should print header and no phases
        mock_print.assert_any_call("\n=== All Phase Status ===\n")
        mock_print.assert_any_call("Detailed Phase Files:")

    @patch('builtins.print')
    def test_list_phases_with_phases_json(self, mock_print):
        """Test listing phases with phases.json"""
        phases_data = {
            "phases": [
                {"id": "1", "title": "Phase 1", "status": "pending"},
                {"id": "2", "title": "Phase 2", "status": "completed"}
            ]
        }
        self.create_test_file("phases.json", phases_data)

        self.manager.list_phases()

        mock_print.assert_any_call("Main Phases:")
        mock_print.assert_any_call("  Phase 1: Phase 1 [pending]")
        mock_print.assert_any_call("  Phase 2: Phase 2 [completed]")

    @patch('builtins.print')
    def test_list_phases_with_individual_files(self, mock_print):
        """Test listing phases with individual files"""
        self.create_test_file("1.json", {"id": "1", "title": "Phase 1", "status": "pending"})
        self.create_test_file("1.1.json", {"id": "1.1", "title": "Sub Phase 1.1", "status": "completed"})

        self.manager.list_phases()

        mock_print.assert_any_call("  1: Phase 1 [pending]")
        mock_print.assert_any_call("  └─ 1.1: Sub Phase 1.1 [completed]")

    # ==================== UPDATE ALL STATUS TESTS ====================

    def test_update_all_status_with_phases_json(self):
        """Test updating all statuses with phases.json"""
        phases_data = {
            "phases": [
                {"id": "1", "title": "Phase 1", "status": "pending"},
                {"id": "2", "title": "Phase 2", "status": "completed"}
            ]
        }
        self.create_test_file("phases.json", phases_data)

        count = self.manager.update_all_status("in-progress")

        self.assertEqual(count, 1)  # Only phases.json should be updated
        updated_data = self.manager.load_json(os.path.join(self.plan_dir, "phases.json"))
        self.assertEqual(updated_data['phases'][0]['status'], "in-progress")
        self.assertEqual(updated_data['phases'][1]['status'], "in-progress")

    def test_update_all_status_with_individual_files(self):
        """Test updating all statuses with individual files"""
        self.create_test_file("1.json", {"id": "1", "status": "pending"})
        self.create_test_file("2.json", {"id": "2", "status": "completed"})

        count = self.manager.update_all_status("completed")

        self.assertEqual(count, 2)  # Both files should be updated
        updated_data1 = self.manager.load_json(os.path.join(self.plan_dir, "1.json"))
        updated_data2 = self.manager.load_json(os.path.join(self.plan_dir, "2.json"))
        self.assertEqual(updated_data1['status'], "completed")
        self.assertEqual(updated_data2['status'], "completed")


if __name__ == '__main__':
    unittest.main()