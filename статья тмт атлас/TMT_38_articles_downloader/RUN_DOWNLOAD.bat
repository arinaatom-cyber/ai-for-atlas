@echo off
chcp 65001 >nul
cd /d "%~dp0"
py download_articles.py
if errorlevel 1 python download_articles.py
echo.
pause
