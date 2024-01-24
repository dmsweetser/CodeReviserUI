#!/bin/bash

# Set the path to the virtual environment activation script
activate_script="venv/bin/activate"

# Display diagnostic information
echo "--- Diagnostic Information ---"
echo "Virtual Environment Activation Script: $activate_script"
echo

# Check if the virtual environment activation script exists
if [ ! -f "$activate_script" ]; then
    echo "Error: Virtual environment activation script not found. Please check your virtual environment path."
    exit 1
fi

# Activate the virtual environment
source "$activate_script"

# Check if the virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Error: Virtual environment is not activated. Please activate it before running this script."
    exit 1
fi

echo "Virtual environment activated successfully."

# Display diagnostic information
echo
echo "--- Script Execution ---"
echo "Running Python script: CodeReviserUI.py"
echo

# Run your Python script within the virtual environment
python CodeReviserUI.py

# Check the exit code of the script
if [ $? -ne 0 ]; then
    echo "Error: The Python script encountered an error."
    exit 1
fi

echo "Script executed successfully."

# Deactivate the virtual environment
deactivate

# Check if deactivation was successful
if [ $? -ne 0 ]; then
    echo "Error: Unable to deactivate virtual environment."
    exit 1
fi

echo "Virtual environment deactivated successfully."

echo
echo "Script execution complete."
