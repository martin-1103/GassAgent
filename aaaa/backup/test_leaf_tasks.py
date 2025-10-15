#!/usr/bin/env python3
"""
Test Leaf Task Finder
"""

from leaf_tasks import LeafTaskFinder

def test():
    """Test the LeafTaskFinder class"""
    print("Testing LeafTaskFinder...")

    # Create finder instance
    finder = LeafTaskFinder()

    # Test get all leaf tasks
    print("\n1. Testing get_all_leaf_tasks():")
    all_tasks = finder.get_all_leaf_tasks()
    print(f"Found {len(all_tasks)} leaf tasks")

    # Test format output
    if all_tasks:
        print("\nFirst 3 tasks:")
        print(finder.format_tasks(all_tasks, limit=3))

    # Test specific phase (if exists)
    if all_tasks:
        first_phase_id = all_tasks[0]['id']
        print(f"\n2. Testing get_leaf_tasks_for_phase('{first_phase_id}'):")
        phase_tasks = finder.get_leaf_tasks_for_phase(first_phase_id)
        print(f"Found {len(phase_tasks)} tasks for phase {first_phase_id}")
        if phase_tasks:
            print(finder.format_tasks(phase_tasks, limit=2))

if __name__ == "__main__":
    test()