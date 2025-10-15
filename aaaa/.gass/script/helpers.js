/**
 * Helper functions for run-tasks.js
 */

const { spawn } = require('child_process');
const path = require('path');
const { query } = require('@anthropic-ai/claude-agent-sdk');

function parseTaskOutput(output) {
    const tasks = [];
    const lines = output.split('\n');

    for (const line of lines) {
        const taskMatch = line.match(/(?:Task|📋|Phase)([^:]+):?\s*(.+)/);
        if (taskMatch) {
            const [, type, description] = taskMatch;

            const phaseMatch = line.match(/(\d+(?:\.\d+)?)\b/);
            const phaseId = phaseMatch ? phaseMatch[1] : 'unknown';

            const priorityMatch = line.match(/priority[:\s]+(\d+)/i);
            const priority = priorityMatch ? parseInt(priorityMatch[1]) : 999;

            if (description && description.trim() && !description.includes('No tasks')) {
                tasks.push({
                    id: tasks.length + 1,
                    phaseId,
                    description: description.trim(),
                    priority,
                    status: 'pending',
                    dependencies: 'completed'
                });
            }
        }
    }

    return tasks;
}

function executeCommand(projectRoot, command, args = []) {
    return new Promise((resolve, reject) => {
        const child = spawn(command, args, {
            cwd: projectRoot,
            stdio: ['pipe', 'pipe', 'pipe'],
            shell: true
        });

        let stdout = '';
        let stderr = '';

        child.stdout.on('data', (data) => {
            stdout += data.toString();
        });

        child.stderr.on('data', (data) => {
            stderr += data.toString();
        });

        child.on('close', (code) => {
            resolve({ stdout, stderr, code });
        });

        child.on('error', (error) => {
            reject(error);
        });
    });
}

function updateTaskStatus(scriptDir, projectRoot, phaseId, status) {
    return new Promise((resolve) => {
        const scriptPath = path.join(scriptDir, 'update-phase-status.js');
        const child = spawn('node', [scriptPath, '--status', status, '--phase', phaseId], {
            cwd: projectRoot,
            stdio: ['pipe', 'pipe', 'pipe']
        });

        let stdout = '';
        let stderr = '';

        child.stdout.on('data', (data) => stdout += data.toString());
        child.stderr.on('data', (data) => stderr += data.toString());

        child.on('close', (code) => {
            if (code !== 0) {
                console.warn(`⚠️  Warning: Failed to update status for phase ${phaseId}: ${stderr}`);
            } else {
                console.log(`✅ Updated phase ${phaseId} status to ${status}`);
            }
            resolve();
        });
    });
}

