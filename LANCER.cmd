@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Lancez INSTALLER_WINDOWS.cmd une fois avant de demarrer le chat.
 pause
 exit /b 1
)
if not exist "node_modules\@flop-labs\sdk\package.json" (
 echo Run INSTALLER_WINDOWS.cmd to install the Testnet SDK.
 pause
 exit /b 1
)
echo FLOP DID Chat v0.3.0 - Testnet
".venv\Scripts\python.exe" flop_chat.py --open-browser %*
set "chat_status=%errorlevel%"
pause
exit /b %chat_status%
