#!/usr/bin/env node

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

class TaskMonitor {
    constructor() {
        this.tasks = new Map();
        this.startTime = Date.now();
        this.checkInterval = 5000; // 5 seconds
    }

    log(message) {
        const timestamp = new Date().toLocaleTimeString();
        console.log(`[${timestamp}] ${message}`);
    }

    checkTaskStatus(shellId) {
        try {
            // Cek apakah ada file hasil yang dibuat
            const possibleOutputs = [
                '.ai/brain/validation/',
                'packages/backend/tests/',
                'packages/web/src/',
                'packages/backend/src/cache/',
                'docs/',
                'vitest.config.ts'
            ];

            for (const output of possibleOutputs) {
                const fullPath = path.join(process.cwd(), output);
                if (fs.existsSync(fullPath)) {
                    const stats = fs.statSync(fullPath);
                    const modifiedTime = stats.mtime;
                    const taskStartTime = this.startTime;

                    if (modifiedTime > new Date(taskStartTime)) {
                        return { status: 'working', lastModified: modifiedTime };
                    }
                }
            }

            return { status: 'unknown', lastModified: null };
        } catch (error) {
            return { status: 'error', error: error.message };
        }
    }

    async monitorTasks() {
        this.log('🚀 Task Monitor Started');
        this.log('📋 Monitoring 5 background tasks...');

        const monitor = setInterval(() => {
            const elapsed = Math.floor((Date.now() - this.startTime) / 1000);
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;

            console.log(`\n⏰ Elapsed: ${minutes}m ${seconds}s`);
            console.log('─'.repeat(50));

            // Check file system changes
            const task1 = this.checkTaskStatus('1.12.1');
            const task2 = this.checkTaskStatus('1.13.1');
            const task3 = this.checkTaskStatus('1.14.1');
            const task4 = this.checkTaskStatus('1.15.1');
            const task5 = this.checkTaskStatus('2.1.1');

            console.log(`📝 Test Infrastructure (1.12.1): ${task1.status}`);
            console.log(`🗄️  Caching Layer (1.13.1): ${task2.status}`);
            console.log(`📚 Documentation (1.14.1): ${task3.status}`);
            console.log(`🧪 Test Environment (1.15.1): ${task4.status}`);
            console.log(`🎨 Canvas Component (2.1.1): ${task5.status}`);

            // Check if any files were created
            this.checkForNewFiles();

            // Stop after 30 minutes
            if (elapsed > 1800) {
                clearInterval(monitor);
                this.log('⏰ Timeout reached (30 minutes)');
                this.generateReport();
                process.exit(0);
            }

        }, this.checkInterval);

        // Handle Ctrl+C
        process.on('SIGINT', () => {
            clearInterval(monitor);
            this.log('\n🛑 Monitoring stopped by user');
            this.generateReport();
            process.exit(0);
        });
    }

    checkForNewFiles() {
        const dirsToCheck = [
            'packages/backend/tests',
            'packages/backend/src/cache',
            'docs',
            'packages/web/src/components'
        ];

        let newFilesFound = false;

        dirsToCheck.forEach(dir => {
            const fullPath = path.join(process.cwd(), dir);
            if (fs.existsSync(fullPath)) {
                const files = this.getRecentFiles(fullPath);
                if (files.length > 0) {
                    console.log(`  📁 ${dir}: ${files.length} new files`);
                    files.forEach(file => console.log(`    ✅ ${file}`));
                    newFilesFound = true;
                }
            }
        });

        if (newFilesFound) {
            console.log('  🎉 Progress detected!');
        }
    }

    getRecentFiles(dir, maxAge = 300000) { // 5 minutes
        try {
            const files = fs.readdirSync(dir, { recursive: true });
            const now = Date.now();
            const recentFiles = [];

            files.forEach(file => {
                const filePath = path.join(dir, file);
                const stats = fs.statSync(filePath);
                if (stats.isFile() && (now - stats.mtime.getTime()) < maxAge) {
                    recentFiles.push(file);
                }
            });

            return recentFiles;
        } catch (error) {
            return [];
        }
    }

    generateReport() {
        this.log('\n📊 Generating Final Report...');

        const report = {
            timestamp: new Date().toISOString(),
            duration: Math.floor((Date.now() - this.startTime) / 1000),
            tasks: {
                '1.12.1': { name: 'Test Infrastructure', status: this.checkTaskStatus('1.12.1') },
                '1.13.1': { name: 'Caching Layer', status: this.checkTaskStatus('1.13.1') },
                '1.14.1': { name: 'Documentation', status: this.checkTaskStatus('1.14.1') },
                '1.15.1': { name: 'Test Environment', status: this.checkTaskStatus('1.15.1') },
                '2.1.1': { name: 'Canvas Component', status: this.checkTaskStatus('2.1.1') }
            }
        };

        const reportPath = '.ai/brain/task-monitor-report.json';
        fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
        this.log(`📄 Report saved to: ${reportPath}`);

        // Summary
        console.log('\n📋 EXECUTION SUMMARY');
        console.log('='.repeat(50));
        Object.entries(report.tasks).forEach(([id, task]) => {
            console.log(`${id}: ${task.name.padEnd(20)} - ${task.status.status}`);
        });
    }
}

// Start monitoring
const monitor = new TaskMonitor();
monitor.monitorTasks().catch(console.error);