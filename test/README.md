# Test Suite for PhaseManager

This directory contains comprehensive tests for the PhaseManager class.

## Files

- `test_phase_manager.py` - Complete test suite with 50+ test cases covering all PhaseManager functionality

## Running Tests

To run all tests:
```bash
python -m unittest test.test_phase_manager
```

To run tests from the test directory:
```bash
cd test
python test_phase_manager.py
```

To run specific test methods:
```bash
python -m unittest test.test_phase_manager.TestPhaseManager.test_load_json_valid_file
```

## Test Coverage

The test suite covers:

### Core Functionality
- JSON file loading and saving
- Phase directory management
- Priority and duration handling
- Leaf phase detection

### Status Management
- Phase status retrieval and updates
- Dependency checking
- Parent status auto-updates
- Status cascading to sub-phases

### Task Management
- Leaf task identification
- Task filtering and sorting
- Phase-specific task retrieval

### CLI Integration
- All CLI commands tested through class methods
- Display formatting
- Error handling

### Edge Cases
- Invalid JSON files
- Missing files and directories
- Invalid status values
- Empty data sets
- Permission errors

## Test Structure

Tests use the standard Python `unittest` framework with:
- `setUp()` and `tearDown()` for test isolation
- Temporary directories for file operations
- Mock objects for testing console output
- Helper methods for creating test data

Each test method focuses on a specific functionality and includes both positive and negative test cases.