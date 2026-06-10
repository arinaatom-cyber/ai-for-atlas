@echo off
cd /d "%~dp0.."
echo Atlas Discovery Agent
echo   Streamlit UI: http://localhost:8501
echo   HTML site:   reports\discovery_index.html
python -m streamlit run discovery_app.py
pause
