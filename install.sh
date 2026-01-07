#!/bin/bash

echo "Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3.10 \
    python3-pip \
    python3-venv \
    portaudio19-dev \
    alsa-utils \
    git \
    gcc \
    g++

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating virtual environment..."
source venv/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-linux.txt

echo "Installation complete!"
echo "To start the assistant, run:"
echo "  source venv/bin/activate"
echo "  python main.py"