async function runClaudeTask(scriptDir, projectRoot, task, onProgress = null) {
    console.log(`🚀 Starting Task ${task.id}: ${task.description.substring(0, 50)}...`);

    try {
        const prompt = `Dengan konteks project structure dan database schema, kerjakan task berikut: ${task.description} - Priority: ${task.priority} - Phase: ${task.phaseId} - Status: ${task.status} - Dependencies: ${task.dependencies}. RULE: Hasil file tidak boleh lebih dari 300 lines. Jika lebih, break menjadi submodule/helper dengan penamaan yang AI-friendly (contoh: authentication.validator.js, authentication.service.js) dan struktur folder yang logical. AI-friendly purposes: validator, service, helper, controller, middleware, utility, handler, processor, manager, builder.`;

        let stdout = '';
        let stderr = '';

        try {
            // Use Claude Agent SDK with Claude Code preset for backward compatibility
            const result = await query({
                prompt: prompt,
                options: {
                    systemPrompt: { type: "preset", preset: "claude_code" },
                    settingSources: ["user", "project", "local"]
                }
            });

            // Process the response - handle multiple response formats
            if (result) {
                try {
                    // Handle streaming response (async iterator)
                    if (typeof result[Symbol.asyncIterator] === 'function') {
                        for await (const message of result) {
                            if (typeof message === 'string') {
                                stdout += message;
                                if (onProgress) onProgress('stdout', message);
                            } else if (message && message.content) {
                                stdout += message.content;
                                if (onProgress) onProgress('stdout', message.content);
                            } else if (message && typeof message === 'object') {
                                // Handle object messages
                                const content = JSON.stringify(message);
                                stdout += content;
                                if (onProgress) onProgress('stdout', content);
                            }
                        }
                    }
                    // Handle response with content property
                    else if (result.content) {
                        stdout = result.content;
                        if (onProgress) onProgress('stdout', stdout);
                    }
                    // Handle plain string response
                    else if (typeof result === 'string') {
                        stdout = result;
                        if (onProgress) onProgress('stdout', stdout);
                    }
                    // Handle object response (convert to string)
                    else if (typeof result === 'object') {
                        stdout = JSON.stringify(result);
                        if (onProgress) onProgress('stdout', stdout);
                    }
                    else {
                        throw new Error('Unknown response format from Claude Agent SDK');
                    }
                } catch (processingError) {
                    console.error(`Error processing SDK response: ${processingError.message}`);
                    throw new Error(`Response processing error: ${processingError.message}`);
                }
            } else {
                throw new Error('Empty response from Claude Agent SDK');
            }

            const taskResult = {
                task,
                success: true,
                output: stdout,
                error: stderr,
                validationPassed: false
            };

            console.log(`🏁 Task ${task.id} execution completed`);

            // Run validation
            try {
                const validation = await runValidation(scriptDir, projectRoot, task);
                taskResult.validationPassed = validation.passed;
                taskResult.validationFeedback = validation.feedback;

                if (validation.passed) {
                    await updateTaskStatus(scriptDir, projectRoot, task.phaseId, 'completed');
                    console.log(`✅ Task ${task.id} validated and marked as completed`);
                } else {
                    console.log(`⚠️  Task ${task.id} needs revisions based on validation`);
                    taskResult.validationOutput = validation.output;
                }
            } catch (error) {
                console.warn(`⚠️  Validation failed for task ${task.id}: ${error.message}`);
            }

            return taskResult;

        } catch (sdkError) {
            console.error(`❌ Claude Agent SDK error for task ${task.id}:`, sdkError.message);

            // Fallback to batch file if SDK fails
            try {
                console.log(`🔄 Falling back to batch file for task ${task.id}...`);
                return await runClaudeTaskFallback(scriptDir, projectRoot, task, onProgress);
            } catch (fallbackError) {
                return {
                    task,
                    success: false,
                    error: `SDK Error: ${sdkError.message}, Fallback Error: ${fallbackError.message}`,
                    validationPassed: false
                };
            }
        }

    } catch (error) {
        console.log(`❌ Task ${task.id} failed to start: ${error.message}`);
        return {
            task,
            success: false,
            error: error.message,
            validationPassed: false
        };
    }
}

async function runValidation(scriptDir, projectRoot, task) {
    try {
        const prompt = `Review dan validasi hasil task ${task.description}. Bandingkan dengan requirements awal di phase ${task.phaseId}. Cek: apa yang kurang, apa yang berlebihan, ada error/tidak. Jika kurang → tambahkan, jika berlebihan → kurangi, jika error → perbaiki. Reference: Berdasarkan .ai\\structure\\structure.md dan .ai\\schemas\\index.json. Validation checklist: Requirements compliance, Code quality (max 300 lines), Structure compliance, Completeness, Integration compatibility, Best practices (AI-friendly naming).`;

        let stdout = '';
        let stderr = '';

        try {
            // Use Claude Agent SDK with Claude Code preset for validation
            const result = await query({
                prompt: prompt,
                options: {
                    systemPrompt: { type: "preset", preset: "claude_code" },
                    settingSources: ["user", "project", "local"]
                }
            });

            // Process the response - handle multiple response formats
            if (result) {
                try {
                    // Handle streaming response (async iterator)
                    if (typeof result[Symbol.asyncIterator] === 'function') {
                        for await (const message of result) {
                            if (typeof message === 'string') {
                                stdout += message;
                            } else if (message && message.content) {
                                stdout += message.content;
                            } else if (message && typeof message === 'object') {
                                // Handle object messages
                                stdout += JSON.stringify(message);
                            }
                        }
                    }
                    // Handle response with content property
                    else if (result.content) {
                        stdout = result.content;
                    }
                    // Handle plain string response
                    else if (typeof result === 'string') {
                        stdout = result;
                    }
                    // Handle object response (convert to string)
                    else if (typeof result === 'object') {
                        stdout = JSON.stringify(result);
                    }
                    else {
                        throw new Error('Unknown response format from Claude Agent SDK');
                    }
                } catch (processingError) {
                    console.error(`Error processing SDK validation response: ${processingError.message}`);
                    throw new Error(`Validation response processing error: ${processingError.message}`);
                }
            } else {
                throw new Error('Empty response from Claude Agent SDK');
            }

            const passed = stdout.toLowerCase().includes('valid') ||
                stdout.toLowerCase().includes('complete') ||
                stdout.toLowerCase().includes('success') ||
                (!stdout.toLowerCase().includes('error') &&
                 !stdout.toLowerCase().includes('missing') &&
                 !stdout.toLowerCase().includes('perlu'));

            return {
                passed,
                feedback: stdout,
                output: stdout,
                error: stderr
            };

        } catch (sdkError) {
            console.error(`❌ Claude Agent SDK validation error:`, sdkError.message);

            // Fallback to batch file if SDK fails
            try {
                console.log(`🔄 Falling back to batch file for validation...`);
                return await runValidationFallback(scriptDir, projectRoot, task);
            } catch (fallbackError) {
                return {
                    passed: false,
                    feedback: `SDK Error: ${sdkError.message}, Fallback Error: ${fallbackError.message}`,
                    error: fallbackError.message
                };
            }
        }

    } catch (error) {
        return {
            passed: false,
            feedback: `Validation error: ${error.message}`,
            error: error.message
        };
    }
}

