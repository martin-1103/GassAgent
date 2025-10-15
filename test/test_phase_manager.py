#!/usr/bin/env python3
"""
PhaseManager Test - Find phases that need breakdown
"""

import unittest
import os
import sys

# Import PhaseManager
import importlib.util
spec = importlib.util.spec_from_file_location("phase_manager", os.path.join(os.path.dirname(__file__), "..", "class", "phase_manager.py"))
phase_manager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(phase_manager_module)
PhaseManager = phase_manager_module.PhaseManager


class TestPhaseBreakdown(unittest.TestCase):

    def setUp(self):
        self.plan_dir = os.path.join(os.path.dirname(__file__), "..", ".ai", "plan")
        self.manager = PhaseManager(self.plan_dir)

    def test_find_phases_need_breakdown(self):
        """Test find phases that need breakdown (>60 minutes)"""
        phases = self.manager.find_phases_needing_breakdown()

        print(f"\n=== PHASES THAT NEED BREAKDOWN ===")
        print(f"Found {len(phases)} phases:")

        for i, phase in enumerate(phases, 1):
            print(f"{i}. Phase {phase['phase_id']}: {phase['title']}")
            print(f"   Duration: {phase['duration']} minutes")
            print(f"   Status: {phase['status']}")
            print()

        self.assertIsInstance(phases, list)

    def test_change_phase_status(self):
        """Test change phase status"""
        print(f"\n=== CHANGE PHASE STATUS ===")

        # Test updating to 'completed'
        result = self.manager.update_status("1", "completed")
        print(f"Update result: {result}")

        # Verify status was changed
        status = self.manager.get_phase_status("1")
        print(f"New status: {status}")

        self.assertTrue(result)
        self.assertEqual(status, "completed")

    def test_get_workable_phases(self):
        """Test get workable phases"""
        print(f"\n=== GET WORKABLE PHASES ===")

        workable_phases = self.manager.get_workable_phases()
        print(f"Found {len(workable_phases)} workable phases:")

        for i, phase in enumerate(workable_phases[:3], 1):
            print(f"{i}. [{phase['id']}] {phase['title']}")
            print(f"   Status: {phase['status']}")
            print()

        self.assertIsInstance(workable_phases, list)


if __name__ == '__main__':
    unittest.main()