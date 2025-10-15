#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const PLAN_DIR = path.join(__dirname, '..', 'plan');

/**
 * Script untuk mendapatkan TRUE leaf phases yang bisa dikerjakan
 * Leaf phases = sub-phases yang dependencies nya sudah completed (termasuk parent phase)
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

function areDependenciesCompleted(dependencies) {
  if (!dependencies || dependencies.length === 0) {
    return true; // Tidak ada dependency = bisa dikerjakan
  }
  return dependencies.every(depId => {
    const depStatus = getPhaseStatus(depId);
    return depStatus === 'completed';
  });
}

function isTrueLeafPhase(subPhase) {
  // Cek apakah sub-phase ini adalah leaf node (tidak punya file terpisah)
  const subPhaseFilePath = path.join(PLAN_DIR, `${subPhase.id}.json`);

  if (fs.existsSync(subPhaseFilePath)) {
    const subPhaseData = loadJSON(subPhaseFilePath);
    if (subPhaseData && subPhaseData.phases && subPhaseData.phases.length > 0) {
      return false; // Ini bukan leaf node, punya sub-phases lagi
    }
  }

  return true; // Ini adalah leaf node
}

function getAllLeafTasks() {
  const allFiles = fs.readdirSync(PLAN_DIR);
  const phaseFiles = allFiles.filter(file => file.endsWith('.json') && file !== 'phases.json');
  const tasks = [];

  phaseFiles.forEach(file => {
    const phaseId = file.replace('.json', '');
    const filePath = path.join(PLAN_DIR, file);
    const data = loadJSON(filePath);

    if (data && data.title) {
      // Tidak perlu cek status parent phase
      // Parent phase status adalah hasil dari children completion

      // Jika ini phase memiliki sub-phases, cek setiap sub-phase
      if (data.phases && Array.isArray(data.phases)) {
        data.phases.forEach(subPhase => {
          // Cek apakah ini true leaf phase
          if (!isTrueLeafPhase(subPhase)) {
            return; // Bukan leaf node, skip
          }

          // Cek dependencies
          const depsCompleted = areDependenciesCompleted(subPhase.dependencies);
          const isPending = subPhase.status === 'pending';

          if (depsCompleted && isPending) {
            const priority = typeof subPhase.priority === 'string' ?
              (subPhase.priority === 'high' ? 1 : subPhase.priority === 'medium' ? 2 : subPhase.priority === 'low' ? 3 : 999) :
              (subPhase.priority || 999);

            tasks.push({
              id: subPhase.id,
              title: subPhase.title,
              description: subPhase.description,
              duration: subPhase.duration,
              priority: priority,
              parent_id: phaseId,
              parent_status: data.status,
              status: subPhase.status,
              dependencies: subPhase.dependencies || [],
              deliverables: subPhase.deliverables || [],
              is_leaf: true
            });
          }
        });
      }
    }
  });

  // Sort by priority then by ID
  tasks.sort((a, b) => {
    if (a.priority !== b.priority) {
      return a.priority - b.priority;
    }
    return a.id.localeCompare(b.id, undefined, { numeric: true });
  });

  return tasks;
}

function getLeafTasksForPhase(phaseId) {
  const filePath = path.join(PLAN_DIR, `${phaseId}.json`);
  const data = loadJSON(filePath);

  if (!data || !data.phases || !Array.isArray(data.phases)) {
    return [];
  }

  // Tidak perlu cek status parent phase
  // Parent phase status adalah hasil dari children completion

  const tasks = [];

  data.phases.forEach(subPhase => {
    // Cek apakah ini true leaf phase
    if (!isTrueLeafPhase(subPhase)) {
      return; // Bukan leaf node, skip
    }

    // Cek dependencies
    const depsCompleted = areDependenciesCompleted(subPhase.dependencies);
    const isPending = subPhase.status === 'pending';

    if (depsCompleted && isPending) {
      const priority = typeof subPhase.priority === 'string' ?
        (subPhase.priority === 'high' ? 1 : subPhase.priority === 'medium' ? 2 : subPhase.priority === 'low' ? 3 : 999) :
        (subPhase.priority || 999);

      tasks.push({
        id: subPhase.id,
        title: subPhase.title,
        description: subPhase.description,
        duration: subPhase.duration,
        priority: priority,
        parent_id: phaseId,
        parent_status: data.status,
        status: subPhase.status,
        dependencies: subPhase.dependencies || [],
        deliverables: subPhase.deliverables || [],
        is_leaf: true
      });
    }
  });

  return tasks;
}

function formatTaskList(tasks, filterText = '') {
  // Limit to 5 items
  const limitedTasks = tasks.slice(0, 5);

  if (limitedTasks.length === 0) {
    console.log(JSON.stringify([], null, 2));
    return;
  }

  // Add all parent summaries to each task
  const tasksWithAllParents = limitedTasks.map(task => {
    const parentHierarchy = [];
    let currentParentId = task.parent_id;

    // Traverse up the parent hierarchy
    while (currentParentId) {
      const parentFilePath = path.join(PLAN_DIR, `${currentParentId}.json`);
      const parentData = loadJSON(parentFilePath);

      if (!parentData) break;

      parentHierarchy.push({
        id: currentParentId,
        title: parentData.title,
        description: parentData.description,
        status: parentData.status,
        progress: parentData.progress || 0
      });

      currentParentId = parentData.parent_id;
    }

    return {
      ...task,
      parent_hierarchy: parentHierarchy.reverse() // Root parent first
    };
  });

  // Format as JSON
  console.log(JSON.stringify(tasksWithAllParents, null, 2));

  }

function main() {
  const args = process.argv.slice(2);

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
Usage: node get-leaf-tasks.js [options]

Options:
  --phase <id>    Filter tasks by parent phase (contoh: 2, 3)
  --help, -h      Tampilkan bantuan ini

Note:
  Leaf tasks = Sub-phases yang:
  1. Tidak punya file terpisah (tidak ada {subPhase.id}.json)
  2. ATAU punya file tapi tidak punya sub-phases lagi
  3. Status pending
   4. Dependencies sudah completed
  5. Bisa dikerjakan kapan saja (parent status otomatis mengikuti children)

Examples:
  node get-leaf-tasks.js
  node get-leaf-tasks.js --phase 2
`);
    return;
  }

  const phaseIndex = args.indexOf('--phase');
  let filterText = '';

  console.log('🔍 Mencari TRUE leaf tasks yang bisa dikerjakan...');
  console.log('   Filter: True leaf nodes, dependencies completed, status pending');

  let leafTasks = [];

  if (phaseIndex !== -1 && phaseIndex < args.length - 1) {
    const phaseId = args[phaseIndex + 1];
    leafTasks = getLeafTasksForPhase(phaseId);
    filterText = ` di Phase ${phaseId}`;
    console.log(`   Phase: ${phaseId}`);
  } else {
    leafTasks = getAllLeafTasks();
  }

  formatTaskList(leafTasks, filterText);
}

if (require.main === module) {
  main();
}

module.exports = {
  getAllLeafTasks,
  getLeafTasksForPhase
};