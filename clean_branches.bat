@echo off
REM Script pour supprimer les branches locales dont le remote a été supprimé

ECHO Récupération et nettoyage des références distantes...
git fetch --prune

ECHO Recherche des branches locales orphelines...
for /f "tokens=1" %%i in ('git branch -vv ^| findstr /C:"gone]"') do (
    ECHO Suppression de la branche %%i...
    git branch -d %%i
)

ECHO Opération terminée.
