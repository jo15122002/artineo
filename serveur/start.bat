@echo off
REM 1) Crée l’environnement (uniquement la première fois)
python -m venv env

REM 2) Active l’environnement (il faut CALL)
call env\Scripts\activate.bat

REM 3) Met à jour pip et installe les dépendances
python -m pip install --upgrade pip
python -m pip install fastapi uvicorn

REM 4) Démarre le serveur
uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause