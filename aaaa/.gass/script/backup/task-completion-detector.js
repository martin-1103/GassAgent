#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

class TaskCompletionDetector {
    constructor() {
        this.projectRoot = process.cwd();
        this.expectedDeliverables = {
            '1.12.1': { // Test Infrastructure
                files: [
                    'packages/backend/tests/config/test-database.config.ts',
                    'packages/backend/tests/config/mock-servers.config.ts',
                    'packages/backend/tests/fixtures/rest-fixtures.ts',
                    'packages/backend/tests/fixtures/grpc-fixtures.ts',
                    'packages/backend/tests/fixtures/graphql-fixtures.ts',
                    'packages/backend/tests/setup/test-setup.ts',
                    'packages/backend/tests/utils/mock-server.factory.ts',
                    'packages/backend/tests/utils/test-data.generator.ts',
                    'packages/backend/tests/helpers/test-environment.helper.ts',
                    'vitest.config.ts'
                ],
                keywords: ['test infrastructure', 'setup complete', 'mock server', 'test database'],
                minFiles: 8
            },
            '1.13.1': { // Caching Layer
                files: [
                    'packages/backend/src/cache/redis-cache.service.ts',
                    'packages/backend/src/cache/cache.config.ts',
                    'packages/backend/src/cache/interfaces/cache.interface.ts',
                    'packages/backend/src/cache/utils/cache.util.ts',
                    'packages/backend/src/cache/strategies/lru-cache.strategy.ts',
                    'packages/backend/src/cache/middleware/cache.middleware.ts'
                ],
                keywords: ['caching layer', 'redis', 'cache strategy', 'complete'],
                minFiles: 5
            },
            '1.14.1': { // Documentation
                files: [
                    'docs/api/README.md',
                    'docs/architecture/README.md',
                    'docs/user-guide/README.md',
                    'docs/development/README.md',
                    'typedoc.json',
                    'swagger.yaml',
                    'docs/build/generate-docs.js'
                ],
                keywords: ['documentation', 'api docs', 'generated', 'complete'],
                minFiles: 6
            },
            '1.15.1': { // Test Environment
                files: [
                    'packages/backend/tests/integration/api.integration.test.ts',
                    'packages/backend/tests/integration/grpc.integration.test.ts',
                    'packages/backend/tests/integration/graphql.integration.test.ts',
                    'packages/backend/tests/e2e/flows.e2e.test.ts',
                    'packages/backend/tests/config/test-environment.config.ts',
                    'docker-compose.test.yml'
                ],
                keywords: ['test environment', 'integration test', 'complete setup'],
                minFiles: 5
            },
            '2.1.1': { // Canvas Component ✅ SELESAI
                files: [
                    'packages/web/src/components/flow-builder/canvas/canvas.component.tsx',
                    'packages/web/src/components/flow-builder/canvas/hooks/use-canvas-state.ts',
                    'packages/web/src/components/flow-builder/canvas/hooks/use-canvas-events.ts',
                    'packages/web/src/components/flow-builder/canvas/hooks/use-canvas-coordinates.ts',
                    'packages/web/src/components/flow-builder/canvas/types/canvas.types.ts',
                    'packages/web/src/components/flow-builder/canvas/interfaces/canvas.interface.ts',
                    'packages/web/src/components/flow-builder/canvas/utils/canvas.util.ts',
                    'packages/web/src/components/flow-builder/canvas/constants/canvas.constants.ts',
                    'packages/web/src/components/flow-builder/canvas/canvas.styles.ts',
                    'packages/web/src/components/flow-builder/canvas/index.ts'
                ],
                keywords: ['canvas component', 'flow builder', 'complete'],
                minFiles: 8
            }
        };
    }

