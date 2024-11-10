#!/bin/bash

echo "Checking and installing requirements..."

# Check Python version
if ! command -v python3.10 &> /dev/null; then
    echo "Python 3.10+ not found. Installing..."
    if [ -f /etc/debian_version ]; then
        sudo apt update
        sudo apt install -y python3.10
    else
        echo "Please install Python 3.10+ manually for your distribution"
        exit 1
    fi
fi

# Check and create venv
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.10 -m venv venv
fi


# Check and install required packages
echo "Checking Python packages..."
while IFS= read -r requirement || [ -n "$requirement" ]; do
    if [[ $requirement =~ ^[^#] ]]; then  # Skip comments
        package=$(echo "$requirement" | cut -d'=' -f1)
        if ! pip freeze | grep -i "^$package==" > /dev/null; then
            echo "Installing $requirement..."
            pip install "$requirement"
        fi
    fi
done < requirements.txt

# Check and install FFmpeg
echo "Checking FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "Installing FFmpeg..."
    if [ -f /etc/debian_version ]; then
        wget https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/ffmpeg/7:7.1-3ubuntu1/ffmpeg_7.1.orig.tar.xz
        tar -xf ffmpeg_7.1.orig.tar.xz
        cd ffmpeg-7.1
        ./configure
        make
        sudo make install
        cd ..
        rm -rf ffmpeg_7.1.orig.tar.xz ffmpeg-7.1
        echo "FFmpeg installed. Please restart your system."
        exit 0
    else
        echo "Please install FFmpeg manually for your distribution"
        exit 1
    fi
fi

echo "All requirements are satisfied!"

# Activate venv
echo "Activating virtual environment..."
source venv/bin/activate