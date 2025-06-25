@echo off
setlocal enabledelayedexpansion

REM !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
REM  USED FOR TESTING, I.E. FOR DEVELOPING THIS PACKAGE; IF YOU WANT TO INSTALL THIS PACKAGE, JUST USE
REM  THE BASIC PIP INSTALLATION. USING THIS SCRIPT WILL LIKELY CAUSE YOU LOTS OF HEARTACHE AND .VENV
REM  TROUBLE.
REM
REM  TL;DR IF YOU DON'T KNOW WHAT YOU ARE DOING, DON'T RUN THIS. USE PIP.
REM !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

REM === CONFIGURATION ===
set "VENV_DIR=.venv-windows"
set "VENV_SCRIPTS=%VENV_DIR%\Scripts"
set "VENV_PYTHON=%VENV_SCRIPTS%\python.exe"
set "VENV_PIP=%VENV_SCRIPTS%\pip.exe"
set "VENV_PYTEST=%VENV_SCRIPTS%\pytest.exe"

REM === ENTRY POINT ===
call :reset
call :test
goto :eof

REM === Create virtual environment ===
:venv
if not exist "%VENV_PYTHON%" (
    echo Creating virtual environment in %VENV_DIR%...
    python -m venv %VENV_DIR%
    call "%VENV_PIP%" install --upgrade pip setuptools
)
goto :eof

REM === Clean build artifacts ===
:clean
echo Cleaning build artifacts...
rmdir /S /Q build 2>nul
rmdir /S /Q dist 2>nul

for /D %%D in (*.egg-info __pycache__ .pytest_cache) do (
    if exist "%%D" rmdir /S /Q "%%D"
)

REM Remove .pyd and .so recursively in src\
for /R src %%F in (*.pyd *.so) do (
    del /F /Q "%%F"
)
goto :eof

REM === Uninstall the package ===
:uninstall
call :venv
echo Uninstalling logngine...
call "%VENV_PIP%" uninstall -y logngine || echo (Already uninstalled)
goto :eof

REM === Run pre-build setup and pre-compilation file creation ===
:build
call "%VENV_PIP%" install tqdm numpy rtree
echo Creating pre-build files with build.py...
call "%VENV_PYTHON%" build.py
goto :eof

REM === Reinstall the package ===
:reinstall
call :venv
call :build
echo Installing logngine in editable mode with test extras...
call "%VENV_PIP%" install -e .[test,dev]
goto :eof

REM === Run tests ===
:test
call :venv
echo Running tests...
call "%VENV_PYTEST%" -v --tb=short --maxfail=5
goto :eof

REM === Reset (clean, uninstall, reinstall) ===
:reset
call :clean
call :uninstall
call :reinstall
goto :eof