#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const PLAN_DIR = path.join(__dirname, '..', 'plan');

/**
 * CLI script untuk update status semua phase dalam direktori .ai/plan
 *
 * Features:
 * - Top-down update: Update parent → semua children otomatis update
 * - Bottom-up update: Children completed → parent otomatis completed (cascade)
 *
 * Usage:
 *   node update-phase-status.js --status pending --all
 *   node update-phase-status.js --status in-progress --phase 1
 *   node update-phase-status.js --status completed --phase 1.1
 *   node update-phase-status.js --list
 */

function showUsage() {
  console.log(`
Usage: node update-phase-status.js [options]

Options:
  --status <status>    Status baru untuk phase (pending, in-progress, completed)
  --all               Update semua phase dan sub-phase
  --phase <id>        Update phase spesifik (contoh: 1, 1.1, 1.1.1)
  --list              Tampilkan status semua phase saat ini
  --help              Tampilkan bantuan ini

Contoh:
  node update-phase-status.js --status in-progress --all
  node update-phase-status.js --status completed --phase 1.1  # Auto-update parent jika semua children completed
  node update-phase-status.js --list
`);
}

function loadJSON(filePath) {
  try {
    const content = fs.readFileSync(filePath, 'utf8');
    return JSON.parse(content);
  } catch (error) {
    console.error(`Error loading ${filePath}:`, error.message);
    return null;
  }
}

function saveJSON(filePath, data) {
  try {
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf8');
    return true;
  } catch (error) {
    console.error(`Error saving ${filePath}:`, error.message);
    return false;
  }
}

function getAllPhaseFiles() {
  const files = fs.readdirSync(PLAN_DIR);
  return files
    .filter(file => file.endsWith('.json') && file !== 'phases.json')
    .sort((a, b) => {
      // Sort by phase ID numerically
      const aId = a.replace('.json', '');
      const bId = b.replace('.json', '');
      return aId.localeCompare(bId, undefined, { numeric: true });
    });
}

function updatePhaseStatus(phaseId, newStatus) {
  const filePath = path.join(PLAN_DIR, `${phaseId}.json`);

  if (!fs.existsSync(filePath)) {
    console.log(`Phase file not found: ${phaseId}.json`);
    return false;
  }

  const data = loadJSON(filePath);
  if (!data) return false;

  // Update status di phase utama
  const oldStatus = data.status;
  data.status = newStatus;

  // Update status di semua sub-phases jika ada
  if (data.phases && Array.isArray(data.phases)) {
    data.phases.forEach(subPhase => {
      subPhase.status = newStatus;
    });
  }

  if (saveJSON(filePath, data)) {
    console.log(`✓ ${phaseId}.json: ${oldStatus} → ${newStatus}`);

    // Update sub-phases
    if (data.phases && Array.isArray(data.phases)) {
      data.phases.forEach(subPhase => {
        updatePhaseStatus(subPhase.id, newStatus);
      });
    }

    // Auto-update parent status if all children are completed
    if (newStatus === 'completed') {
      updateParentStatusIfAllChildrenCompleted(phaseId);
    }

    return true;
  }

  return false;
}

function updateParentStatusIfAllChildrenCompleted(childPhaseId) {
  // Extract parent phase ID (e.g., from "2.1.1" get "2.1", from "2.1" get "2")
  const parts = childPhaseId.split('.');
  if (parts.length <= 1) {
    return; // No parent for main phases
  }

  const parentPhaseId = parts.slice(0, -1).join('.');

  const parentFilePath = path.join(PLAN_DIR, `${parentPhaseId}.json`);
  if (!fs.existsSync(parentFilePath)) {
    return; // Parent file doesn't exist
  }

  const parentData = loadJSON(parentFilePath);
  if (!parentData || !parentData.phases || !Array.isArray(parentData.phases)) {
    return; // Parent has no phases to check
  }

  // Check if all children are completed
  const allChildrenCompleted = parentData.phases.every(child => {
    const childStatus = child.status || 'pending';
    return childStatus === 'completed';
  });

  if (allChildrenCompleted && parentData.status !== 'completed') {
    const oldStatus = parentData.status;
    parentData.status = 'completed';

    if (saveJSON(parentFilePath, parentData)) {
      console.log(`🎯 AUTO-UPDATE: ${parentPhaseId}.json: ${oldStatus} → completed (all children completed)`);

      // Recursively check parent's parent
      updateParentStatusIfAllChildrenCompleted(parentPhaseId);
    }
  }
}

