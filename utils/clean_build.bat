@echo off
REM filepath: c:\Users\lapin\Documents\Gobelins\Mon_Dossier_De_Travail\Projet_fin_d_annee\dev\utils\clean_build.bat

echo ========================================
echo Script de nettoyage des fichiers build
echo ========================================
echo Repertoire courant: %CD%

REM Se placer dans le dossier parent (dev)
cd /d "%~dp0.."
echo Nouveau repertoire: %CD%
echo.

echo Verification de la structure des dossiers...
if exist ".\serveur\front" (
    echo [OK] Dossier serveur\front trouve
) else (
    echo [ERREUR] Dossier serveur\front introuvable
)

if exist ".\serveur\back" (
    echo [OK] Dossier serveur\back trouve
) else (
    echo [ERREUR] Dossier serveur\back introuvable
)
echo.

echo Suppression des fichiers temporaires de Nuxt...
if exist ".\serveur\front\node_modules" (
    echo Suppression de .\serveur\front\node_modules...
    rmdir /s /q ".\serveur\front\node_modules"
    if errorlevel 1 (
        echo [ERREUR] Echec suppression node_modules
    ) else (
        echo [OK] node_modules supprime
    )
) else (
    echo [INFO] .\serveur\front\node_modules n'existe pas
)

if exist ".\serveur\front\.nuxt" (
    echo Suppression de .\serveur\front\.nuxt...
    rmdir /s /q ".\serveur\front\.nuxt"
    if errorlevel 1 (
        echo [ERREUR] Echec suppression .nuxt
    ) else (
        echo [OK] .nuxt supprime
    )
) else (
    echo [INFO] .\serveur\front\.nuxt n'existe pas
)

if exist ".\serveur\front\.output" (
    echo Suppression de .\serveur\front\.output...
    rmdir /s /q ".\serveur\front\.output"
    if errorlevel 1 (
        echo [ERREUR] Echec suppression .output
    ) else (
        echo [OK] .output supprime
    )
) else (
    echo [INFO] .\serveur\front\.output n'existe pas
)

if exist ".\serveur\front\package-lock.json" (
    echo Suppression de .\serveur\front\package-lock.json...
    del /q ".\serveur\front\package-lock.json"
    if errorlevel 1 (
        echo [ERREUR] Echec suppression package-lock.json
    ) else (
        echo [OK] package-lock.json supprime
    )
) else (
    echo [INFO] .\serveur\front\package-lock.json n'existe pas
)

echo.
echo Suppression de l'environnement virtuel Python...
if exist ".\serveur\back\env" (
    echo Suppression de .\serveur\back\env...
    rmdir /s /q ".\serveur\back\env"
    if errorlevel 1 (
        echo [ERREUR] Echec suppression env
    ) else (
        echo [OK] env supprime
    )
) else (
    echo [INFO] .\serveur\back\env n'existe pas
)

if exist ".\serveur\back\__pycache__" (
    echo Suppression de .\serveur\back\__pycache__...
    rmdir /s /q ".\serveur\back\__pycache__"
    if errorlevel 1 (
        echo [ERREUR] Echec suppression __pycache__
    ) else (
        echo [OK] __pycache__ supprime
    )
) else (
    echo [INFO] .\serveur\back\__pycache__ n'existe pas
)

REM Recherche recursive des dossiers __pycache__
echo.
echo Recherche recursive des dossiers __pycache__...
for /d /r ".\serveur\back" %%i in (__pycache__) do (
    if exist "%%i" (
        echo Suppression de %%i...
        rmdir /s /q "%%i"
    )
)

echo.
echo ========================================
echo Nettoyage termine !
echo ========================================
pause