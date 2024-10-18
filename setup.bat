@echo off
REM Check Python version and install if necessary
where python
if %ERRORLEVEL% neq 0 (
    echo Python not found, installing Python 3.12.3...
    REM Insert logic to install Python 3.12.3 if not installed
)
python --version
pip install --upgrade pip
pip install -r requirements.txt
echo Setup complete.