    /**
     * Check if task is completed by analyzing files and content
     */
    isTaskCompleted(taskId) {
        const taskConfig = this.expectedDeliverables[taskId];
        if (!taskConfig) {
            return { completed: false, reason: 'Unknown task ID' };
        }

        let filesFound = 0;
        let keywordsFound = 0;
        const missingFiles = [];

        // Check files exist
        taskConfig.files.forEach(file => {
            const filePath = path.join(this.projectRoot, file);
            if (fs.existsSync(filePath)) {
                filesFound++;
            } else {
                missingFiles.push(file);
            }
        });

        // Check for completion keywords in files
        const searchDirs = [
            'packages/backend/src',
            'packages/web/src',
            'docs',
            'packages/backend/tests'
        ];

        searchDirs.forEach(dir => {
            const dirPath = path.join(this.projectRoot, dir);
            if (fs.existsSync(dirPath)) {
                const files = this.getAllFiles(dirPath);
                files.forEach(file => {
                    if (file.endsWith('.ts') || file.endsWith('.js') || file.endsWith('.md')) {
                        try {
                            const content = fs.readFileSync(file, 'utf8');
                            taskConfig.keywords.forEach(keyword => {
                                if (content.toLowerCase().includes(keyword.toLowerCase())) {
                                    keywordsFound++;
                                }
                            });
                        } catch (error) {
                            // Skip files that can't be read
                        }
                    }
                });
            }
        });

        const fileRatio = filesFound / taskConfig.files.length;
        const hasEnoughFiles = filesFound >= taskConfig.minFiles;
        const hasKeywords = keywordsFound > 0;

        const completed = fileRatio >= 0.8 && hasEnoughFiles; // 80% files complete

        return {
            completed,
            filesFound,
            totalFiles: taskConfig.files.length,
            fileRatio: Math.round(fileRatio * 100),
            keywordsFound,
            hasEnoughFiles,
            hasKeywords,
            missingFiles: missingFiles.slice(0, 5), // Show max 5 missing files
            status: completed ? 'COMPLETED' : 'IN_PROGRESS'
        };
    }

    getAllFiles(dirPath, arrayOfFiles = []) {
        const files = fs.readdirSync(dirPath);

        files.forEach(file => {
            const fullPath = path.join(dirPath, file);
            if (fs.statSync(fullPath).isDirectory()) {
                arrayOfFiles = this.getAllFiles(fullPath, arrayOfFiles);
            } else {
                arrayOfFiles.push(fullPath);
            }
        });

        return arrayOfFiles;
    }

    /**
     * Get overall completion status
     */
    getAllTaskStatus() {
        const results = {};
        const allTaskIds = Object.keys(this.expectedDeliverables);

        allTaskIds.forEach(taskId => {
            results[taskId] = this.isTaskCompleted(taskId);
        });

        return results;
    }

    /**
     * Check if all tasks are completed
     */
    areAllTasksCompleted() {
        const status = this.getAllTaskStatus();
        const completed = Object.values(status).every(task => task.completed);
        const incomplete = Object.entries(status).filter(([_, task]) => !task.completed);

        return {
            completed,
            incompleteTasks: incomplete.map(([id, task]) => ({ id, ...task })),
            summary: {
                total: Object.keys(status).length,
                completed: Object.values(status).filter(t => t.completed).length,
                inProgress: Object.values(status).filter(t => !t.completed).length
            }
        };
    }

    /**
     * Generate completion report
     */
    generateReport() {
        const allStatus = this.getAllTaskStatus();
        const overall = this.areAllTasksCompleted();

        console.log('\n📊 TASK COMPLETION REPORT');
        console.log('='.repeat(60));

        Object.entries(allStatus).forEach(([taskId, status]) => {
            const icon = status.completed ? '✅' : '🔄';
            const percentage = status.fileRatio;

            console.log(`${icon} Task ${taskId}: ${percentage}% Complete`);
            console.log(`   Files: ${status.filesFound}/${status.totalFiles}`);

            if (!status.completed && status.missingFiles.length > 0) {
                console.log(`   Missing: ${status.missingFiles.slice(0, 3).join(', ')}`);
            }
        });

        console.log('\n📋 SUMMARY:');
        console.log(`Total Tasks: ${overall.summary.total}`);
        console.log(`Completed: ${overall.summary.completed}`);
        console.log(`In Progress: ${overall.summary.inProgress}`);

        if (overall.completed) {
            console.log('\n🎉 ALL TASKS COMPLETED!');
        } else {
            console.log(`\n⏳ ${overall.summary.inProgress} task(s) still in progress`);
        }

        return overall;
    }
}

// CLI Usage
if (require.main === module) {
    const detector = new TaskCompletionDetector();

    if (process.argv.includes('--watch') || process.argv.includes('-w')) {
        console.log('👀 Watching task completion status...');

        const checkInterval = setInterval(() => {
            console.clear();
            const result = detector.generateReport();

            if (result.completed) {
                console.log('\n🎉 ALL TASKS COMPLETED! Stopping watch...');
                clearInterval(checkInterval);
                process.exit(0);
            }
        }, 10000); // Check every 10 seconds

        process.on('SIGINT', () => {
            clearInterval(checkInterval);
            console.log('\n🛑 Stopped watching');
            process.exit(0);
        });

    } else {
        detector.generateReport();
    }
}

module.exports = TaskCompletionDetector;