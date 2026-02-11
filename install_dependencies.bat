@echo off

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Python is not installed. Please install Python 3.8 or higher.
    pause
    exit /b 1
)

REM Check if pip is installed
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo pip is not installed. Please ensure pip is available with your Python installation.
    pause
    exit /b 1
)

REM Install dependencies from offline_packages
echo Installing Python dependencies from offline_packages...
pip install --no-index --find-links=offline_packages -r requirements.txt

if %errorlevel% neq 0 (
    echo Failed to install Python dependencies.
    pause
    exit /b 1
)

echo Python dependencies installed successfully.
pause
exit /b 0