function listAllPhases() {
  console.log('\n=== Status Semua Phase ===\n');

  // Load main phases from phases.json
  const phasesData = loadJSON(path.join(PLAN_DIR, 'phases.json'));
  if (phasesData && phasesData.phases) {
    console.log('Main Phases:');
    phasesData.phases.forEach(phase => {
      console.log(`  Phase ${phase.id}: ${phase.title} [${phase.status}]`);
    });
    console.log('');
  }

  // Load detailed phase files
  console.log('Detailed Phase Files:');
  const files = getAllPhaseFiles();

  files.forEach(file => {
    const phaseId = file.replace('.json', '');
    const filePath = path.join(PLAN_DIR, file);
    const data = loadJSON(filePath);

    if (data) {
      const indent = phaseId.includes('.') ? '  └─ ' : '  ';
      const status = data.status || 'unknown';
      const title = data.title || 'Untitled';

      console.log(`${indent}${phaseId}: ${title} [${status}]`);

      // Show sub-phases count if exists
      if (data.phases && data.phases.length > 0) {
        console.log(`${indent}  └─ ${data.phases.length} sub-phases`);
      }
    }
  });

  console.log('');
}

function updateAllPhases(newStatus) {
  console.log(`\n=== Mengupdate semua phase ke status: ${newStatus} ===\n`);

  // Update main phases.json
  const phasesPath = path.join(PLAN_DIR, 'phases.json');
  const phasesData = loadJSON(phasesPath);

  if (phasesData && phasesData.phases) {
    phasesData.phases.forEach(phase => {
      phase.status = newStatus;
    });

    if (saveJSON(phasesPath, phasesData)) {
      console.log('✓ phases.json updated');
    }
  }

  // Update all detailed phase files
  const files = getAllPhaseFiles();
  let successCount = 0;

  files.forEach(file => {
    const phaseId = file.replace('.json', '');
    if (updatePhaseStatus(phaseId, newStatus)) {
      successCount++;
    }
  });

  console.log(`\n✓ Berhasil update ${successCount} phase files`);
}

function main() {
  const args = process.argv.slice(2);

  if (args.includes('--help') || args.length === 0) {
    showUsage();
    return;
  }

  if (args.includes('--list')) {
    listAllPhases();
    return;
  }

  const statusIndex = args.indexOf('--status');
  const allIndex = args.indexOf('--all');
  const phaseIndex = args.indexOf('--phase');

  if (statusIndex === -1 || statusIndex === args.length - 1) {
    console.error('Error: --status option requires a value');
    showUsage();
    process.exit(1);
  }

  const newStatus = args[statusIndex + 1];
  const validStatuses = ['pending', 'in-progress', 'completed'];

  if (!validStatuses.includes(newStatus)) {
    console.error(`Error: Invalid status "${newStatus}". Valid statuses: ${validStatuses.join(', ')}`);
    process.exit(1);
  }

  if (allIndex !== -1) {
    updateAllPhases(newStatus);
  } else if (phaseIndex !== -1 && phaseIndex < args.length - 1) {
    const phaseId = args[phaseIndex + 1];
    console.log(`\n=== Mengupdate phase ${phaseId} ke status: ${newStatus} ===\n`);
    updatePhaseStatus(phaseId, newStatus);
  } else {
    console.error('Error: Please specify either --all or --phase <id>');
    showUsage();
    process.exit(1);
  }
}

if (require.main === module) {
  main();
}

module.exports = {
  updatePhaseStatus,
  updateAllPhases,
  listAllPhases
};