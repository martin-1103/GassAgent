#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const PLAN_DIR = path.join(__dirname, '..', 'plan');

/**
 * Script untuk mengecek completion status dari phase beserta semua sub-phases
 */

function loadJSON(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(content);
  } catch (error) {
    console.error(`Error loading ${filePath}:`, error.message);
    return null;
  }
}

function getPhaseStatus(phaseId) {
  const filePath = path.join(PLAN_DIR, `${phaseId}.json`);
  if (!fs.existsSync(filePath)) {
    return 'unknown';
  }
  const data = loadJSON(filePath);
  return data ? (data.status || 'pending') : 'unknown';
}

function checkPhaseCompletion(phaseId, indent = 0) {
  const filePath = path.join(PLAN_DIR, `${phaseId}.json`);
  const data = loadJSON(filePath);

  if (!data) {
    console.log(`${'  '.repeat(indent)}❌ ${phaseId}: File tidak ditemukan`);
    return { completed: 0, total: 0, status: 'unknown' };
  }

  const status = data.status || 'pending';
  const statusIcon = status === 'completed' ? '✅' : status === 'in-progress' ? '🔄' : '⏳';

  console.log(`${'  '.repeat(indent)}${statusIcon} ${phaseId}: ${data.title}`);

  if (!data.phases || data.phases.length === 0) {
    // Leaf phase - tidak punya sub-phases
    return {
      completed: status === 'completed' ? 1 : 0,
      total: 1,
      status: status
    };
  }

  // Parent phase - hitung completion dari sub-phases
  let totalCompleted = 0;
  let totalSubPhases = 0;

  data.phases.forEach(subPhase => {
    const subPhaseResult = checkSubPhaseCompletion(subPhase, phaseId, indent + 1);
    totalCompleted += subPhaseResult.completed;
    totalSubPhases += subPhaseResult.total;
  });

  const percentage = totalSubPhases > 0 ? Math.round((totalCompleted / totalSubPhases) * 100) : 0;
  const parentShouldBeCompleted = percentage === 100;

  console.log(`${'  '.repeat(indent)}📊 ${phaseId} Summary: ${totalCompleted}/${totalSubPhases} completed (${percentage}%)`);

  if (parentShouldBeCompleted && status !== 'completed') {
    console.log(`${'  '.repeat(indent)}⚠️  ${phaseId} SEHARUSNYA completed (semua sub-phases selesai)`);
  } else if (!parentShouldBeCompleted && status === 'completed') {
    console.log(`${'  '.repeat(indent)}⚠️  ${phaseId} TIDAK seharusnya completed (masih ada sub-phases pending)`);
  }

  return {
    completed: totalCompleted,
    total: totalSubPhases,
    status: status,
    percentage: percentage
  };
}

function checkSubPhaseCompletion(subPhase, parentId, indent) {
  const status = subPhase.status || 'pending';
  const statusIcon = status === 'completed' ? '✅' : status === 'in-progress' ? '🔄' : '⏳';

  console.log(`${'  '.repeat(indent)}${statusIcon} ${subPhase.id} (parent: ${parentId}): ${subPhase.title}`);

  // Cek apakah sub-phase ini punya file terpisah dengan sub-phases lagi
  const subPhaseFilePath = path.join(PLAN_DIR, `${subPhase.id}.json`);
  if (fs.existsSync(subPhaseFilePath)) {
    const subPhaseData = loadJSON(subPhaseFilePath);
    if (subPhaseData && subPhaseData.phases && subPhaseData.phases.length > 0) {
      // Ini parent dari leaf phases - rekursif
      let totalCompleted = 0;
      let totalSubPhases = 0;

      subPhaseData.phases.forEach(leafPhase => {
        const leafResult = checkLeafPhaseCompletion(leafPhase, subPhase.id, indent + 1);
        totalCompleted += leafResult.completed;
        totalSubPhases += leafResult.total;
      });

      const percentage = totalSubPhases > 0 ? Math.round((totalCompleted / totalSubPhases) * 100) : 0;
      console.log(`${'  '.repeat(indent)}📊 ${subPhase.id} Summary: ${totalCompleted}/${totalSubPhases} completed (${percentage}%)`);

      if (percentage === 100 && status !== 'completed') {
        console.log(`${'  '.repeat(indent)}⚠️  ${subPhase.id} SEHARUSNYA completed (semua leaf phases selesai)`);
      }

      return { completed: totalCompleted, total: totalSubPhases };
    }
  }

  // Ini adalah leaf phase
  return { completed: status === 'completed' ? 1 : 0, total: 1 };
}

function checkLeafPhaseCompletion(leafPhase, parentId, indent) {
  const status = leafPhase.status || 'pending';
  const statusIcon = status === 'completed' ? '✅' : status === 'in-progress' ? '🔄' : '⏳';

  console.log(`${'  '.repeat(indent)}${statusIcon} ${leafPhase.id} (parent: ${parentId}): ${leafPhase.title}`);

  return { completed: status === 'completed' ? 1 : 0, total: 1 };
}

function main() {
  const args = process.argv.slice(2);

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Usage: node check-phase-completion.js [options]

Options:
  --phase <id>    Check specific phase completion (contoh: 2, 2.1)
  --all           Check all main phases
  --help, -h      Tampilkan bantuan ini

Examples:
  node check-phase-completion.js --phase 2
  node check-phase-completion.js --all
`);
    return;
  }

  const phaseIndex = args.indexOf('--phase');
  const allIndex = args.indexOf('--all');

  if (allIndex !== -1) {
    console.log('🔍 Checking completion status for ALL main phases...\n');

    for (let i = 1; i <= 10; i++) {
      console.log(`\n${'='.repeat(80)}`);
      console.log(`📋 PHASE ${i} COMPLETION STATUS`);
      console.log(`${'='.repeat(80)}`);

      const result = checkPhaseCompletion(i.toString());

      if (result.total > 0) {
        console.log(`\n🎯 Phase ${i} Final Status: ${result.completed}/${result.total} completed (${result.percentage}%)`);
        console.log(`   Current Status: ${result.status}`);
        console.log(`   Should Be: ${result.percentage === 100 ? 'completed' : 'pending/in-progress'}`);
      }
    }
  } else if (phaseIndex !== -1 && phaseIndex < args.length - 1) {
    const phaseId = args[phaseIndex + 1];
    console.log(`🔍 Checking completion status for Phase ${phaseId}...\n`);

    const result = checkPhaseCompletion(phaseId);

    if (result.total > 0) {
      console.log(`\n🎯 Phase ${phaseId} Final Status: ${result.completed}/${result.total} completed (${result.percentage}%)`);
      console.log(`   Current Status: ${result.status}`);
      console.log(`   Should Be: ${result.percentage === 100 ? 'completed' : 'pending/in-progress'}`);
    }
  } else {
    console.log('❌ Please specify --phase <id> or --all');
    console.log('Use --help for more information.');
  }
}

if (require.main === module) {
  main();
}