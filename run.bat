@echo off
REM Run script with conda environment activated
REM Usage: run.bat [args...]

REM Activate conda environment (adjust 'env' to your env name)
call conda activate env

REM Run the Python script with any arguments passed to this batch file
python run.py %*

REM Keep window open if there's an error
if %ERRORLEVEL% neq 0 (
    echo.
    echo Script failed with error code %ERRORLEVEL%
    pause
)
