@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\sync_build.ps1" %*
set "BUILD_SYNC_EXIT=%ERRORLEVEL%"
pause
exit /b %BUILD_SYNC_EXIT%
