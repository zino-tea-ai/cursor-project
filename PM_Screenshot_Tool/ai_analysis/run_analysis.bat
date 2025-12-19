@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   AI Screenshot Analysis Tool
echo   AI截图分析工具
echo ============================================================
echo.

:: 检查API Key
if "%ANTHROPIC_API_KEY%"=="" (
    echo [Warning] ANTHROPIC_API_KEY not set
    echo.
    echo Please enter your Anthropic API Key:
    echo (Get it from: https://console.anthropic.com/)
    echo.
    set /p API_KEY=API Key: 
    set ANTHROPIC_API_KEY=!API_KEY!
)

:: 显示项目列表
echo.
echo Available projects:
echo -------------------
python batch_ai_analyze.py --status

echo.
echo Options:
echo   1. Analyze a specific project
echo   2. Analyze all projects
echo   3. View project status
echo   4. Exit
echo.
set /p choice=Select (1-4): 

if "%choice%"=="1" (
    echo.
    set /p project_name=Enter project name: 
    echo.
    echo Starting analysis for !project_name!...
    python batch_ai_analyze.py --project !project_name!
) else if "%choice%"=="2" (
    echo.
    echo Starting analysis for all projects...
    python batch_ai_analyze.py --all
) else if "%choice%"=="3" (
    python batch_ai_analyze.py --status
) else (
    echo Exiting...
    exit /b 0
)

echo.
echo ============================================================
echo   Analysis complete!
echo ============================================================
pause




chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   AI Screenshot Analysis Tool
echo   AI截图分析工具
echo ============================================================
echo.

:: 检查API Key
if "%ANTHROPIC_API_KEY%"=="" (
    echo [Warning] ANTHROPIC_API_KEY not set
    echo.
    echo Please enter your Anthropic API Key:
    echo (Get it from: https://console.anthropic.com/)
    echo.
    set /p API_KEY=API Key: 
    set ANTHROPIC_API_KEY=!API_KEY!
)

:: 显示项目列表
echo.
echo Available projects:
echo -------------------
python batch_ai_analyze.py --status

echo.
echo Options:
echo   1. Analyze a specific project
echo   2. Analyze all projects
echo   3. View project status
echo   4. Exit
echo.
set /p choice=Select (1-4): 

if "%choice%"=="1" (
    echo.
    set /p project_name=Enter project name: 
    echo.
    echo Starting analysis for !project_name!...
    python batch_ai_analyze.py --project !project_name!
) else if "%choice%"=="2" (
    echo.
    echo Starting analysis for all projects...
    python batch_ai_analyze.py --all
) else if "%choice%"=="3" (
    python batch_ai_analyze.py --status
) else (
    echo Exiting...
    exit /b 0
)

echo.
echo ============================================================
echo   Analysis complete!
echo ============================================================
pause




chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   AI Screenshot Analysis Tool
echo   AI截图分析工具
echo ============================================================
echo.

:: 检查API Key
if "%ANTHROPIC_API_KEY%"=="" (
    echo [Warning] ANTHROPIC_API_KEY not set
    echo.
    echo Please enter your Anthropic API Key:
    echo (Get it from: https://console.anthropic.com/)
    echo.
    set /p API_KEY=API Key: 
    set ANTHROPIC_API_KEY=!API_KEY!
)

:: 显示项目列表
echo.
echo Available projects:
echo -------------------
python batch_ai_analyze.py --status

echo.
echo Options:
echo   1. Analyze a specific project
echo   2. Analyze all projects
echo   3. View project status
echo   4. Exit
echo.
set /p choice=Select (1-4): 

if "%choice%"=="1" (
    echo.
    set /p project_name=Enter project name: 
    echo.
    echo Starting analysis for !project_name!...
    python batch_ai_analyze.py --project !project_name!
) else if "%choice%"=="2" (
    echo.
    echo Starting analysis for all projects...
    python batch_ai_analyze.py --all
) else if "%choice%"=="3" (
    python batch_ai_analyze.py --status
) else (
    echo Exiting...
    exit /b 0
)

echo.
echo ============================================================
echo   Analysis complete!
echo ============================================================
pause




chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   AI Screenshot Analysis Tool
echo   AI截图分析工具
echo ============================================================
echo.

:: 检查API Key
if "%ANTHROPIC_API_KEY%"=="" (
    echo [Warning] ANTHROPIC_API_KEY not set
    echo.
    echo Please enter your Anthropic API Key:
    echo (Get it from: https://console.anthropic.com/)
    echo.
    set /p API_KEY=API Key: 
    set ANTHROPIC_API_KEY=!API_KEY!
)

:: 显示项目列表
echo.
echo Available projects:
echo -------------------
python batch_ai_analyze.py --status

echo.
echo Options:
echo   1. Analyze a specific project
echo   2. Analyze all projects
echo   3. View project status
echo   4. Exit
echo.
set /p choice=Select (1-4): 

if "%choice%"=="1" (
    echo.
    set /p project_name=Enter project name: 
    echo.
    echo Starting analysis for !project_name!...
    python batch_ai_analyze.py --project !project_name!
) else if "%choice%"=="2" (
    echo.
    echo Starting analysis for all projects...
    python batch_ai_analyze.py --all
) else if "%choice%"=="3" (
    python batch_ai_analyze.py --status
) else (
    echo Exiting...
    exit /b 0
)

echo.
echo ============================================================
echo   Analysis complete!
echo ============================================================
pause





chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   AI Screenshot Analysis Tool
echo   AI截图分析工具
echo ============================================================
echo.

:: 检查API Key
if "%ANTHROPIC_API_KEY%"=="" (
    echo [Warning] ANTHROPIC_API_KEY not set
    echo.
    echo Please enter your Anthropic API Key:
    echo (Get it from: https://console.anthropic.com/)
    echo.
    set /p API_KEY=API Key: 
    set ANTHROPIC_API_KEY=!API_KEY!
)

:: 显示项目列表
echo.
echo Available projects:
echo -------------------
python batch_ai_analyze.py --status

echo.
echo Options:
echo   1. Analyze a specific project
echo   2. Analyze all projects
echo   3. View project status
echo   4. Exit
echo.
set /p choice=Select (1-4): 

if "%choice%"=="1" (
    echo.
    set /p project_name=Enter project name: 
    echo.
    echo Starting analysis for !project_name!...
    python batch_ai_analyze.py --project !project_name!
) else if "%choice%"=="2" (
    echo.
    echo Starting analysis for all projects...
    python batch_ai_analyze.py --all
) else if "%choice%"=="3" (
    python batch_ai_analyze.py --status
) else (
    echo Exiting...
    exit /b 0
)

echo.
echo ============================================================
echo   Analysis complete!
echo ============================================================
pause




chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ============================================================
echo   AI Screenshot Analysis Tool
echo   AI截图分析工具
echo ============================================================
echo.

:: 检查API Key
if "%ANTHROPIC_API_KEY%"=="" (
    echo [Warning] ANTHROPIC_API_KEY not set
    echo.
    echo Please enter your Anthropic API Key:
    echo (Get it from: https://console.anthropic.com/)
    echo.
    set /p API_KEY=API Key: 
    set ANTHROPIC_API_KEY=!API_KEY!
)

:: 显示项目列表
echo.
echo Available projects:
echo -------------------
python batch_ai_analyze.py --status

echo.
echo Options:
echo   1. Analyze a specific project
echo   2. Analyze all projects
echo   3. View project status
echo   4. Exit
echo.
set /p choice=Select (1-4): 

if "%choice%"=="1" (
    echo.
    set /p project_name=Enter project name: 
    echo.
    echo Starting analysis for !project_name!...
    python batch_ai_analyze.py --project !project_name!
) else if "%choice%"=="2" (
    echo.
    echo Starting analysis for all projects...
    python batch_ai_analyze.py --all
) else if "%choice%"=="3" (
    python batch_ai_analyze.py --status
) else (
    echo Exiting...
    exit /b 0
)

echo.
echo ============================================================
echo   Analysis complete!
echo ============================================================
pause












































