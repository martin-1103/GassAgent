#!/usr/bin/env node

/**
 * Enhanced Plan Breakdown Analyzer dengan Loop Tracking
 * Fungsi:
 * 1. Membaca plan.json dari .ai/plan/
 * 2. Membaca tasks.json dari .ai/plan/
 * 3. Jika tasks.json ada, cek breakdown_complete
 * 4. Jika breakdown_complete === false atau duration > 30 menit, pecah
 * 5. Jika tasks.json tidak ada, generate dengan AI
 * 6. Simpan output di .ai/output/{phase_id}.json
 * 7. Loop terus sampai semua phases complete
 */

const fs = require('fs').promises;
const path = require('path');
const { spawn } = require('child_process');
const chalk = require('chalk');
const readline = require('readline');

// Import helper functions
const {
  readJsonFile,
  writeJsonFile,
  ensureDir,
  fileExists,
  parseDuration,
  formatDuration,
  logger,
  getPhaseDuration,
  validatePhaseData
} = require('./helpers');

// Track state untuk loop
const state = {
  completedPhases: new Set(),
  failedPhases: new Set(),
  maxIterations: 100,
  currentIteration: 0
};

class PlanBreakdownAnalyzer {
    constructor() {
        // Set working directory to project root instead of script directory
        this.projectRoot = process.cwd();
        if (this.projectRoot.endsWith('script')) {
            this.projectRoot = path.dirname(this.projectRoot);
        }

        this.planDir = path.join(this.projectRoot, 'plan');
        this.outputDir = path.join(this.projectRoot, 'output');
        this.loopTrackingFile = path.join(this.projectRoot, '.breakdown_loop_state.json');
    }

    /**
     * Load loop state dari file
     */
    async loadLoopState() {
        try {
            if (await fileExists(this.loopTrackingFile)) {
                const stateData = await readJsonFile(this.loopTrackingFile);
                state.completedPhases = new Set(stateData.completedPhases || []);
                state.failedPhases = new Set(stateData.failedPhases || []);
                state.currentIteration = stateData.currentIteration || 0;

                logger.info(`Loaded loop state: ${state.completedPhases.size} completed, ${state.failedPhases.size} failed`);
            }
        } catch (error) {
            logger.warn('Failed to load loop state, starting fresh:', error.message);
        }
    }

    /**
     * Save loop state ke file
     */
    async saveLoopState() {
        try {
            const stateData = {
                completedPhases: Array.from(state.completedPhases),
                failedPhases: Array.from(state.failedPhases),
                currentIteration: state.currentIteration,
                lastUpdated: new Date().toISOString()
            };

            await writeJsonFile(this.loopTrackingFile, stateData);
            logger.debug('Loop state saved');
        } catch (error) {
            logger.error('Failed to save loop state:', error.message);
        }
    }

    /**
     * Reset loop state
     */
    async resetLoopState() {
        state.completedPhases.clear();
        state.failedPhases.clear();
        state.currentIteration = 0;

        try {
            await fs.unlink(this.loopTrackingFile);
            logger.info('Loop state reset');
        } catch (error) {
            // File mungkin tidak ada, abaikan
        }
    }

    /**
     * Membaca plan.json
     */
    async readPlanJson() {
        try {
            const planPath = path.join(this.planDir, 'phases.json');
            logger.info(`Reading plan from: ${planPath}`);

            const planData = await readJsonFile(planPath);

            if (!planData.phases || !Array.isArray(planData.phases)) {
                throw new Error('Invalid plan.json structure: missing phases array');
            }

            logger.info(`Loaded plan with ${planData.phases.length} phases`);
            return planData;
        } catch (error) {
            logger.error('Failed to read plan.json:', error);
            throw error;
        }
    }

