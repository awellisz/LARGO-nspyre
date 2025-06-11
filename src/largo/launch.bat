@echo OFF
REM Launches the instrument server, data server, and GUI in separate command windows all at once
REM Modified from https://gist.githubusercontent.com/maximlt/531419545b039fa33f8845e5bc92edd6/raw/18df186517ddd1194fe3c4cb65c06ecd912cec7e/run_python_script_in_conda_env.bat
REM It doesn't require:
REM - conda to be in the PATH
REM - cmd.exe to be initialized with conda init

REM CHANGE THESE TO YOUR OWN PATHS
SET CONDAPATH=C:\Users\Antoni\miniconda3
SET ENVNAME=nspyre_env

set CURDIR = %CD% 

REM necessary if activating base environment (not really needed here)
if %ENVNAME%==base (SET ENVPATH=%CONDAPATH%) else (SET ENVPATH=%CONDAPATH%\envs\%ENVNAME%)

start "inserv" cmd /k "cd %CURDIR% && call %CONDAPATH%\Scripts\activate.bat %ENVPATH% && python drivers\remote_inserv.py"
REM 2 second delay to avoid anaconda yelling at you for accessing the same environment too quickly
timeout /t 2 >nul
start "dataserv" cmd /k "cd %CURDIR% && call %CONDAPATH%\Scripts\activate.bat %ENVPATH% && nspyre-dataserv"
timeout /t 2 >nul
rem start "gui" cmd /k "cd %CURDIR% && call %CONDAPATH%\Scripts\activate.bat %ENVPATH% && python gui\app.py"
start "gui" cmd /k "cd %CURDIR% && call %CONDAPATH%\Scripts\activate.bat %ENVPATH% && largo"
