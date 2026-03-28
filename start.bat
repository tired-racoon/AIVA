@echo off

if not exist "winenv" (
    echo Virtual environment not found. Running install.bat...
    call install.bat
)

call winenv\Scripts\activate.bat
python main.py