    /**
     * Membaca tasks.json untuk phase tertentu
     */
    async readTasksJson(phaseId) {
        try {
            const tasksPath = path.join(this.planDir, `${phaseId}.json`);

            if (!(await fileExists(tasksPath))) {
                logger.info(`Tasks file not found for phase ${phaseId}: ${tasksPath}`);
                return null;
            }

            const tasksData = await readJsonFile(tasksPath);
            logger.info(`Loaded tasks for phase ${phaseId}`);
            return tasksData;
        } catch (error) {
            logger.error(`Failed to read tasks for phase ${phaseId}:`, error);
            return null;
        }
    }

    /**
     * Mengecek apakah phase perlu di-breakdown
     */
    shouldBreakdown(phase, tasksData) {
        // Jika tasksData tidak ada, perlu generate
        if (!tasksData) {
            logger.info(`Phase ${phase.id} needs tasks generation`);
            return true;
        }

        // Jika breakdown_complete === false, perlu breakdown
        if (tasksData.breakdown_complete === false) {
            logger.info(`Phase ${phase.id} has incomplete breakdown`);
            return true;
        }

        // Cek duration
        const duration = getPhaseDuration(phase);
        if (duration > 30) { // 30 menit
            logger.info(`Phase ${phase.id} duration ${duration}min > 30min, needs breakdown`);
            return true;
        }

        // Jika sudah pernah di-breakdown tapi gagal, coba lagi
        if (state.failedPhases.has(phase.id.toString())) {
            logger.info(`Phase ${phase.id} previously failed, retrying`);
            return true;
        }

        logger.info(`Phase ${phase.id} doesn't need breakdown (duration: ${duration}min)`);
        return false;
    }

    /**
     * Generate tasks untuk phase menggunakan AI
     */
    async generateTasksForPhase(phase) {
        try {
            logger.info(`Generating tasks for phase ${phase.id} using AI...`);

            const prompt = this.buildPromptForPhase(phase);
            const phaseFileName = `${phase.id}.json`;
            const outputPath = path.join(this.outputDir, phaseFileName);

            // Panggil AI dengan task manager
            const result = await this.callAI(prompt, outputPath);

            if (result.success) {
                // Update status di plan directory
                await this.updatePhaseTasks(phase.id, result.data);
                state.completedPhases.add(phase.id.toString());
                state.failedPhases.delete(phase.id.toString()); // Remove from failed if present

                logger.info(`✅ Successfully generated tasks for phase ${phase.id}`);
                return true;
            } else {
                state.failedPhases.add(phase.id.toString());
                logger.error(`❌ Failed to generate tasks for phase ${phase.id}: ${result.error}`);
                return false;
            }
        } catch (error) {
            state.failedPhases.add(phase.id.toString());
            logger.error(`❌ Error generating tasks for phase ${phase.id}:`, error);
            return false;
        }
    }

    /**
     * Build prompt untuk phase
     */
    buildPromptForPhase(phase) {
        const durationStr = phase.duration || 'Unknown';
        const priorityStr = phase.priority || 'medium';
        const depsStr = phase.dependencies ? phase.dependencies.join(', ') : 'None';

        return `You are a project planning expert. Break down the following phase into detailed sub-phases:

PHASE ID: ${phase.id}
TITLE: ${phase.title}
DURATION: ${durationStr}
PRIORITY: ${priorityStr}
DEPENDENCIES: ${depsStr}
DESCRIPTION: ${phase.description}

Requirements:
1. Break down into 3-8 sub-phases
2. Each sub-phase should be 15-60 minutes maximum
3. Create logical dependency chains
4. Include parallel execution opportunities
5. Provide specific deliverables for each sub-phase
6. Create execution plan with critical path and milestones
7. Set breakdown_complete: true

Output format: JSON dengan struktur seperti contoh yang ada (lihat file .ai/plan/1.1.json untuk referensi)`;
    }

