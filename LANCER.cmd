@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Lancez INSTALLER_WINDOWS.cmd une fois avant de demarrer le chat.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" flop_chat.py --open-browser
pause
