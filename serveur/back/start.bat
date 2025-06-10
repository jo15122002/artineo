@echo off
REM serveur/back/start.bat

REM — Parser l’argument --debug (s’il est fourni)
set "BACK_DEBUG=false"
:parse_args
if "%~1"=="" goto after_parse
if /I "%~1"=="--debug" (
    set "BACK_DEBUG=true"
    shift
    goto parse_args
) else (
    echo Unknown argument: %~1
    echo Usage: %~nx0 [--debug]
    exit /b 1
)
:after_parse

if "%BACK_DEBUG%"=="true" (
    echo 🔧 Mode DEBUG activé
) else (
    echo Mode DEBUG désactivé
)

REM — Crée un venv avec Python 3.11 si nécessaire
py -3.11 -m venv env

REM — Active le venv
call env\Scripts\activate.bat

REM — Met à jour pip
py -3.11 -m pip install --upgrade pip

REM — Installe les dépendances
py -3.11 -m pip install -r requirements.txt

REM — Lance le serveur avec Uvicorn
if "%BACK_DEBUG%"=="true" (
    py -3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
) else (
    py -3.11 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level info
)
pause