    /**
     * Panggil AI menggunakan Claude Agent SDK
     */
    async callAI(prompt, outputPath) {
        try {
            const { query } = require('@anthropic-ai/claude-agent-sdk');

            logger.info('Calling AI for breakdown generation...');

            const result = await query({
                prompt: prompt,
                options: {
                    systemPrompt: { type: "preset", preset: "claude_code" },
                    settingSources: ["user", "project", "local"]
                }
            });

            let output = '';

            // Process the response
            if (result) {
                try {
                    // Handle streaming response (async iterator)
                    if (typeof result[Symbol.asyncIterator] === 'function') {
                        for await (const message of result) {
                            if (typeof message === 'string') {
                                output += message;
                            } else if (message && message.content) {
                                output += message.content;
                            } else if (message && typeof message === 'object') {
                                output += JSON.stringify(message);
                            }
                        }
                    }
                    // Handle response with content property
                    else if (result.content) {
                        output = result.content;
                    }
                    // Handle plain string response
                    else if (typeof result === 'string') {
                        output = result;
                    }
                    // Handle object response (convert to string)
                    else if (typeof result === 'object') {
                        output = JSON.stringify(result);
                    }
                    else {
                        throw new Error('Unknown response format from Claude Agent SDK');
                    }
                } catch (processingError) {
                    logger.error(`Error processing SDK response: ${processingError.message}`);
                    throw new Error(`Response processing error: ${processingError.message}`);
                }
            } else {
                throw new Error('Empty response from Claude Agent SDK');
            }

            // Extract JSON from the output
            const jsonMatch = output.match(/```json\s*([\s\S]*?)\s*```/) || output.match(/\{[\s\S]*\}/);
            if (!jsonMatch) {
                throw new Error('No JSON found in AI response');
            }

            const jsonStr = jsonMatch[1] || jsonMatch[0];
            const jsonData = JSON.parse(jsonStr);

            return {
                success: true,
                data: jsonData
            };

        } catch (error) {
            logger.error(`AI call failed: ${error.message}`);
            return {
                success: false,
                error: error.message
            };
        }
    }

    /**
     * Update phase tasks file
     */
    async updatePhaseTasks(phaseId, tasksData) {
        try {
            const tasksPath = path.join(this.planDir, `${phaseId}.json`);

            // Validate data sebelum save
            const validation = validatePhaseData(tasksData);
            if (!validation.valid) {
                throw new Error(`Invalid phase data: ${validation.errors.join(', ')}`);
            }

            await writeJsonFile(tasksPath, tasksData);
            logger.info(`Updated tasks file: ${tasksPath}`);

            // Save ke output juga sebagai backup
            const outputPath = path.join(this.outputDir, `${phaseId}.json`);
            await ensureDir(this.outputDir);
            await writeJsonFile(outputPath, tasksData);
            logger.info(`Saved to output: ${outputPath}`);

        } catch (error) {
            logger.error(`Failed to update phase ${phaseId} tasks:`, error);
            throw error;
        }
    }

    /**
     * Proses satu phase
     */
    async processPhase(phase) {
        const phaseId = phase.id.toString();

        // Skip jika sudah completed
        if (state.completedPhases.has(phaseId)) {
            logger.info(`⏭️  Phase ${phaseId} already completed, skipping`);
            return true;
        }

        logger.info(`🔄 Processing phase ${phaseId}: ${phase.title}`);

        try {
            // Baca tasks yang ada
            const tasksData = await this.readTasksJson(phaseId);

            // Cek apakah perlu breakdown
            if (this.shouldBreakdown(phase, tasksData)) {
                // Generate tasks baru
                const success = await this.generateTasksForPhase(phase);
                if (success) {
                    logger.info(`✅ Phase ${phaseId} completed successfully`);
                    return true;
                } else {
                    logger.error(`❌ Phase ${phaseId} failed`);
                    return false;
                }
            } else {
                // Tidak perlu breakdown, mark as completed
                state.completedPhases.add(phaseId);
                logger.info(`✅ Phase ${phaseId} doesn't need breakdown, marked as completed`);
                return true;
            }
        } catch (error) {
            logger.error(`❌ Error processing phase ${phaseId}:`, error);
            state.failedPhases.add(phaseId);
            return false;
        }
    }

