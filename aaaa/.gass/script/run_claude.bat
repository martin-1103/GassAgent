@echo off
:: Headless Claude Code Runner - Robust Version
:: Located in .ai/script/ folder

:: Get script directory and project root with better path resolution
set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%\..\..
set PROJECT_ROOT=%PROJECT_ROOT:\\=\%

:: Normalize project root path
for %%i in ("%PROJECT_ROOT%") do set PROJECT_ROOT=%%~fi

:: Verify project root exists
if not exist "%PROJECT_ROOT%" (
    echo Error: Project root not found: %PROJECT_ROOT%
    exit /b 1
)

:: Change to project root
cd /d "%PROJECT_ROOT%"
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to change to project root: %PROJECT_ROOT%
    exit /b 1
)

:: Reject if no arguments provided
if "%~1"=="" (
    echo Error: No prompt provided.
    echo.
    echo Usage: run_claude.bat "Your prompt here"
    echo Example: run_claude.bat "Create file test.txt with hello world"
    exit /b 1
)

:: Check if Claude CLI exists
set CLAUDE_CLI="D:\coder\npm-global\claude.cmd"
if not exist %CLAUDE_CLI% (
    echo Error: Claude CLI not found at: %CLAUDE_CLI%
    echo Please check your Claude installation path.
    exit /b 1
)

echo Running Claude Code from project root: %PROJECT_ROOT%
echo Task: %*
echo.

:: Run Claude with context file and task
set PROMPT=%*
:: Add context reading instruction at the beginning
set ENHANCED_PROMPT=First, read the task context file mentioned in the prompt. If no file mentioned, look for .ai/brain/tasks/*.md files. Then execute the task following all instructions exactly. Task: %PROMPT%

%CLAUDE_CLI% -p "%ENHANCED_PROMPT%" --output-format json --allowedTools "Write,Read,Bash,Task,Edit,Glob,Grep" --permission-mode acceptEdits

:: Check exit code
if %ERRORLEVEL% NEQ 0 (
    echo Error: Claude execution failed with exit code: %ERRORLEVEL%
    exit /b %ERRORLEVEL%
)

echo Task completed successfully.