@echo off
echo Starting Grocery Price Comparison App...
echo Current directory: %CD%
echo.
echo Files in current directory:
dir /b
echo.
python "%~dp0server.py"
if errorlevel 1 (
    echo.
    echo Error starting the server
    echo Please check the error message above
    pause
)
