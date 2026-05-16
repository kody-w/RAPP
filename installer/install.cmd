@echo off
REM kody-w/RAPP - thin grail re-fetcher (Mirror Spec compliant)
REM
REM This repo mirrors the grail kernel at kody-w/rapp-installer.
REM The actual install logic lives in grail; this script re-fetches
REM grail's installer on every run.
REM
REM Mirror Spec: https://kody-w.github.io/RAPP/pages/vault/Architecture/Mirror%20Spec

echo.
echo   RAPP Brainstem Installer (mirror)
echo   =================================
echo.
echo   Re-fetching grail installer...
echo.

powershell -ExecutionPolicy Bypass -Command "& { irm https://raw.githubusercontent.com/kody-w/rapp-installer/main/install.ps1 | iex }"

if %ERRORLEVEL% neq 0 (
    echo.
    echo   Installation failed. Try running grail's install.ps1 directly:
    echo     powershell -Command "irm https://raw.githubusercontent.com/kody-w/rapp-installer/main/install.ps1 ^| iex"
    echo.
    pause
    exit /b 1
)

echo.
echo   Installation complete.
echo   Open a new terminal and run: brainstem
echo.
pause
