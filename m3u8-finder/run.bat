@echo off
chcp 65001 >nul
cd /d "%~dp0"
python m3u8_finder.py
if errorlevel 1 pause
