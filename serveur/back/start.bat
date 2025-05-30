@echo off
REM — Crée un venv avec Python 3.11
py -3.11 -m venv env

REM — Active le venv
call env\Scripts\activate.bat

REM — Met à jour pip
py -3.11 -m pip install --upgrade pip

REM — Installe les dépendances
py -3.11 -m pip install -r requirements.txt

REM — Lance le serveur
py -3.11 -m uvicorn main:app --reload
pause
