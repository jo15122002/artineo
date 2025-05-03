@echo off
REM -----------------------------------------------------------------------------
REM start.bat — Lance le serveur Nuxt en mode développement sur Windows
REM Placez ce fichier à la racine de votre projet (même dossier que package.json)
REM -----------------------------------------------------------------------------

REM 1. Se placer dans le dossier du script
cd /d "%~dp0"

REM 2. Installer les dépendances si besoin
echo 📦 Vérification et installation des dépendances...
npm install

REM 3. Lancer le serveur Nuxt en mode dev dans une nouvelle fenêtre
echo 🚀 Démarrage du serveur Nuxt (dev mode)...
start "Nuxt Dev Server" cmd /k "npm run dev"

REM 4. Laisser le serveur monter un instant
timeout /t 2 /nobreak >nul

REM 5. Ouvrir le navigateur par défaut sur l'URL de développement
echo 🌐 Ouverture du navigateur sur http://localhost:3000...
start "" "http://localhost:3000"

exit /B