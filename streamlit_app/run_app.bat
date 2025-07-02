@echo off
echo ========================================
echo   BdStall Web Scraper - Streamlit UI
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo 💡 Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "app.py" (
    echo ❌ app.py not found in current directory
    echo 💡 Make sure this batch file is in the streamlit_app folder
    pause
    exit /b 1
)

REM Install dependencies if requirements.txt exists
if exist "requirements.txt" (
    echo 📦 Installing/updating dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        echo 💡 Try running: pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo ✅ Dependencies installed successfully
    echo.
)

echo 🚀 Starting BdStall Web Scraper...
echo 📱 The app will open in your default browser
echo 🔗 URL: http://localhost:8501
echo.
echo ⏹️  Press Ctrl+C to stop the application
echo ========================================
echo.

REM Run the Streamlit app
streamlit run app.py

echo.
echo 👋 Application stopped
pause