function runClaudeTaskFallback(scriptDir, projectRoot, task, onProgress = null) {
    return new Promise((resolve) => {
        const batchPath = path.join(scriptDir, 'run_claude.bat');
        const prompt = `Dengan konteks project structure dan database schema, kerjakan task berikut: ${task.description} - Priority: ${task.priority} - Phase: ${task.phaseId} - Status: ${task.status} - Dependencies: ${task.dependencies}. RULE: Hasil file tidak boleh lebih dari 300 lines. Jika lebih, break menjadi submodule/helper dengan penamaan yang AI-friendly (contoh: authentication.validator.js, authentication.service.js) dan struktur folder yang logical. AI-friendly purposes: validator, service, helper, controller, middleware, utility, handler, processor, manager, builder.`;
        const command = `cmd /c cd /d "${projectRoot}" && "${batchPath}" "${prompt}"`;

        const child = spawn('cmd', ['/c', command], {
            stdio: ['pipe', 'pipe', 'pipe'],
            shell: true
        });

        let stdout = '';
        let stderr = '';

        child.stdout.on('data', (data) => {
            stdout += data.toString();
            if (onProgress) onProgress('stdout', data.toString());
        });

        child.stderr.on('data', (data) => {
            stderr += data.toString();
            if (onProgress) onProgress('stderr', data.toString());
        });

        child.on('close', async (code) => {
            const result = {
                task,
                success: code === 0,
                output: stdout,
                error: stderr,
                validationPassed: false,
                usedFallback: true
            };

            console.log(`🏁 Task ${task.id} fallback execution completed`);

            if (result.success) {
                try {
                    const validation = await runValidation(scriptDir, projectRoot, task);
                    result.validationPassed = validation.passed;
                    result.validationFeedback = validation.feedback;

                    if (validation.passed) {
                        await updateTaskStatus(scriptDir, projectRoot, task.phaseId, 'completed');
                        console.log(`✅ Task ${task.id} validated and marked as completed`);
                    } else {
                        console.log(`⚠️  Task ${task.id} needs revisions based on validation`);
                        result.validationOutput = validation.output;
                    }
                } catch (error) {
                    console.warn(`⚠️  Validation failed for task ${task.id}: ${error.message}`);
                }
            } else {
                console.log(`❌ Task ${task.id} fallback failed with code ${code}`);
                if (stderr) {
                    console.log(`   Error: ${stderr.trim()}`);
                }
            }

            resolve(result);
        });

        child.on('error', (error) => {
            console.log(`❌ Task ${task.id} fallback failed to start: ${error.message}`);
            resolve({
                task,
                success: false,
                error: `Fallback Error: ${error.message}`,
                validationPassed: false,
                usedFallback: true
            });
        });
    });
}

