#!/bin/bash
# Run script with conda environment activated (for WSL/Linux/Mac)
# Usage: ./run.sh [args...]

# Activate conda environment (adjust 'env' to your env name)
conda activate env

# Run the Python script with any arguments passed to this script
python run.py "$@"

# Keep window open if there's an error
if [ $? -ne 0 ]; then
    echo ""
    echo "Script failed with error code $?"
    read -p "Press Enter to continue..."
fi
