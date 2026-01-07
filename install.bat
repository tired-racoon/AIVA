@echo off
echo Installing Python dependencies...

echo Creating virtual environment...
python -m venv winenv

echo Activating virtual environment...
call winenv\Scripts\activate.bat

echo Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements-windows.txt

echo.
echo Installation complete!
echo.
echo To start GUI application, run:
echo   start_gui.bat
echo.
echo To build .exe, run:
echo   build_windows.bat
pause