function runValidationFallback(scriptDir, projectRoot, task) {
    const batchPath = path.join(scriptDir, 'run_claude.bat');
    const prompt = `Review dan validasi hasil task ${task.description}. Bandingkan dengan requirements awal di phase ${task.phaseId}. Cek: apa yang kurang, apa yang berlebihan, ada error/tidak. Jika kurang → tambahkan, jika berlebihan → kurangi, jika error → perbaiki. Reference: Berdasarkan .ai\\structure\\structure.md dan .ai\\schemas\\index.json. Validation checklist: Requirements compliance, Code quality (max 300 lines), Structure compliance, Completeness, Integration compatibility, Best practices (AI-friendly naming).`;
    const command = `cmd /c cd /d "${projectRoot}" && "${batchPath}" "${prompt}"`;

    return executeCommand(projectRoot, 'cmd', ['/c', command])
        .then(({ stdout, stderr, code }) => {
            const passed = code === 0 && (
                stdout.toLowerCase().includes('valid') ||
                stdout.toLowerCase().includes('complete') ||
                stdout.toLowerCase().includes('success') ||
                !stdout.toLowerCase().includes('error') &&
                !stdout.toLowerCase().includes('missing') &&
                !stdout.toLowerCase().includes('perlu')
            );

            return {
                passed,
                feedback: stdout,
                output: stdout,
                error: stderr,
                usedFallback: true
            };
        })
        .catch(error => ({
            passed: false,
            feedback: `Fallback validation error: ${error.message}`,
            error: error.message,
            usedFallback: true
        }));
}

function filterTasks(tasks, filter) {
    if (!filter || filter.trim() === '') {
        return tasks;
    }

    const filterLower = filter.toLowerCase();
    return tasks.filter(task =>
        task.description.toLowerCase().includes(filterLower) ||
        task.phaseId.includes(filter)
    );
}


function displaySummary(results, totalTasks, startTime) {
    const endTime = Date.now();
    const duration = ((endTime - startTime) / 1000).toFixed(2);

    console.log('\n' + '='.repeat(70));
    console.log('📊 EXECUTION SUMMARY');
    console.log('='.repeat(70));
    console.log(`Total tasks: ${totalTasks}`);
    console.log(`Successful execution: ${results.filter(r => r.success).length}`);
    console.log(`Failed execution: ${results.filter(r => !r.success).length}`);
    console.log(`Validation passed: ${results.filter(r => r.validationPassed).length}`);
    console.log(`Validation failed: ${results.filter(r => !r.validationPassed && r.success).length}`);
    console.log(`Duration: ${duration} seconds`);

    const failedTasks = results.filter(r => !r.success);
    if (failedTasks.length > 0) {
        console.log('\n❌ FAILED TASKS:');
        failedTasks.forEach(result => {
            console.log(`   Task ${result.task.id}: ${result.error || 'Unknown error'}`);
        });
    }

    const validationFailed = results.filter(r => r.success && !r.validationPassed);
    if (validationFailed.length > 0) {
        console.log('\n⚠️  TASKS NEEDING REVISION:');
        validationFailed.forEach(result => {
            console.log(`   Task ${result.task.id}: ${result.task.description.substring(0, 50)}...`);
        });
    }

    console.log('='.repeat(70));
}

// Additional helper functions for plan-breakdown-analyzer.js
const fs = require('fs').promises;

async function readJsonFile(filePath) {
    try {
        // Jika filePath relatif, cari di beberapa lokasi
        if (!path.isAbsolute(filePath)) {
            // Determine project root
            let projectRoot = process.cwd();
            if (projectRoot.endsWith('script')) {
                projectRoot = path.dirname(projectRoot);
            }

            const possiblePaths = [
                path.join(projectRoot, '.ai/plan', filePath),
                path.join(projectRoot, '.ai', filePath),
                path.join(projectRoot, filePath),
                path.resolve(process.cwd(), '.ai/plan', filePath),
                path.resolve(process.cwd(), '.ai', filePath),
                path.resolve(process.cwd(), filePath)
            ];

            for (const fullPath of possiblePaths) {
                if (await fileExists(fullPath)) {
                    const content = await fs.readFile(fullPath, 'utf8');
                    return JSON.parse(content);
                }
            }

            // Coba dengan ekstensi .json jika tidak ada
            for (const fullPath of possiblePaths) {
                const withJson = fullPath.endsWith('.json') ? fullPath : `${fullPath}.json`;
                if (await fileExists(withJson)) {
                    const content = await fs.readFile(withJson, 'utf8');
                    return JSON.parse(content);
                }
            }

            throw new Error(`File tidak ditemukan di path: ${filePath}`);
        } else {
            // Jika path absolute, gunakan langsung
            if (!(await fileExists(filePath))) {
                throw new Error(`File tidak ditemukan: ${filePath}`);
            }
            const content = await fs.readFile(filePath, 'utf8');
            return JSON.parse(content);
        }
    } catch (error) {
        console.error(`Gagal membaca file JSON ${filePath}:`, error);
        throw error;
    }
}

