#!/usr/bin/env node

const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const {
    parseTaskOutput,
    executeCommand,
    updateTaskStatus,
    runClaudeTask,
    runValidation,
    filterTasks,
    displaySummary
} = require('./helpers');

/**
 * Run Tasks Script
 * Menjalankan get-leaf-tasks dan execute tasks dengan validation secara paralel
 */

class RunTasks {
    constructor() {
        this.scriptDir = __dirname;
        this.projectRoot = path.resolve(this.scriptDir, '../..');
        this.maxParallel = 5;
        this.runningTasks = new Set();
        this.completedTasks = 0;
        this.totalTasks = 0;
        this.results = [];
        this.loopMode = false;
        this.loopDelay = 5000; // 5 seconds delay between loops
        this.currentLoop = 0;
    }

    /**
     * Parse command line arguments
     */
    parseArgs() {
        const args = process.argv.slice(2);
        const options = {
            maxParallel: 5,
            filter: '',
            loop: false,
            loopDelay: 5000
        };

        // Check for loop mode
        if (args.includes('--loop') || args.includes('-l')) {
            options.loop = true;
            this.loopMode = true;

            // Remove loop flag from args
            const loopIndex = args.indexOf('--loop');
            if (loopIndex !== -1) args.splice(loopIndex, 1);
            const lIndex = args.indexOf('-l');
            if (lIndex !== -1) args.splice(lIndex, 1);
        }

        // Check for loop delay
        const delayIndex = args.findIndex(arg => arg.startsWith('--delay='));
        if (delayIndex !== -1) {
            options.loopDelay = parseInt(args[delayIndex].split('=')[1]) * 1000;
            this.loopDelay = options.loopDelay;
            args.splice(delayIndex, 1);
        }

        
        if (args[0] && !isNaN(args[0])) {
            options.maxParallel = parseInt(args[0]);
        }

        if (args[1]) {
            options.filter = args[1];
        }

        if (args[0] && isNaN(args[0])) {
            options.filter = args.join(' ');
        }

        this.maxParallel = options.maxParallel;
        return options;
    }

    
    /**
     * Get leaf tasks using existing script
     */
    async getLeafTasks() {
        try {
            const scriptPath = path.join(this.scriptDir, 'get-leaf-tasks.js');
            const { stdout, stderr, code } = await executeCommand(this.projectRoot, 'node', [scriptPath]);

            if (code !== 0) {
                throw new Error(`Script failed: ${stderr}`);
            }

            const tasks = parseTaskOutput(stdout);
            return tasks;
        } catch (error) {
            console.error('❌ Error getting leaf tasks:', error.message);
            throw error;
        }
    }

    
    /**
     * Run Claude with task description
     */
    async runClaudeTask(task) {
        this.runningTasks.add(task.id);
        this.completedTasks++;

        const result = await runClaudeTask(this.scriptDir, this.projectRoot, task);

        this.runningTasks.delete(task.id);
        console.log(`🏁 Task ${task.id} execution completed (${this.completedTasks}/${this.totalTasks})`);

        return result;
    }

    /**
     * Run validation for completed task
     */
    async runValidation(task) {
        return await runValidation(this.scriptDir, this.projectRoot, task);
    }

    /**
     * Run tasks in parallel with limit
     */
    async runTasksInParallel(tasks) {
        const results = [];
        let taskIndex = 0;

        // Process tasks in batches
        const processBatch = async () => {
            while (taskIndex < tasks.length && this.runningTasks.size < this.maxParallel) {
                const task = tasks[taskIndex++];
                const promise = this.runClaudeTask(task);
                results.push(promise);
            }
        };

        // Start initial batch
        await processBatch();

        // Continue processing as tasks complete
        while (this.runningTasks.size > 0) {
            await new Promise(resolve => setTimeout(resolve, 2000)); // Check every 2 seconds
            await processBatch();
        }

        // Wait for all remaining tasks
        return Promise.all(results);
    }

    /**
     * Display execution summary
     */
    showSummary(results, startTime) {
        displaySummary(results, this.totalTasks, startTime);
    }

