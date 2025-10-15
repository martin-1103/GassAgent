#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

/**
 * Script untuk mencari leaf phases yang durasinya >60 menit
 * Leaf phase = phase yang tidak memiliki sub-phases (tidak ada file child)
 */

function needsBreakdown(duration) {
  // Duration sekarang dalam format numerik menit
  // Handle range formats: "960-1440" atau single values: "960"

  if (!duration) return false;

  const durationStr = duration.toString();

  if (durationStr.includes('-')) {
    // Range format: "960-1440"
    const [min, max] = durationStr.split('-');
    const minMinutes = parseInt(min.trim());
    const maxMinutes = parseInt(max.trim());
    return minMinutes > 60 || maxMinutes > 60;
  } else {
    // Single value: "960"
    const minutes = parseInt(durationStr);
    return minutes > 60;
  }
}

function logDurationCheck(phaseId, duration) {
  const needsBreak = needsBreakdown(duration);
  console.log(`Phase ${phaseId}: ${duration} minutes → ${needsBreak ? '✅ needs breakdown' : '❌ no breakdown'}`);
  return needsBreak;
}

function getAllPlanFiles(planDir) {
  const files = [];

  function scanDirectory(dir) {
    const items = fs.readdirSync(dir);

    for (const item of items) {
      const fullPath = path.join(dir, item);
      const stat = fs.statSync(fullPath);

      if (stat.isDirectory()) {
        scanDirectory(fullPath);
      } else if (item.endsWith('.json') && item !== 'index.json') {
        files.push(fullPath);
      }
    }
  }

  scanDirectory(planDir);
  return files;
}

function isLeafPhase(filePath, allFiles) {
  const fileName = path.basename(filePath, '.json');

  // Cek apakah ada file child untuk phase ini
  // Contoh: jika file adalah "1.2.json", cek apakah ada "1.2.1.json", "1.2.2.json", etc.
  const childPattern = new RegExp(`^${fileName.replace(/\./g, '\\.')}\\.\\d+\\.json$`);

  return !allFiles.some(file => {
    const baseName = path.basename(file);
    return childPattern.test(baseName);
  });
}

function parsePhaseData(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    const data = JSON.parse(content);

    const phases = [];

    if (data.phases && Array.isArray(data.phases)) {
      data.phases.forEach(phase => {
        phases.push({
          id: phase.id || 'undefined',
          title: phase.title || 'No title',
          duration: phase.duration || '0',
          status: phase.status || 'pending'
        });
      });
    }

    return {
      filePath,
      fileName: path.basename(filePath),
      phases,
      breakdownComplete: data.breakdown_complete || false
    };
  } catch (error) {
    console.error(`Error parsing ${filePath}:`, error.message);
    return null;
  }
}

function main() {
  const planDir = path.join(__dirname, '..', 'plan');

  console.log('🔍 Scanning untuk leaf phases dengan durasi >60 menit...\n');

  // Get all plan files (exclude phases.json)
  const allFiles = getAllPlanFiles(planDir).filter(file =>
    !file.endsWith('phases.json')
  );
  console.log(`📁 Total files ditemukan: ${allFiles.length}`);

  const leafPhases = [];
  const processedFiles = [];

  for (const filePath of allFiles) {
    const isLeaf = isLeafPhase(filePath, allFiles);

    if (isLeaf) {
      const phaseData = parsePhaseData(filePath);

      if (phaseData && phaseData.phases.length > 0) {
        processedFiles.push(phaseData);

        // Cek setiap phase dalam array [phases]
        for (const phase of phaseData.phases) {
          if (phase.duration && needsBreakdown(phase.duration)) {
            leafPhases.push({
              file: phaseData.fileName,
              phaseId: phase.id || 'No ID',
              title: phase.title,
              duration: phase.duration,
              status: phase.status || 'pending'
            });
          }
        }
      }
    }
  }

  // Filter untuk hanya menampilkan 20 teratas untuk membatasi output
  const topLeafPhases = leafPhases.slice(0, 20);

  console.log('\n📊 HASIL SCAN:');
  console.log('================================');

  if (leafPhases.length === 0) {
    console.log('✅ Tidak ada leaf phase dengan durasi >60 menit!');
    console.log('✅ Semua leaf phases sudah sesuai requirement (<60 menit)');
  } else {
    console.log(`⚠️  Ditemukan ${leafPhases.length} leaf phases dengan durasi >60 menit`);
    console.log(`📋 Menampilkan ${Math.min(topLeafPhases.length, leafPhases.length)} teratas:\n`);

    // Group by file (hanya untuk top phases)
    const groupedByFile = {};
    topLeafPhases.forEach(phase => {
      if (!groupedByFile[phase.file]) {
        groupedByFile[phase.file] = [];
      }
      groupedByFile[phase.file].push(phase);
    });

    for (const [fileName, phases] of Object.entries(groupedByFile)) {
      console.log(`📄 File: ${fileName}`);

      phases.forEach(phase => {
        console.log(`   - Phase ${phase.phaseId}: ${phase.title}`);
        console.log(`     Duration: ${phase.duration} minutes`);
        console.log(`     Status: ${phase.status}`);
        logDurationCheck(phase.phaseId, phase.duration);
        console.log('');
      });
    }

    if (leafPhases.length > topLeafPhases.length) {
      console.log(`... dan ${leafPhases.length - topLeafPhases.length} leaf phases lainnya.\n`);
    }

    console.log('\n🎯 REKOMENDASI:');
    console.log('================================');
    console.log(`1. Breakdown ${leafPhases.length} leaf phases di atas`);
    console.log('2. Gunakan plan-breakdown-analyzer agent untuk setiap phase');
    console.log('3. Update breakdown log setelah selesai');
  }

  console.log('\n📈 STATISTICS:');
  console.log('================================');
  console.log(`Total files scanned: ${allFiles.length}`);
  console.log(`Total leaf files: ${processedFiles.length}`);
  console.log(`Leaf phases with >60min: ${leafPhases.length}`);

  if (leafPhases.length > 0) {
    console.log('\n🔄 NEXT STEPS:');
    console.log('================================');
    console.log('Run breakdown untuk phase-phase di atas menggunakan:');
    console.log('node find-leaf-phases.js -> untuk mendapatkan daftar phase');
    console.log('Kemudian gunakan plan-breakdown-analyzer agent untuk breakdown');
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  needsBreakdown,
  logDurationCheck,
  getAllPlanFiles,
  isLeafPhase,
  parsePhaseData
};