async function writeJsonFile(filePath, data) {
    try {
        const content = JSON.stringify(data, null, 2);
        await fs.writeFile(filePath, content, 'utf8');
    } catch (error) {
        console.error(`Gagal menulis file JSON ${filePath}:`, error);
        throw error;
    }
}

async function ensureDir(dirPath) {
    try {
        await fs.mkdir(dirPath, { recursive: true });
    } catch (error) {
        console.error(`Gagal membuat directory ${dirPath}:`, error);
        throw error;
    }
}

async function fileExists(filePath) {
    try {
        await fs.access(filePath);
        return true;
    } catch {
        return false;
    }
}

function parseDuration(durationStr) {
    if (!durationStr) return 0;

    // Handle formats like "2-3 days", "4-6 weeks", "1 week", "30 minutes"
    const match = durationStr.match(/(\d+)-(\d+)\s*(hour|day|week|minute|min)s?/i);
    if (match) {
        // Return the average duration in minutes
        const [, min, max, unit] = match;
        const avg = (parseInt(min) + parseInt(max)) / 2;

        switch (unit.toLowerCase()) {
            case 'minute':
            case 'min':
                return avg;
            case 'hour':
                return avg * 60;
            case 'day':
                return avg * 8 * 60; // 8 hours per day
            case 'week':
                return avg * 5 * 8 * 60; // 5 days per week
            default:
                return avg;
        }
    }

    // Handle single value like "1 week", "2 hours", "30 minutes"
    const singleMatch = durationStr.match(/(\d+)\s*(hour|day|week|minute|min)s?/i);
    if (singleMatch) {
        const [, value, unit] = singleMatch;
        const num = parseInt(value);

        switch (unit.toLowerCase()) {
            case 'minute':
            case 'min':
                return num;
            case 'hour':
                return num * 60;
            case 'day':
                return num * 8 * 60;
            case 'week':
                return num * 5 * 8 * 60;
            default:
                return num;
        }
    }

    return 0;
}

function formatDuration(minutes) {
    if (minutes < 60) {
        return `${Math.round(minutes)} minutes`;
    } else if (minutes < 8 * 60) {
        return `${Math.round(minutes / 60)} hours`;
    } else {
        return `${Math.round(minutes / (8 * 60))} days`;
    }
}

function getPhaseDuration(phase) {
    return parseDuration(phase.duration || '');
}

function validatePhaseData(data) {
    const errors = [];

    if (!data.title || typeof data.title !== 'string') {
        errors.push('Missing or invalid title');
    }

    if (!data.description || typeof data.description !== 'string') {
        errors.push('Missing or invalid description');
    }

    if (!data.phases || !Array.isArray(data.phases)) {
        errors.push('Missing or invalid phases array');
    } else {
        data.phases.forEach((phase, index) => {
            if (!phase.id || !phase.title) {
                errors.push(`Invalid phase at index ${index}: missing id or title`);
            }
        });
    }

    if (data.execution_plan) {
        if (!data.execution_plan.parallel_groups || !Array.isArray(data.execution_plan.parallel_groups)) {
            errors.push('Invalid execution_plan: missing parallel_groups array');
        }

        if (!data.execution_plan.critical_path || !Array.isArray(data.execution_plan.critical_path)) {
            errors.push('Invalid execution_plan: missing critical_path array');
        }
    }

    return {
        valid: errors.length === 0,
        errors
    };
}

const logger = {
    info: (message) => console.log(`ℹ️  ${message}`),
    error: (message, error) => console.error(`❌ ${message}`, error || ''),
    warn: (message) => console.warn(`⚠️  ${message}`),
    debug: (message) => console.debug(`🐛 ${message}`)
};

module.exports = {
    parseTaskOutput,
    executeCommand,
    updateTaskStatus,
    runClaudeTask,
    runValidation,
    filterTasks,
    displaySummary,
    readJsonFile,
    writeJsonFile,
    ensureDir,
    fileExists,
    parseDuration,
    formatDuration,
    getPhaseDuration,
    validatePhaseData,
    logger
};