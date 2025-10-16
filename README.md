# Claude CLI Tools - Project Management System

A comprehensive command-line tool for project initialization, phase breakdown, and task execution with AI-powered automation.

## Overview

Claude CLI Tools provides three main commands for managing your software development projects:

- **`gass init`** - Initialize new projects with comprehensive planning
- **`gass break`** - Break down large phases into manageable sub-phases
- **`gass run`** - Execute tasks with parallel processing and validation

## Installation

Make sure you have Python 3.7+ installed, then install the package:

```bash
pip install -e .
```

## Quick Start

### 1. Initialize a New Project

Start by creating a comprehensive project plan:

```bash
gass init @requirements.md myproject
```

This will:
- Analyze your PRD/requirements document
- Generate development phases with dependencies
- Create database schema design
- Generate project structure organization
- Save all outputs to `.ai/` directory

**Parameters:**
- `@requirements.md` - Path to your PRD/requirements file (supports @ notation)
- `myproject` - Target folder name for your project (optional)

**Example outputs:**
```
.ai/
├── plan/
│   ├── index.json          # Project overview
│   └── phases.json         # Detailed development phases
├── schema/
│   └── index.json          # Database schema overview
└── structure/
    └── structure.md        # Directory structure plan
```

### 2. Break Down Large Phases

If any phase duration exceeds 60 minutes, break it down:

```bash
gass break --workers 2 --max-iterations 50
```

This will:
- Find phases with duration > 60 minutes
- Automatically break them into smaller sub-phases
- Maintain dependencies and critical paths
- Generate breakdown files for each large phase

**Parameters:**
- `--workers N` - Number of parallel workers (default: 1)
- `--max-iterations N` - Maximum iterations to prevent infinite loops (default: 50)

### 3. Execute Tasks

Run available tasks in parallel with validation:

```bash
gass run --max-tasks 3
```

This will:
- Find available tasks that can be worked on
- Execute tasks in parallel using Claude AI
- Validate implementation quality
- Update task status automatically
- Generate validation reports and logs

**Parameters:**
- `--max-tasks N` - Maximum concurrent tasks (default: 5)

## Detailed Usage

### gass init - Project Initialization

The `init` command creates a comprehensive foundation for your project:

**Usage:**
```bash
gass init [plan-path] [target-folder]
```

**Features:**
- **Plan Analysis**: Analyzes PRD and creates structured development phases
- **Database Design**: Generates phase-aware database schema
- **Project Structure**: Creates organized directory structure
- **Dependency Mapping**: Maps phase dependencies and critical paths

**Examples:**
```bash
# Initialize with requirements file
gass init @requirements.txt webapp

# Initialize with markdown specification
gass init @project_spec.rbac

# Initialize without target folder
gass init @features.md
```

**What gets created:**
- Development phases with timelines and dependencies
- Database schema with tables and relationships
- Project directory structure with modules
- All files saved in `.ai/` directory for AI consumption

### gass break - Phase Breakdown

The `break` command handles automated phase decomposition:

**Usage:**
```bash
gass break [options]
```

**Features:**
- **Automatic Detection**: Finds phases exceeding 60-minute threshold
- **Intelligent Breakdown**: Creates logical sub-phases with dependencies
- **Dependency Preservation**: Maintains original phase relationships
- **Progress Monitoring**: Real-time worker activity display

**Examples:**
```bash
# Basic breakdown with single worker
gass break

# Breakdown with multiple workers for faster processing
gass break --workers 3

# Limited number of iterations
gass break --max-iterations 20
```

**Output:**
- Each large phase gets its own breakdown file
- Sub-phases maintain original dependencies
- Critical paths are preserved
- Breakdown complete flag when finished

### gass run - Task Execution

The `run` command executes available tasks with comprehensive validation:

**Usage:**
```bash
gass run [options]
```

**Workflow:**
1. **Task Analysis**: Identifies workable tasks using PhaseManager
2. **Parallel Execution**: Runs multiple tasks simultaneously
3. **Quality Validation**: Validates implementation with lint checking
4. **Status Management**: Updates task status based on results

