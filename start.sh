#!/bin/bash

if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running install.sh..."
    bash install.sh
fi

source venv/bin/activate
python main.py