    /**
     * Main loop untuk breakdown semua phases
     */
    async breakdownAllPhases() {
        try {
            await ensureDir(this.outputDir);
            await this.loadLoopState();

            // Baca plan
            const planData = await this.readPlanJson();
            const phases = planData.phases;

            logger.info(`🚀 Starting breakdown loop for ${phases.length} phases`);
            logger.info(`📊 Current state: ${state.completedPhases.size} completed, ${state.failedPhases.size} failed`);

            let allComplete = true;
            let processedInThisIteration = 0;

            // Proses semua phases
            for (const phase of phases) {
                if (!state.completedPhases.has(phase.id.toString())) {
                    allComplete = false;
                    const success = await this.processPhase(phase);
                    if (success) {
                        processedInThisIteration++;
                    }

                    // Save state setelah setiap phase
                    await this.saveLoopState();
                }
            }

            state.currentIteration++;

            if (allComplete) {
                logger.info(`🎉 All phases completed! Total iterations: ${state.currentIteration}`);
                await this.resetLoopState();
                return true;
            } else {
                logger.info(`📈 Iteration ${state.currentIteration} complete. Processed ${processedInThisIteration} phases.`);
                logger.info(`📊 Status: ${state.completedPhases.size}/${phases.length} phases completed`);

                if (state.currentIteration >= state.maxIterations) {
                    logger.error(`🛑 Maximum iterations (${state.maxIterations}) reached`);
                    return false;
                }

                // Continue loop
                return await this.breakdownAllPhases();
            }

        } catch (error) {
            logger.error('💥 Error in breakdown loop:', error);
            await this.saveLoopState();
            throw error;
        }
    }

    /**
     * Get status summary
     */
    getStatusSummary() {
        return {
            completed: state.completedPhases.size,
            failed: state.failedPhases.size,
            iteration: state.currentIteration,
            completedPhases: Array.from(state.completedPhases),
            failedPhases: Array.from(state.failedPhases)
        };
    }
}

/**
 * Main execution
 */
async function main() {
    const analyzer = new PlanBreakdownAnalyzer();

    try {
        console.log(chalk.blue.bold('🔨 Enhanced Plan Breakdown Analyzer with Loop Tracking'));
        console.log(chalk.gray('==================================================='));

        // Check for reset flag
        const args = process.argv.slice(2);
        if (args.includes('--reset')) {
            console.log(chalk.yellow('🔄 Resetting loop state...'));
            await analyzer.resetLoopState();
        }

        if (args.includes('--status')) {
            await analyzer.loadLoopState();
            const status = analyzer.getStatusSummary();
            console.log(chalk.cyan('📊 Current Status:'));
            console.log(`  Completed: ${status.completed} phases`);
            console.log(`  Failed: ${status.failed} phases`);
            console.log(`  Iteration: ${status.iteration}`);
            if (status.completedPhases.length > 0) {
                console.log(`  Completed phases: ${status.completedPhases.join(', ')}`);
            }
            if (status.failedPhases.length > 0) {
                console.log(`  Failed phases: ${status.failedPhases.join(', ')}`);
            }
            return;
        }

        // Run breakdown loop
        const success = await analyzer.breakdownAllPhases();

        if (success) {
            console.log(chalk.green.bold('✅ Breakdown completed successfully!'));
            process.exit(0);
        } else {
            console.log(chalk.red.bold('❌ Breakdown failed!'));
            process.exit(1);
        }

    } catch (error) {
        console.error(chalk.red.bold('💥 Fatal error:'), error);
        process.exit(1);
    }
}

// Run if called directly
if (require.main === module) {
    main().catch(console.error);
}

module.exports = PlanBreakdownAnalyzer;