**Examples:**
```bash
# Execute with default 5 concurrent tasks
gass run

# Execute with limited concurrency
gass run --max-tasks 2

# Execute single task at a time
gass run --max-tasks 1
```

**Validation Process:**
- Automatic lint checking and fixing
- File size validation (300 lines max)
- AI-friendly naming convention enforcement
- Scope compliance verification
- Integration compatibility checking

**Output:**
- Task context files (`.ai/brain/tasks/`)
- Validation reports (`.ai/brain/validation/`)
- Status logs (`.ai/brain/status/`)

## File Structure

After using the tools, your project will have this structure:

```
project/
├── .ai/
│   ├── plan/
│   │   ├── index.json          # Project overview
│   │   ├── phases.json         # Development phases
│   │   └── [phase-id].json     # Individual phase files
│   ├── schema/
│   │   ├── index.json          # Database overview
│   │   └── [table]/             # Table-specific schemas
│   ├── structure/
│   │   └── structure.md        # Directory structure
│   └── brain/
│       ├── tasks/              # Task context files
│       ├── validation/         # Validation reports
│       └── status/             # Status logs
└── [your-project-files/]
```

## Command Reference

### Common Options

All commands support these standard options:
- `--help` - Show detailed help information
- `--verbose` - Enable verbose logging (where applicable)

### gass init Options

```bash
gass init [plan-path] [target-folder]
```

**Arguments:**
- `plan-path` (required) - Path to PRD/requirements file
- `target-folder` (optional) - Target project folder name

### gass break Options

```bash
gass break [--workers N] [--max-iterations N]
```

**Options:**
- `--workers N` - Number of parallel workers (default: 1)
- `--max-iterations N` - Maximum iterations (default: 50)

### gass run Options

```bash
gass run [--max-tasks N]
```

**Options:**
- `--max-tasks N` - Maximum concurrent tasks (default: 5)

## Best Practices

### 1. Project Initialization
- Start with clear, detailed requirements
- Include technical specifications and constraints
- Specify target technology stack if possible

### 2. Phase Management
- Review generated phases for accuracy
- Adjust durations based on team capacity
- Ensure dependencies are logical

### 3. Task Execution
- Start with smaller `--max-tasks` values for complex projects
- Monitor validation reports for quality issues
- Review status logs for progress tracking

### 4. Iterative Development
- Use `gass break` when phases become too large
- Re-run `gass run` as tasks complete
- Update requirements and regenerate as needed

## Troubleshooting

### Common Issues

**"No available tasks to execute"**
- Check if phases have status "pending"
- Verify dependencies are completed
- Use `gass break` if phases are too large

**"Claude execution failed"**
- Check internet connection
- Verify Claude CLI installation
- Review prompt files for formatting issues

**"Validation failed"**
- Review validation reports in `.ai/brain/validation/`
- Fix lint issues manually if needed
- Check file size limits (300 lines max)

### Getting Help

For command-specific help:
```bash
gass init --help
gass break --help
gass run --help
```

For general help:
```bash
gass --help
```

## Examples

### Complete Workflow Example

```bash
# 1. Initialize new RBAC project
gass init @rbac_requirements.md rbac

# 2. Break down large phases if needed
gass break --workers 2

# 3. Execute available tasks
gass run --max-tasks 3

# 4. Monitor progress and repeat as needed
gass run
```

### Web Application Example

```bash
# Initialize e-commerce project
gass init @ecommerce_spec.md shop

# Execute tasks with limited concurrency
gass run --max-tasks 2

# Break down large phases
gass break --workers 3

# Continue execution
gass run
```

## Contributing

This tool is part of the Claude CLI ecosystem. For issues and contributions:

1. Check existing issues in the repository
2. Follow the established code patterns
3. Test with various project types
4. Update documentation for new features

## License

This project is part of the Claude CLI Tools ecosystem.