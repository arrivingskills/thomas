@echo off
setlocal EnableDelayedExpansion

echo =======================================================
echo  Scanning for System Python Installations
echo  (Excluding Virtual Environments)
echo =======================================================
echo.

:: ---------------------------------------------------------
:: Method 1: The Official Python Launcher (py.exe)
:: ---------------------------------------------------------
where py >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo [Method: Python Launcher Registry]
    echo The 'py' launcher is installed. These versions are registered system-wide:
    echo.

    :: -0 lists available versions, p prints the full paths
    py --list-paths

    goto :Finish
)

:: ---------------------------------------------------------
:: Method 2: PATH Scanning + Heuristics
:: ---------------------------------------------------------
echo [Method: PATH Scanning]
echo Python Launcher not found. Scanning system PATH and filtering venvs...
echo.

set "found_any=0"

:: Loop through every 'python.exe' found in the PATH
for /f "tokens=*" %%A in ('where python 2^>nul') do (
    set "exe_path=%%A"
    set "dir_path=%%~dpA"

    :: Initialize heuristic flag
    set "is_venv=0"

    :: CHECK 1: Look for pyvenv.cfg in the same folder as python.exe
    if exist "!dir_path!pyvenv.cfg" set "is_venv=1"

    :: CHECK 2: Look for pyvenv.cfg in the parent folder (Common for 'Scripts' folder layout)
    if exist "!dir_path!..\pyvenv.cfg" set "is_venv=1"

    :: CHECK 3: Basic string check for common venv folder names in the path (Optional safety net)
    echo !exe_path! | findstr /I /C:"\venv\" >nul && set "is_venv=1"
    echo !exe_path! | findstr /I /C:"\.venv\" >nul && set "is_venv=1"

    if "!is_venv!"=="0" (
        echo [Found] !exe_path!
        :: Run the found python to get its precise version
        "!exe_path!" --version
        echo.
        set "found_any=1"
    )
)

if "!found_any!"=="0" (
    echo [!] No system Python versions found in PATH.
)

:Finish
echo.
echo =======================================================
pause