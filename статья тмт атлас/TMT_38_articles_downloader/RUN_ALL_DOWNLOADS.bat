@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === Этап 1: базовая загрузка ===
python download_articles.py doi_list.txt
echo.
echo === Этап 2: curl_cffi ===
pip install curl_cffi -q
python download_stage2.py
echo.
echo === Этап 3: Cell/репозитории ===
python download_stage3.py
echo.
echo === Этап 4: Playwright ===
pip install playwright -q
python -m playwright install chromium
python download_stage4_playwright.py
echo.
echo === Этап 5: CORE API + PMC packages ===
python download_stage5.py
echo.
echo === Финальный отчёт ===
python finalize_status.py
echo.
echo Готово. Смотрите TMT_articles\STATUS_RU.txt
pause
