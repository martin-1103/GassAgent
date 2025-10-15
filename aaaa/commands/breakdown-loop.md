---
allowed-tools: Read, Write, Task, Bash
description: Looping breakdown analyzer menggunakan find-leaf-phases.js
argument-hint: [reset]
---

$ARGUMENTS

## Task

Automated breakdown analyzer yang menggunakan `find-leaf-phases.js` script untuk:

1. **Run script** `.gass/script/find-leaf-phases.js` untuk scan semua leaf phases >60 menit
2. **Process results** - script akan menampilkan semua leaf phases yang perlu breakdown
3. **Call agent** plan-breakdown-analyzer untuk setiap phase yang ditemukan
4. **Update log** dengan hasil breakdown
5. **Loop** sampai semua phases selesai

## Flow

If "$ARGUMENTS" = "reset":
- Clear breakdown log
- Start fresh scan

Else:
1. **Run find-leaf-phases.js** untuk mendapatkan daftar leaf phases >60 menit
2. **Process each phase** yang ditemukan script:
   - Call plan-breakdown-analyzer agent
   - Update log dengan hasil
3. **Repeat** scan sampai tidak ada lagi leaf phases >60 menit

## Script Output Analysis

The `find-leaf-phases.js` script akan menampilkan:
- ✅ Jika tidak ada leaf phases >60 menit: "Tidak ada leaf phase dengan durasi >60 menit!"
- ⚠️ Jika ada phases >60 menit: Daftar lengkap dengan:
  - File name (contoh: 1.2.3.json)
  - Phase ID dan title
  - Duration dalam menit
  - Status breakdown
  - Check results: "Phase X: 960-1440 minutes → ✅ needs breakdown"

## Processing Logic

Untuk setiap leaf phase yang ditemukan:

```javascript
// Script output format:
// ⚠️ Ditemukan 3 leaf phases dengan durasi >60 menit:
// 📄 File: 1.2.3.json
//    - Phase 1: Backend Development
//      Duration: 960-1440 minutes
//      Status: pending
//      Phase 1: 960-1440 minutes → ✅ needs breakdown
```

1. **Parse script output** untuk extract phase info
2. **Call plan-breakdown-analyzer** dengan:
   - File path
   - Phase ID
   - Phase details
3. **Update breakdown log** dengan results
4. **Continue to next phase**

## Completion Criteria

Process selesai saat:
- Script return: ✅ "Tidak ada leaf phase dengan durasi >60 menit!"
- Semua leaf phases sudah <60 menit
- Breakdown log menunjukkan status "Completed"

## Error Handling

- Jika script error → log dan stop
- Jika agent error → log dan continue ke phase berikutnya
- Jika parsing error → log manual intervention needed

## Output Format

Show real-time:
- Script execution results
- Phase being processed
- Agent call status
- Log updates
- Progress: "Processing X/Y phases"
- Final status: "Completed" or "Error"

## Benefits

✅ **Simplified logic** - Delegating scanning to specialized script
✅ **Consistent duration checking** - Using tested needsBreakdown() function
✅ **Leaf phase detection** - Automatic identification of phases without children
✅ **Error reduction** - Less manual parsing and validation
✅ **Maintainability** - Centralized logic in find-leaf-phases.js