Initialize project dengan comprehensive planning, database schema dan structure generation.

## Usage:
```bash
/init [plan-path] [target-folder]
```

## Parameters:
- `plan-path`: Path ke PRD/plan file (required)
- `target-folder`: Nama target folder untuk project (required)

## What it does:
1. **Run plan-analyzer agent** untuk analyze requirements dan generate development phases
2. **Spawn PARALLEL agents** dengan plan analysis context:
   - database-schema-designer agent untuk generate phase-aware database schema
   - project-structure-generator agent untuk generate phase-aware project structure


## Examples:
```bash
/init @sample_prd.md rbac
/init @docs/plan.txt my-project
/init requirements.md webapp
```

## Notes:
- Generate comprehensive ANALYSIS dan PLANNING documents
- Tidak create actual project files
- Output disimpan sesuai agent definition:
  - `plan-analyzer` → `.ai/plan/` (development phases dan roadmap)
  - `database-schema-designer` → `.ai/schema/` (phase-aware database schema)
  - `project-structure-generator` → `.ai/structure/structure.md` (phase-aware directory structure)
- **Plan analyzer runs FIRST** untuk generate development context
- Database dan structure agents dijalankan secara PARALLEL dengan plan analysis context
- **Target-folder parameter diteruskan ke agents:**
  - `plan-analyzer` menerima PRD content untuk generate development phases
  - `database-schema-designer` menerima plan analysis context untuk generate phase-aware schema
  - `project-structure-generator` menerima plan analysis context + target-folder untuk generate phase-aware structure