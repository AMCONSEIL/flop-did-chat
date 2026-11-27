@echo off
cd /d "%~dp0"
node -e "process.exit(Number(process.versions.node.split('.')[0]) >= 24 ? 0 : 1)"
if errorlevel 1 goto neednode
call npm ci --ignore-scripts --no-audit --no-fund
if errorlevel 1 goto fail
python -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install --require-hashes --only-binary=:all: -r requirements.lock.txt
if errorlevel 1 goto fail
echo FLOP DID Chat v0.3.0 Testnet installed. Run LANCER.cmd.
pause
exit /b 0
:neednode
echo Install Node.js 24 or later and npm.
:fail
echo Installation interrompue. Aucune cle de wallet n'a ete lue.
pause
exit /b 1
