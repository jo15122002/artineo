@echo off
setlocal

:: Se placer dans le répertoire du script
pushd "%~dp0"

:: Lancer le backend (back\start.bat) dans une nouvelle fenêtre CMD
start "Artineo Backend" cmd /k "cd /d ""%~dp0back"" && call start.bat"

:: Lancer le frontend (front\start.bat) dans une nouvelle fenêtre CMD
start "Artineo Frontend" cmd /k "cd /d ""%~dp0front"" && call start.bat"

:: Retour à l'endroit initial
popd
