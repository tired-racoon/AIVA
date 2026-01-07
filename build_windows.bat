@echo off
echo Building Windows executable...

if not exist "winenv" (
    echo Virtual environment not found. Running install.bat...
    call install.bat
)

call winenv\Scripts\activate.bat

echo Installing PyInstaller...
pip install pyinstaller

echo Building executable...
python build_windows.py

echo.
echo Build complete! Check dist/AIVA.exe
pause