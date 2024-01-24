#!/bin/bash

echo "Setting up Python virtual environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python is not installed. Please install Python before running this script."
    exit 1
fi

# Create a virtual environment
python3 -m venv venv
if [ $? -ne 0 ]; then
    echo "Error: Unable to create virtual environment."
    exit 1
fi

echo "Virtual environment created successfully."

# Activate the virtual environment
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "Error: Unable to activate virtual environment."
    exit 1
fi

echo "Virtual environment activated successfully."

echo "Installing required packages..."

# Uncomment these to enable CUDA
# export CMAKE_ARGS="-DLLAMA_CUBLAS=on"
# export FORCE_CMAKE=1

pip install llama-cpp-python --force-reinstall --upgrade --no-cache-dir
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "Error: Unable to install required packages."
    exit 1
fi

echo
echo "Environment setup complete."
echo "To activate the virtual environment, run: source venv/bin/activate"
