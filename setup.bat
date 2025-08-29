@echo off
REM Setup script for Asset Management System

echo Setting up Python virtual environment...
python -m venv venv

if not exist "venv\Scripts\activate" (
    echo Error: Failed to create virtual environment
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to activate virtual environment
    pause
    exit /b 1
)

echo Upgrading pip...
python -m pip install --upgrade pip
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to upgrade pip
    pause
    exit /b 1
)

echo Installing project dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Setup completed successfully!
echo Virtual environment: %CD%\venv
echo To activate the environment, run: call venv\Scripts\activate.bat
pause
