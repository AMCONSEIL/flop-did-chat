@echo off
cd /d "%~dp0"
python -m venv .venv
if errorlevel 1 goto fail
".venv\Scripts\python.exe" -m pip install --require-hashes --only-binary=:all: -r requirements.lock.txt
if errorlevel 1 goto fail
echo Installation terminee. Lancez LANCER.cmd.
pause
exit /b 0
:fail
echo Installation interrompue. Aucune cle de wallet n'a ete lue.
pause
exit /b 1
