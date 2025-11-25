@echo off
title Claude Usage Server for Car Thing
cd /d "%~dp0"
echo.
echo Starting Claude Usage Server...
echo.
python claude_usage_server.py
echo.
echo Server stopped.
pause
