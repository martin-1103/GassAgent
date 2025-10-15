#!/usr/bin/env node

/**
 * Headless Claude Code Runner - Node.js Version
 * More reliable alternative to batch script
 */

const { execSync, spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Get script directory and project root
const scriptDir = __dirname;
const projectRoot = path.resolve(scriptDir, '../..');

// Claude CLI path
const claudeCliPath = 'D:\\coder\\npm-global\\claude.cmd';

function main() {
    // Get arguments
    const args = process.argv.slice(2);

    if (args.length === 0) {
        console.error('Error: No prompt provided.');
        console.error('');
        console.error('Usage: node run_claude.js "Your prompt here"');
        console.error('Example: node run_claude.js "Create file test.txt with hello world"');
        process.exit(1);
    }

    const prompt = args.join(' ');

    // Verify project root exists
    if (!fs.existsSync(projectRoot)) {
        console.error(`Error: Project root not found: ${projectRoot}`);
        process.exit(1);
    }

    // Check if Claude CLI exists
    if (!fs.existsSync(claudeCliPath)) {
        console.error(`Error: Claude CLI not found at: ${claudeCliPath}`);
        console.error('Please check your Claude installation path.');
        process.exit(1);
    }

    console.log(`Running Claude Code from project root: ${projectRoot}`);
    console.log(`Task: ${prompt}`);
    console.log('');

    try {
        // Change to project root
        process.chdir(projectRoot);

        // Prepare command
        const command = `"${claudeCliPath}" -p "${prompt}" --output-format json --allowedTools "Write,Read,Bash,Task,Edit,Glob,Grep" --permission-mode acceptEdits`;

        // Execute Claude
        const result = execSync(command, {
            encoding: 'utf8',
            stdio: ['inherit', 'pipe', 'pipe'],
            cwd: projectRoot
        });

        console.log(result);
        console.log('Task completed successfully.');

    } catch (error) {
        console.error(`Error: Claude execution failed with exit code: ${error.status}`);
        console.error(error.stderr || error.stdout || error.message);
        process.exit(error.status || 1);
    }
}

// Run main function
main();