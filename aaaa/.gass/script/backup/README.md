# Project Scripts

Kumpulan script CLI untuk mengelola project phases, tasks, dan menjalankan Claude Code dalam mode headless.

## Available Scripts

### 1. update-phase-status.js
Script untuk mengupdate status phases.

```bash
# Lihat status semua phase
node update-phase-status.js --list

# Update semua phase
node update-phase-status.js --status pending --all
node update-phase-status.js --status in-progress --all
node update-phase-status.js --status completed --all

# Update phase spesifik
node update-phase-status.js --status completed --phase 1
node update-phase-status.js --status in-progress --phase 1.1
```

### 2. get-leaf-tasks.js
Script untuk mendapatkan **true leaf tasks** yang bisa dikerjakan.

```bash
# Dapatkan semua true leaf tasks yang bisa dikerjakan
node get-leaf-tasks.js

# Filter leaf tasks dari phase spesifik
node get-leaf-tasks.js --phase 2
node get-leaf-tasks.js --phase 2.1
```

**True leaf tasks** adalah sub-phases terdalam yang:
- Tidak punya file terpisah ATAU punya file tapi tidak punya sub-phases lagi
- Status pending
- Dependencies sudah completed
- Bisa dikerjakan kapan saja (parent status otomatis mengikuti children)

### 3. get-dependent-tasks.js
Script untuk mendapatkan tasks yang dependencies nya sudah completed.

```bash
# Dapatkan semua tasks dengan dependencies completed
node get-dependent-tasks.js

# Filter tasks dari phase spesifik
node get-dependent-tasks.js --phase 2
node get-dependent-tasks.js --phase 3
```

### 4. check-phase-completion.js
Script untuk mengecek completion status dan percentage dari phases.

```bash
# Cek completion status phase spesifik
node check-phase-completion.js --phase 2

# Cek semua main phases
node check-phase-completion.js --all
```

### 5. get-ready-leaf-phases.js
Script untuk mendapatkan leaf phases yang ready untuk dikerjakan.

```bash
# Dapatkan semua leaf phases yang ready
node get-ready-leaf-phases.js

# Filter dari phase spesifik
node get-ready-leaf-phases.js --phase 2
```

## Headless Claude Code Scripts

### 6. headless-claude.js
Node.js script untuk menjalankan Claude Code dalam mode headless dengan fitur lengkap.

```bash
# Basic usage
node headless-claude.js

# Custom prompt
node headless-claude.js --custom "Buat README.md untuk project ini"

# Create custom file
node headless-claude.js --file todo.txt "Daftar belanja: mie, susu, telur"
```

**Features:**
- JSON output parsing
- Error handling
- Cost tracking
- Session management
- Custom options support

### 7. run_claude.bat
Simple batch file untuk menjalankan Claude Code tanpa instalasi Node.js.

```cmd
# Basic usage
run_claude.bat "Create file tmp/test.txt with hello world"

# Complex task
run_claude.bat "Buat dokumentasi API di docs/api.md"
```

**Features:**
- No Node.js required
- Auto project root detection
- Simple argument passing
- Windows Command Prompt ready

## Status Options

- `pending` - Phase belum dimulai
- `in-progress` - Phase sedang dikerjakan
- `completed` - Phase sudah selesai

## Priority System

- **Priority 1**: High priority tasks (dikerjakan pertama)
- **Priority 2**: Medium priority tasks
- **Priority 3**: Low priority tasks
- **Priority 999+**: Unspecified/lowest priority

## Script Features

### Update Script Features
- Update bulk untuk semua phase
- Update spesifik phase beserta sub-phases
- Auto recursive update
- Status validation
- File existence checking

### Task Scripts Features
- Priority-based sorting
- Dependency checking
- True leaf node detection
- Comprehensive filtering options
- Detailed task information display

### Completion Script Features
- Percentage calculation
- Hierarchical status checking
- Should-be status recommendations
- Comprehensive progress reporting

## File Structure

```
.ai/
├── script/
│   ├── update-phase-status.js      # Update phase status
│   ├── get-leaf-tasks.js            # Get true leaf tasks
│   ├── get-dependent-tasks.js       # Get tasks with completed dependencies
│   ├── check-phase-completion.js    # Check completion percentage
│   ├── get-ready-leaf-phases.js     # Get ready leaf phases
│   ├── headless-claude.js           # Node.js headless Claude runner
│   ├── run_claude.bat               # Simple batch file runner
│   ├── package.json                 # Node.js package config
│   └── README.md                    # This file
└── plan/
    ├── phases.json                 # Main phases configuration
    ├── 1.json, 2.json, ...         # Phase files
    ├── 1.1.json, 1.2.json, ...    # Sub-phase files
    └── ...
```

## Usage Examples

### Typical Workflow
```bash
# 1. Reset semua phases ke pending
node update-phase-status.js --status pending --all

# 2. Tandai Phase 1 sebagai completed
node update-phase-status.js --status completed --phase 1

# 3. Lihat tasks yang bisa dikerjakan
node get-leaf-tasks.js

# 4. Cek progress Phase 2
node check-phase-completion.js --phase 2
```

### Debugging Dependencies
```bash
# Lihat tasks yang dependencies nya sudah selesai
node get-dependent-tasks.js

# Cek completion semua phases
node check-phase-completion.js --all
```

## Headless Claude Usage

### Quick Start
```bash
# Simple file creation (Batch file - no Node.js needed)
.ai\script\run_claude.bat "Buat file tmp/hello.txt dengan isi Hello World"

# Advanced usage (Node.js required)
node .ai/script/headless-claude.js --custom "Generate project documentation"
```

### Automation Examples
```bash
# Create project structure
.ai\script\run_claude.bat "Buat struktur folder untuk React project: src/, components/, utils/, tests/"

# Generate configuration files
node .ai/script/headless-claude.js --file package.json 'React project with TypeScript, ESLint, Prettier'

# Create documentation
node .ai/script/headless-claude.js --custom "Buat README.md lengkap untuk project ini"
```

### Integration with CI/CD
```bash
# Automated testing setup
.ai\script\run_claude.bat "Setup Jest testing configuration dan test files untuk semua components"

# Documentation generation
node .ai/script/headless-claude.js --custom "Generate API documentation dari semua route files"
```

## Choosing the Right Script

### Use run_claude.bat when:
- You don't have Node.js installed
- Need simple, quick tasks
- Working on Windows Command Prompt
- Want minimal setup

### Use headless-claude.js when:
- Need advanced features
- Want JSON output parsing
- Need error handling and logging
- Working with complex automation
- Need session management