    /**
     * Single execution run
     */
    async runSingle(options, startTime) {
        console.log('🔍 Getting leaf tasks...');
        const tasks = await this.getLeafTasks();

        if (tasks.length === 0) {
            console.log('ℹ️  No tasks found to execute.');
            return { hasTasks: false, results: [] };
        }

        // Apply filter if provided
        let filteredTasks = filterTasks(tasks, options.filter);
        if (options.filter) {
            console.log(`🔍 Filter applied: "${options.filter}"`);
            console.log(`📊 Found ${filteredTasks.length} matching tasks out of ${tasks.length} total`);
        } else {
            console.log(`📊 Found ${tasks.length} tasks to execute`);
        }

        if (filteredTasks.length === 0) {
            console.log('ℹ️  No tasks match the filter criteria.');
            return { hasTasks: false, results: [] };
        }

        // Sort by priority
        filteredTasks.sort((a, b) => a.priority - b.priority);

        this.totalTasks = filteredTasks.length;
        console.log(`🚀 Starting parallel execution (max ${this.maxParallel} concurrent tasks)...`);
        console.log('─'.repeat(70));

        const results = await this.runTasksInParallel(filteredTasks);
        this.showSummary(results, startTime);

        return { hasTasks: true, results, taskCount: filteredTasks.length };
    }

    /**
     * Main execution method with loop support
     */
    async run(options) {
        const overallStartTime = Date.now();
        this.currentLoop = 0;
        let totalResults = [];
        let totalTasksProcessed = 0;

        if (this.loopMode) {
            console.log(`🔄 Infinite loop mode enabled (${this.loopDelay/1000}s delay)`);
            console.log('🎯 Will run forever until manually stopped (Ctrl+C)');
            console.log('⚠️  Press Ctrl+C to stop the infinite loop');
            console.log('─'.repeat(70));
        }

        do {
            this.currentLoop++;
            const loopStartTime = Date.now();

            if (this.loopMode) {
                console.log(`\n🔄 Loop #${this.currentLoop}`);
                console.log('─'.repeat(50));
            }

            try {
                const result = await this.runSingle(options, loopStartTime);

                if (!result.hasTasks) {
                    if (this.loopMode) {
                        console.log('\n⏳ No tasks available now. Waiting before checking again...');
                        console.log('💤 Sleep mode - checking for new tasks...');
                        await this.delay(this.loopDelay);
                        continue; // Continue the loop instead of breaking
                    } else {
                        console.log('\n✅ No more tasks available. Stopping execution.');
                        break;
                    }
                }

                totalResults.push(...result.results);
                totalTasksProcessed += result.taskCount;

                if (this.loopMode) {
                    console.log(`\n⏳ Waiting ${this.loopDelay/1000}s before next loop...`);
                    await this.delay(this.loopDelay);
                }

            } catch (error) {
                console.error(`❌ Error in loop ${this.currentLoop}:`, error.message);

                if (this.loopMode) {
                    console.log('⚠️  Continuing to next loop despite error...');
                    await this.delay(this.loopDelay);
                } else {
                    throw error;
                }
            }

        } while (this.loopMode);

        // Final summary for loop mode
        if (this.loopMode) {
            this.showLoopSummary(totalResults, totalTasksProcessed, overallStartTime);
        }
    }

    /**
     * Delay function
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Show loop summary
     */
    showLoopSummary(allResults, totalTasks, startTime) {
        const endTime = Date.now();
        const duration = ((endTime - startTime) / 1000).toFixed(2);

        console.log('\n' + '='.repeat(70));
        console.log('🔄 INFINITE LOOP EXECUTION SUMMARY');
        console.log('='.repeat(70));
        console.log(`Total loops: ${this.currentLoop}`);
        console.log(`Total tasks processed: ${totalTasks}`);
        console.log(`Successful execution: ${allResults.filter(r => r.success).length}`);
        console.log(`Failed execution: ${allResults.filter(r => !r.success).length}`);
        console.log(`Validation passed: ${allResults.filter(r => r.validationPassed).length}`);
        console.log(`Total duration: ${duration} seconds`);
        console.log(`Average per loop: ${(duration / this.currentLoop).toFixed(2)} seconds`);
        console.log('🔄 Loop stopped by user (Ctrl+C)');

        // Show failed tasks across all loops
        const failedTasks = allResults.filter(r => !r.success);
        if (failedTasks.length > 0) {
            console.log('\n❌ FAILED TASKS:');
            failedTasks.forEach(result => {
                console.log(`   Task ${result.task.id}: ${result.error || 'Unknown error'}`);
            });
        }

        // Show validation failures across all loops
        const validationFailed = allResults.filter(r => r.success && !r.validationPassed);
        if (validationFailed.length > 0) {
            console.log('\n⚠️  TASKS NEEDING REVISION:');
            validationFailed.forEach(result => {
                console.log(`   Task ${result.task.id}: ${result.task.description.substring(0, 50)}...`);
            });
        }

        console.log('='.repeat(70));
    }
}

// CLI usage
if (require.main === module) {
    const runner = new RunTasks();
    const options = runner.parseArgs();

    runner.run(options);
}

module.exports = RunTasks;